# Querydesk NL2SQL

A local NL2SQL demo built around `SCHEMA.md`. It uses a FastAPI API, a LangGraph server-side pipeline, PostgreSQL, SQLGlot validation, and a React/Vite TypeScript UI.

## Pipeline

1. Check whether the request can be answered by this database.
2. Detect the analytical intent and candidate tables; ask for clarification when needed.
3. Validate scope against retrieved schema context.
4. Retrieve relevant table definitions, relationships, business definitions, and global caveats from `SCHEMA.md`.
5. Generate PostgreSQL SQL.
6. Parse and restrict SQL to one read-only query, then use a separate model call to check whether it answers the request.
7. Add a configurable result cap, re-parse the SQL, and ask PostgreSQL for an `EXPLAIN` plan.
8. Execute in a read-only transaction with a statement timeout.
9. Render the result as a table. CSV download is created in the browser; **Summarize** calls the model only when clicked.

## Email identity, conversations, and feedback

The app has a lightweight email-only sign-in. The API issues a random bearer token held in process memory and derives a stable user ID from the normalized email. Conversation, message, and feedback rows store that user ID; all chat/history/summary/feedback routes filter by it. The browser stores the bearer token and can sign in again after an API restart to recover the same chats. Sessions expire after 24 hours and are lost when the API process restarts.

This is **not secure authentication**: there is no password or email verification, so anyone who knows an email address can enter it and see that email's chats. Use it only for a trusted demo with non-sensitive data. It also expects one API process because sessions are held in memory.

Conversation data is stored in a PostgreSQL application database, separate from the analytics database. It has three tables: `conversation`, `messages`, and `feedback`; all include the app user ID. The API commits a submitted user message before calling the LLM or analytics database, so a downstream model/database outage does not discard the accepted question. Feedback is attached to assistant messages; downvotes require a comment. Service credentials in `.env.example` are local-development examples only. Set private values before exposing any service beyond localhost.

Recent messages in the selected conversation are passed as context for follow-up questions. If the schema cannot represent a request or its intent is unclear, the assistant asks a follow-up and offers suggestions; SQL generation and execution wait until the request is sufficiently clear. Choosing a suggestion adds it as a new turn in that conversation.

The model's semantic check is a guardrail, not a mathematical proof. SQLGlot checks syntax and AST properties. PostgreSQL `EXPLAIN` checks the query against the live database before execution.

## Run locally

1. Copy `.env.example` to `.env`, set `GOOGLE_API_KEY` to your Gemini API key, and replace the application database password with a private value.
2. Start the services:

   ```sh
   docker compose up --build --remove-orphans
   ```

   On fresh volumes, this creates the sample analytics schema/data and starts the application database. The API listens on `http://localhost:8000`.
3. Start the web client in another terminal:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

   Open `http://localhost:5173` and enter an email address to sign in.

The compose stack exposes the analytics database on port `5432` and the application database on port `5433`. Application tables are created automatically when the API starts. The API accepts comma-separated browser origins in `CORS_ORIGINS` (default: `http://localhost:5173`).

To access a Vite frontend on an EC2 host by IP, set `VITE_API_URL=http://<EC2-IP>:8000` in `frontend/.env.local` and `CORS_ORIGINS=http://<EC2-IP>:5173` in the server's `.env`, then restart Vite and the API. Allow ports 5173 and 8000 in the EC2 security group only from trusted IP addresses. This demo login sends bearer tokens over HTTP, so use it only on a trusted network; use HTTPS and real authentication for a public deployment.

Existing chats stored by the earlier SQLite version are retained in the old Docker volume if it exists, but are not automatically imported. Chats created under Keycloak remain in the PostgreSQL application database, but their old Keycloak subject IDs cannot be automatically mapped to email-derived IDs; they will not appear in the new email-only login unless you migrate that mapping.

The database uses a read-only transaction for both `EXPLAIN` and query execution. The configured row cap defaults to 500 and the statement timeout defaults to 8 seconds. For a real deployment, use a dedicated database role with only `SELECT` privileges as an additional boundary.

If the PostgreSQL volume already existed before the sample data was added, init scripts will not run again automatically. Apply the idempotent seed file without deleting the existing volume:

```sh
docker compose exec -T db psql -U nl2sql -d nl2sql_demo < db/sample_data.sql
```

### Local OpenAI-compatible model endpoint

For a model server listening at `http://127.0.0.1:1976/v1/chat/completions`, set:

```env
MODEL_PROVIDER=openai-compatible
MODEL_NAME=<model id accepted by your local server>
MODEL_API_KEY=
MODEL_BASE_URL=http://127.0.0.1:1976/v1
```

Run only PostgreSQL in Docker (`docker compose up -d db`), then run FastAPI on your host so its `127.0.0.1` reaches the model server:

```sh
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The OpenAI SDK requires a non-empty key value to construct its client, so the adapter sends `local-no-key` when a custom compatible endpoint is configured and `MODEL_API_KEY` is blank. The local server must ignore that bearer token. If it rejects any authorization header, it will need a no-auth HTTP adapter instead. Set `MODEL_NAME` to the model identifier expected by the server; if supported, its `/v1/models` endpoint may list it.

## Model providers

Gemini is the default provider (`MODEL_PROVIDER=google_genai`) and uses `GOOGLE_API_KEY`; the default model is `gemini-3.8-flash`. The model name is configurable. The adapter also supports OpenAI-compatible endpoints and Anthropic; other LangChain providers can be enabled by adding the provider integration package and its provider-specific configuration. Keys stay on the server and are never sent to the browser.

## Replacing `SCHEMA.md`

Set `SCHEMA_PATH` to the new Markdown file. The current reader extracts `### table_name` sections, column tables, `## Relationships`, `## Business definitions`, and `## Global data rules and caveats`. It retrieves table sections based on question terms and explicit table hints. Preserve exact database table and column names. If a schema uses a different Markdown layout, update the reader or provide a normalized schema document; arbitrary prose cannot be parsed reliably without a defined contract.

The demo is configured for PostgreSQL. Changing to a different database dialect also requires a matching SQLAlchemy driver and execution configuration.
