import { FormEvent, ReactNode, useEffect, useRef, useState } from 'react'
import { authenticatedFetch, currentUser, login, logout, SessionUser } from './authClient'

type QueryResult = {
  status: string
  message: string
  intent?: string
  resolved_question?: string
  suggestions: string[]
  sql?: string
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  truncated: boolean
  stages: string[]
  question?: string
  summary?: string
}

type ChatSummary = { id: string; user_id: string; title: string; created_at: string; updated_at: string }
type MessageFeedback = { rating: 'up' | 'down'; comment?: string | null }
type ChatMessage = {
  id: string
  chat_id: string
  user_id: string
  role: 'user' | 'assistant'
  content: string
  payload: QueryResult
  created_at: string
  feedback?: MessageFeedback | null
}
type ChatDetail = { chat: ChatSummary; messages: ChatMessage[] }
type ChatTurn = { user_message: ChatMessage; assistant_message: ChatMessage; result: QueryResult }

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const examples = [
  'Show me all customers',
  'Show monthly revenue for the last 12 months',
  'What are the top 5 products by units sold?',
]

function csvValue(value: unknown): string {
  const raw = value == null ? '' : String(value)
  return `"${raw.replaceAll('"', '""')}"`
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => ({})) as { detail?: unknown }
  if (typeof body.detail === 'string' && body.detail.trim()) return new Error(body.detail)
  if (Array.isArray(body.detail)) {
    const messages = body.detail.map(item => typeof item?.msg === 'string' ? item.msg : '').filter(Boolean)
    if (messages.length) return new Error(messages.join(' '))
  }
  return new Error(`${fallback} (HTTP ${response.status}).`)
}

