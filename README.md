# Querydesk

Querydesk lets anyone ask questions about a database in everyday language. With this system, you can see both the answer and the SQL behind it. The point is not to ask a model to guess at a database: the app reads a `SCHEMA.md`, narrows the relevant context, checks the request, validates the SQL, and only then runs it.

We have implemented a chat UI for interacting with the system. The system is smart enough to maintain a context of the entire chat and know what is the next question about. Results appear in a table, can be downloaded as CSV, and can be summarized on demand. Users can leave feedback on an answer.

## Getting started

You’ll need Docker Compose and a model API key. Gemini is the default provider. Compose starts both the API and the Vite frontend, so Node.js is only needed if you want to run the frontend outside Docker.

1. Create the environment files from their examples:

   ```sh
   cp .env.example .env
   cp frontend/.env.example frontend/.env.local
   ```

   In the root `.env`, set the model and app database values Compose needs:

   ```env
   MODEL_PROVIDER=google_genai
   MODEL_NAME=gemini-3.8-flash
   GOOGLE_API_KEY=<your_gemini_key>
   APP_DB_PASSWORD=choose_a_private_password
   ```

   The rest of the root example can stay as-is for this Compose setup. In `frontend/.env.local`, leave the API URL blank so requests use the `/api` proxy:

   ```env
   VITE_API_URL=
   ```

2. Start the complete app in the background:

   ```sh
   docker compose up --build -d
   ```

   Compose starts both databases, the API, and the frontend. On an empty analytics database volume, it loads the sample schema and rows from `db/init.sql` and `db/sample_data.sql`. The app is available at [http://localhost:5173](http://localhost:5173); the API listens on port `8000`.

Open the app and enter an email address. To stop the services, run `docker compose down`; this keeps the database volumes and saved chats.

The current sign-in is deliberately simple: an email identifies a chat space, and the API keeps short-lived bearer sessions in memory. It is not proof of identity—anyone who enters someone else’s email can see that email’s chats. Use it only for a trusted demo with non-sensitive data. After an API restart, sign in again with the same email to recover the same saved chats.

### Using a different model or host

The model connection is configured on the server. Gemini is the default (`MODEL_PROVIDER=google_genai`), using `GOOGLE_API_KEY`. For an OpenAI-compatible local service, configure it like this instead:

```env
MODEL_PROVIDER=openai-compatible
MODEL_NAME=system
MODEL_BASE_URL=http://host.docker.internal:1976/v1
MODEL_API_KEY=
```

Use the model ID your local service expects. From inside Docker, `127.0.0.1` points back to the API container, so use the host name your platform provides (for example, `host.docker.internal` on Docker Desktop). Keys and model settings stay on the server and are not sent to the browser.

### Using another database schema

Replace the root `SCHEMA.md` with a description of your database, then restart the API. Keep the format the schema reader understands: a dialect declaration, `### table_name` sections with Markdown column tables, and optional `## Relationships`, `## Business definitions`, and `## Global data rules and caveats` sections. The reader uses those descriptions to find relevant context; it does not inspect the database to fill in missing joins or business meanings. See [Architecture and workflow](docs/architecture.md#schema-reading-and-retrieval) for what is retrieved and how.


## QueryDesk as a package

The frontend manages chat windows, feedback collection and rendering server output in a tabular form.

There are two PostgreSQL databases. The analytics database (the sample database for which this NL2SQL system is built) is where generated SQL runs. The second database holds conversations, messages, and feedback. Keeping those separate means the chat history does not share the analytics database’s tables or credentials.

## The sample database used

The current demo analytics schema is a small customer and order database. Its tables, business definitions, and example relationships are described in [The database behind the demo](docs/database.md), including a relationship diagram. That page also explains the separate tables used to save chats and feedback.

## Code Flow

The model is reached through a small adapter, so the rest of the pipeline does not need to know whether the configured provider is Gemini, Anthropic, or an OpenAI-compatible service. The schema reader follows a similar boundary: it turns `SCHEMA.md` into table descriptions and retrieves the pieces that appear relevant to a question.

```mermaid
flowchart LR
    Browser[React and Vite chat] -->|HTTP and bearer session| API[FastAPI]
    API --> ChatDB[(Application PostgreSQL<br/>chats, messages, feedback)]
    API --> Graph[LangGraph NL2SQL workflow]
    Graph --> Schema[Markdown schema reader<br/>SCHEMA.md]
    Graph --> Model[LLM adapter]
    Graph --> Safety[SQLGlot validation]
    Safety --> Analytics[(Analytics PostgreSQL<br/>read-only queries)]
    Graph --> API
    API --> Browser
```

The detailed architecture and graph behavior are in [Architecture and workflow](docs/architecture.md). The prompts sent to the model are collected in [Prompts](docs/prompts.md).

## The LangGraph workflow

Each message moves through a graph with explicit stops. A request that is unrelated to the database ends early. An ambiguous or unsupported request gets a clarification and suggested alternatives instead of SQL. Only a request that passes scope checks reaches SQL generation.

```mermaid
flowchart TD
    Start([New message]) --> Check[Check database scope]
    Check -->|Out of scope or error| Stop1([Return a response])
    Check -->|In scope| Intent[Resolve intent and follow-up context]
    Intent -->|Needs clarification| Stop2([Ask a clarifying question])
    Intent -->|Clear request| Scope[Validate against schema scope]
    Scope -->|Unsupported or unclear| Stop2
    Scope -->|Supported| Retrieve[Retrieve relevant schema context]
    Retrieve --> Generate[Generate one read-only SQL query]
    Generate --> Validate[Parse SQL and check its meaning]
    Validate -->|Rejected| Stop3([Return validation error])
    Validate -->|Accepted| Optimize[Add row cap and run EXPLAIN]
    Optimize -->|Database rejects plan| Stop4([Return a database error])
    Optimize -->|Plan accepted| Execute[Execute in read-only transaction]
    Execute --> Finish([Return rows and SQL])
```

The graph’s nodes and branches are explained in [Architecture and workflow](docs/architecture.md). Prompt wording is documented in [Prompts](docs/prompts.md).

## A few important limits

Schema retrieval is lexical: it scores table names, column names, and words in each table description, then includes the strongest matches. This keeps large schemas from being sent wholesale to the model, but a well-written `SCHEMA.md` still matters. It should explain table grain, relationships, business terms, and data caveats. The reader does not inspect the live database to discover those rules.

SQLGlot checks that the result is a single read-only query and only refers to documented tables. A separate model call checks whether the query appears to answer the request. That semantic check is a useful guardrail, not a proof. Before execution, the app adds a result cap, asks PostgreSQL to `EXPLAIN` the query, and then runs it in a read-only transaction with a statement timeout.

The query result limit defaults to 500 rows and the statement timeout to 8 seconds. For a deployment with real data, use a database role with only `SELECT` privileges, enable HTTPS, and replace the demo sign-in.