export default function App() {
  const [chats, setChats] = useState<ChatSummary[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [summarizingId, setSummarizingId] = useState<string | null>(null)
  const [copiedSqlId, setCopiedSqlId] = useState<string | null>(null)
  const [savingFeedbackId, setSavingFeedbackId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [user, setUser] = useState<SessionUser | null>(() => currentUser())
  const [loginEmail, setLoginEmail] = useState('')
  const [signingIn, setSigningIn] = useState(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('querydesk-theme') === 'dark')
  const endRef = useRef<HTMLDivElement>(null)
  const initializedForUser = useRef<string | null>(null)

  useEffect(() => {
    if (!user) {
      initializedForUser.current = null
      setChats([])
      setActiveChatId(null)
      setMessages([])
      return
    }
    if (initializedForUser.current === user.user_id) return
    initializedForUser.current = user.user_id
    void initializeChats()
  }, [user?.user_id])
  useEffect(() => {
    const handleExpiredSession = () => {
      initializedForUser.current = null
      setUser(null)
      setError('Your demo session ended. Enter your email to sign in again.')
    }
    window.addEventListener('querydesk-session-expired', handleExpiredSession)
    return () => window.removeEventListener('querydesk-session-expired', handleExpiredSession)
  }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages.length, loading, activeChatId])

  function toggleTheme() {
    setDarkMode(current => {
      const next = !current
      localStorage.setItem('querydesk-theme', next ? 'dark' : 'light')
      return next
    })
  }

  async function signIn(event: FormEvent) {
    event.preventDefault()
    setSigningIn(true)
    setError('')
    try {
      const signedInUser = await login(loginEmail)
      setUser(signedInUser)
      setLoginEmail('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.')
    } finally {
      setSigningIn(false)
    }
  }

  async function signOut() {
    initializedForUser.current = null
    setUser(null)
    setChats([])
    setActiveChatId(null)
    setMessages([])
    setError('')
    try {
      await logout()
    } catch {
      // Clear the browser session even if the API is currently unavailable.
    }
  }

  async function initializeChats() {
    try {
      const response = await authenticatedFetch(`${API}/api/chats`)
      if (!response.ok) throw await apiError(response, 'Could not load chats')
      const data = await response.json() as ChatSummary[]
      setChats(data)
      if (data.length) await selectChat(data[0].id)
      else await createChat()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load chats.')
    }
  }

  async function createChat(): Promise<string | null> {
    if (loading) return null
    setError('')
    try {
      const response = await authenticatedFetch(`${API}/api/chats`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
      })
      const data = await response.json().catch(() => ({})) as ChatSummary & { detail?: string }
      if (!response.ok) throw new Error(data.detail ?? `Could not create a chat (HTTP ${response.status}).`)
      setChats(current => [data, ...current.filter(chat => chat.id !== data.id)])
      setActiveChatId(data.id)
      setMessages([])
      setQuestion('')
      setError('')
      return data.id
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create a chat.')
      return null
    }
  }

  async function selectChat(chatId: string) {
    if (loading) return
    setError('')
    try {
      const response = await authenticatedFetch(`${API}/api/chats/${chatId}`)
      const data = await response.json() as ChatDetail & { detail?: string }
      if (!response.ok) throw new Error(data.detail ?? `Could not open this chat (HTTP ${response.status}).`)
      setActiveChatId(chatId)
      setMessages(data.messages)
      setQuestion('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open this chat.')
    }
  }

  async function sendQuestion(text = question, event?: FormEvent) {
    event?.preventDefault()
    if (!text.trim() || loading) return
    let chatId = activeChatId
    if (!chatId) {
      chatId = await createChat()
      if (!chatId) return
    }
    const pendingMessage: ChatMessage = {
      id: `pending-${Date.now()}`, chat_id: chatId, user_id: user?.user_id ?? '', role: 'user', content: text.trim(), payload: {} as QueryResult, created_at: new Date().toISOString(),
    }
    setMessages(current => [...current, pendingMessage])
    setQuestion('')
    setLoading(true)
    setError('')
    try {
      const response = await authenticatedFetch(`${API}/api/chats/${chatId}/query`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text.trim() }),
      })
      const data = await response.json() as ChatTurn & { detail?: string }
      if (!response.ok) throw new Error(data.detail ?? `Could not process this message (HTTP ${response.status}).`)
      setMessages(current => [...current.filter(message => message.id !== pendingMessage.id), data.user_message, data.assistant_message])
      setChats(current => current.map(chat => chat.id === chatId
        ? { ...chat, title: chat.title === 'New chat' ? text.trim().slice(0, 60) : chat.title, updated_at: new Date().toISOString() }
        : chat).sort((a, b) => b.updated_at.localeCompare(a.updated_at)))
    } catch (err) {
      setMessages(current => current.map(message => message.id === pendingMessage.id
        ? { ...message, content: text.trim() }
        : message))
      setError(err instanceof Error ? err.message : 'Could not process this message.')
    } finally {
      setLoading(false)
    }
  }

  async function summarize(message: ChatMessage) {
    if (!activeChatId || !message.payload.sql || summarizingId) return
    setSummarizingId(message.id)
    setError('')
    try {
      const response = await authenticatedFetch(`${API}/api/chats/${activeChatId}/messages/${message.id}/summarize`, { method: 'POST' })
      const data = await response.json() as { summary?: string; detail?: string }
      if (!response.ok) throw new Error(data.detail ?? `Could not summarize this result (HTTP ${response.status}).`)
      setMessages(current => current.map(item => item.id === message.id
        ? { ...item, payload: { ...item.payload, summary: data.summary } }
        : item))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not summarize this result.')
    } finally {
      setSummarizingId(null)
    }
  }

  async function copySql(message: ChatMessage) {
    const sql = message.payload.sql
    if (!sql) return
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(sql)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = sql
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        const copied = document.execCommand('copy')
        textarea.remove()
        if (!copied) throw new Error('Clipboard access is unavailable.')
      }
      setCopiedSqlId(message.id)
      window.setTimeout(() => setCopiedSqlId(current => current === message.id ? null : current), 1800)
    } catch {
      setError('Could not copy the SQL. Check your browser clipboard permissions and try again.')
    }
  }

  async function submitFeedback(message: ChatMessage, rating: 'up' | 'down', comment?: string): Promise<boolean> {
    setSavingFeedbackId(message.id)
    setError('')
    try {
      const response = await authenticatedFetch(`${API}/api/chats/${message.chat_id}/messages/${message.id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating, comment }),
      })
      const data = await response.json() as MessageFeedback & { detail?: string }
      if (!response.ok) throw new Error(data.detail ?? 'Could not save feedback.')
      setMessages(current => current.map(item => item.id === message.id ? { ...item, feedback: data } : item))
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save feedback.')
      return false
    } finally {
      setSavingFeedbackId(null)
    }
  }

  const activeChat = chats.find(chat => chat.id === activeChatId)
  const hasConversation = messages.length > 0
  const csvFor = (result: QueryResult) => [
    result.columns.map(csvValue).join(','),
    ...result.rows.map(row => result.columns.map(column => csvValue(row[column])).join(',')),
  ].join('\r\n')

  function downloadCsv(message: ChatMessage) {
    const result = message.payload
    if (!result.columns.length) return
    const blob = new Blob([`\uFEFF${csvFor(result)}`], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'query-results.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  if (!user) {
    return <main className={`login-screen${darkMode ? ' dark' : ''}`}>
      <form className="login-card" onSubmit={event => void signIn(event)}>
        <a className="brand" href="#" aria-label="Querydesk home"><span className="brand-mark">q</span><span className="brand-name">querydesk</span></a>
        <div className="eyebrow"><span className="sparkle">✳</span> YOUR DATA, IN PLAIN ENGLISH</div>
        <h1>Welcome back</h1>
        <p>Enter your email to open your private chat space.</p>
        <label htmlFor="login-email">Email address</label>
        <input id="login-email" type="email" autoComplete="email" required maxLength={320} value={loginEmail} onChange={event => setLoginEmail(event.target.value)} placeholder="you@example.com" />
        {error && <div className="login-error" role="alert">{error}</div>}
        <button className="login-submit" type="submit" disabled={signingIn || !loginEmail.trim()}>{signingIn ? 'Signing in…' : 'Continue'}</button>
        <small>This demo uses your email as an identity label. No password or email verification is required.</small>
      </form>
    </main>
  }

  return (
    <div className={`chat-layout${darkMode ? ' dark' : ''}`}>
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="Querydesk home"><span className="brand-mark">q</span><span className="brand-name">querydesk</span></a>
        <button className="new-chat-button" onClick={() => void createChat()} disabled={loading}><span className="new-chat-plus">＋</span><span>New chat</span><kbd>⌘ K</kbd></button>
        <div className="sidebar-label">YOUR CHATS <span>{chats.length}</span></div>
        <nav className="chat-list" aria-label="Saved chats">
          {chats.map(chat => <button key={chat.id} className={`chat-list-item ${chat.id === activeChatId ? 'selected' : ''}`} onClick={() => void selectChat(chat.id)} disabled={loading} title={chat.title}>
            <span className="chat-list-icon">◌</span><span className="chat-list-title">{chat.title}</span>
          </button>)}
        </nav>
        <div className="sidebar-bottom"><span className="schema-dot"/><div><strong>nl2sql_demo</strong><small>PostgreSQL workspace</small></div></div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumb"><span>Chats</span><span className="breadcrumb-slash">/</span><strong>{activeChat?.title ?? 'New chat'}</strong></div>
          <div className="topbar-right"><span className="read-only-badge"><span/> READ ONLY</span><span className="identity-email" title={user.email}>{user.email}</span><button className="theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`} title={`Switch to ${darkMode ? 'light' : 'dark'} mode`}>{darkMode ? '☀' : '☾'}<span>{darkMode ? 'Light' : 'Dark'}</span></button><button className="logout-button" onClick={() => void signOut()}>Sign out</button><span className="avatar" title={user.email}>{(user.preferred_username[0] || 'U').toUpperCase()}</span></div>
        </header>

        <section className={`conversation ${hasConversation ? 'has-messages' : 'welcome-conversation'}`}>
          {!hasConversation ? <div className="welcome-content">
            <div className="eyebrow"><span className="sparkle">✳</span> YOUR DATA, IN PLAIN ENGLISH</div>
            <h1>What would you<br/>like to know?</h1>
            <p>Ask a question about your customers, orders, or products.</p>
            <div className="welcome-examples"><span>TRY ASKING</span>{examples.map(example => <button key={example} onClick={() => void sendQuestion(example)} disabled={loading}>{example}<span>↗</span></button>)}</div>
          </div> : <div className="message-list">
            {messages.map(message => message.role === 'user'
              ? <UserBubble key={message.id} message={message}/>
              : <AssistantMessage key={message.id} message={message} onDownload={downloadCsv} onSummarize={summarize} onCopySql={copySql} copiedSql={copiedSqlId === message.id} onFeedback={submitFeedback} feedbackBusy={savingFeedbackId === message.id} summarizing={summarizingId === message.id} onSuggestion={suggestion => void sendQuestion(suggestion)} onRetry={retryQuestion => void sendQuestion(retryQuestion)} disabled={loading}/>) }
            {loading && <div className="assistant-row"><span className="assistant-avatar">✳</span><div className="thinking-bubble"><span className="spinner"/> Checking the schema and preparing a validated query…</div></div>}
            <div ref={endRef}/>
          </div>}
        </section>

        {error && <div className="page-error"><span>!</span>{error}<button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
        <footer className="composer-area">
          <form className="query-box" onSubmit={event => void sendQuestion(question, event)}>
            <span className="input-icon">⌕</span>
            <input value={question} onChange={event => setQuestion(event.target.value)} placeholder={hasConversation ? 'Ask a follow-up…' : 'Ask a question about your data…'} aria-label="Ask a question about your data" disabled={loading}/>
            <button className="ask-button" disabled={loading || !question.trim()}>{loading ? <><span className="spinner"/> Thinking</> : <>Send <span>↗</span></>}</button>
          </form>
          <div className="composer-hint">Answers are grounded in your schema and validated before execution.</div>
        </footer>
      </main>
    </div>
  )
}

function UserBubble({ message }: { message: ChatMessage }) {
  return <div className="user-row"><div className="user-message">{message.content}</div><span className="user-avatar">V</span></div>
}

function AssistantMessage({
  message, onDownload, onSummarize, onCopySql, copiedSql, onFeedback, feedbackBusy, summarizing, onSuggestion, onRetry, disabled,
}: {
  message: ChatMessage
  onDownload: (message: ChatMessage) => void
  onSummarize: (message: ChatMessage) => void
  onCopySql: (message: ChatMessage) => void
  copiedSql: boolean
  onFeedback: (message: ChatMessage, rating: 'up' | 'down', comment?: string) => Promise<boolean>
  feedbackBusy: boolean
  summarizing: boolean
  onSuggestion: (suggestion: string) => void
  onRetry: (question: string) => void
  disabled: boolean
}) {
  const result = message.payload ?? {} as QueryResult
  const complete = result.status === 'complete'
  const [feedbackComment, setFeedbackComment] = useState(message.feedback?.comment ?? '')
  const [showFeedbackForm, setShowFeedbackForm] = useState(false)

  async function sendDownvote(event: FormEvent) {
    event.preventDefault()
    if (!feedbackComment.trim()) return
    if (await onFeedback(message, 'down', feedbackComment.trim())) setShowFeedbackForm(false)
  }

  return <div className="assistant-row">
    <span className="assistant-avatar">✳</span>
    <article className="assistant-content">
      {complete ? <>
        <div className="assistant-intro"><strong>Query result</strong>{result.intent && <span className="intent-chip">{result.intent}</span>}</div>
        {result.resolved_question && result.resolved_question.toLowerCase() !== (result.question ?? '').toLowerCase() && <div className="interpreted-question">Interpreted as: {result.resolved_question}</div>}
        <div className="result-actions"><button className="secondary-button" onClick={() => onDownload(message)} disabled={!result.columns?.length}>↓ <span>Download CSV</span></button><button className="primary-button" onClick={() => onSummarize(message)} disabled={summarizing}>{summarizing ? <><span className="spinner"/> Summarizing</> : <><span>✳</span> Summarize</>}</button></div>
        {result.summary && <div className="summary-card"><div className="summary-label"><span>✳</span> QUICK SUMMARY</div><p>{result.summary}</p></div>}
        <div className="table-card">
          <div className="table-toolbar"><div><span className="table-icon">▦</span><strong>Results</strong><span className="row-count">{result.row_count}{result.truncated ? '+' : ''} {result.row_count === 1 ? 'row' : 'rows'}</span></div><span className="table-meta">VALIDATED <span className="live-dot"/></span></div>
          {!result.columns?.length ? <div className="empty-state">The query returned no columns.</div> : !result.rows?.length ? <div className="empty-state"><span>◌</span><strong>No rows found</strong><p>Try adjusting your filters or asking a broader question.</p></div> : <div className="table-scroll"><table><thead><tr>{result.columns.map(column => <th key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{result.rows.map((row, index) => <tr key={index}>{result.columns.map(column => <td key={column}>{formatValue(row[column])}</td>)}</tr>)}</tbody></table></div>}
          {result.truncated && <div className="table-footnote">Showing the first {result.row_count} rows. Narrow your question for a smaller result.</div>}
        </div>
        {result.sql && <details className="sql-card"><summary><span className="sql-icon">⌘</span><span>Generated SQL</span><span className="chevron">⌄</span></summary><div className="sql-content"><div className="sql-toolbar"><span>SQL</span><button className="copy-sql-button" onClick={() => onCopySql(message)}>{copiedSql ? '✓ Copied' : 'Copy SQL'}</button></div><pre><code><HighlightedSQL sql={result.sql}/></code></pre></div></details>}
      </> : <>
        <div className="assistant-intro"><strong>{result.status === 'needs_clarification' ? 'Quick clarification' : result.status === 'out_of_scope' ? 'Outside this database' : 'I couldn’t complete that'}</strong></div>
        <p className={`assistant-text${result.status === 'error' ? ' assistant-error-text' : ''}`}>{result.message || message.content}</p>
        {result.status === 'error' && result.question && <button className="retry-button" onClick={() => onRetry(result.question!)} disabled={disabled}>↻ Try again</button>}
        {!!result.suggestions?.length && <div className="clarification-options">{result.suggestions.map((suggestion, index) => <button key={`${suggestion}-${index}`} onClick={() => onSuggestion(suggestion)} disabled={disabled}>{suggestion}<span>↗</span></button>)}</div>}
      </>}
      <div className="message-feedback">
        <span>{message.feedback ? 'Thanks for your feedback' : 'Was this helpful?'}</span>
        <button className={message.feedback?.rating === 'up' ? 'selected' : ''} aria-label="Helpful" title="Helpful" disabled={feedbackBusy} onClick={() => void onFeedback(message, 'up')}>👍</button>
        <button className={message.feedback?.rating === 'down' ? 'selected' : ''} aria-label="Not helpful" title="Not helpful" disabled={feedbackBusy} onClick={() => { setFeedbackComment(message.feedback?.comment ?? ''); setShowFeedbackForm(true) }}>👎</button>
      </div>
      {showFeedbackForm && <form className="feedback-form" onSubmit={event => void sendDownvote(event)}>
        <label htmlFor={`feedback-${message.id}`}>What could be improved?</label>
        <textarea id={`feedback-${message.id}`} value={feedbackComment} onChange={event => setFeedbackComment(event.target.value)} maxLength={2000} rows={2} required />
        <div><button type="button" className="feedback-cancel" onClick={() => setShowFeedbackForm(false)}>Cancel</button><button type="submit" className="feedback-submit" disabled={!feedbackComment.trim() || feedbackBusy}>{feedbackBusy ? 'Saving…' : 'Send feedback'}</button></div>
      </form>}
      <div className="assistant-footnote">Generated SQL is schema-grounded and read-only.</div>
    </article>
  </div>
}

const SQL_KEYWORDS = new Set('SELECT DISTINCT FROM WHERE AND OR NOT NULL IS IN LIKE ILIKE BETWEEN AS JOIN INNER LEFT RIGHT FULL OUTER CROSS ON GROUP BY ORDER ASC DESC LIMIT OFFSET COUNT SUM AVG MIN MAX CASE WHEN THEN ELSE END COALESCE CAST WITH UNION ALL HAVING EXISTS TRUE FALSE'.split(' '))
const SQL_TOKEN_PATTERN = /--[^\n]*|\/\*[\s\S]*?\*\/|'(?:''|[^'])*'|"(?:""|[^"])*"|`(?:``|[^`])*`|\b\d+(?:\.\d+)?\b|\b[a-z_][\w$]*\b|[(),.;=*<>!+\/%-]/gi

function HighlightedSQL({ sql }: { sql: string }) {
  const fragments: ReactNode[] = []
  let cursor = 0
  for (const match of sql.matchAll(SQL_TOKEN_PATTERN)) {
    const token = match[0]
    const index = match.index ?? cursor
    if (index > cursor) fragments.push(sql.slice(cursor, index))
    let kind = 'identifier'
    if (token.startsWith('--') || token.startsWith('/*')) kind = 'comment'
    else if (token.startsWith("'")) kind = 'string'
    else if (/^\d/.test(token)) kind = 'number'
    else if (/^[a-z_][\w$]*$/i.test(token) && /^\s*\(/.test(sql.slice(index + token.length))) kind = 'function'
    else if (SQL_KEYWORDS.has(token.toUpperCase())) kind = 'keyword'
    else if (/^[(),.;=*<>!+\/%-]$/.test(token)) kind = 'operator'
    fragments.push(<span className={`sql-${kind}`} key={`${index}-${token}`}>{token}</span>)
    cursor = index + token.length
  }
  if (cursor < sql.length) fragments.push(sql.slice(cursor))
  return <>{fragments}</>
}

function formatValue(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value)
  return String(value)
}
