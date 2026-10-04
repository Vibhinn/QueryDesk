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

## Accounts, conversations, and feedback

The React app signs users in through Keycloak using the OIDC Authorization Code flow with PKCE. The development realm allows self-registration using an email address and password; email is the username. This is not passwordless email-only login. Email verification and password reset are disabled in the local realm because no SMTP server is configured; set up SMTP and enable those flows before production. The API verifies each bearer access token and derives the user's ID from its signed `sub` claim. It never trusts a user ID sent by the browser. Chat list, history, summary, and feedback endpoints enforce conversation ownership using that identity.

Conversation data is stored in a PostgreSQL application database, separate from the analytics database. It has three tables: `conversation`, `messages`, and `feedback`; all include the Keycloak user ID. The API commits a submitted user message before calling the LLM or analytics database, so a downstream model/database outage does not discard the accepted question. Feedback is attached to assistant messages; downvotes require a comment. These service credentials and Keycloak's admin credentials in `.env.example` are local-development examples only. Set strong private values before exposing any service beyond localhost.

Recent messages in the selected conversation are passed as context for follow-up questions. If the schema cannot represent a request or its intent is unclear, the assistant asks a follow-up and offers suggestions; SQL generation and execution wait until the request is sufficiently clear. Choosing a suggestion adds it as a new turn in that conversation.

The model's semantic check is a guardrail, not a mathematical proof. SQLGlot checks syntax and AST properties. PostgreSQL `EXPLAIN` checks the query against the live database before execution.

## Run locally

1. Copy `.env.example` to `.env`, set `GOOGLE_API_KEY` to your Gemini API key, and replace all local-development passwords with private values.
2. Start the services:

   ```sh
   docker compose up --build
   ```

   On fresh volumes, this creates the sample analytics schema/data and starts the application database plus Keycloak. The API listens on `http://localhost:8000`; Keycloak is at `http://localhost:8081` and its admin console is available there. The development admin credentials come from `KEYCLOAK_ADMIN_USERNAME` and `KEYCLOAK_ADMIN_PASSWORD` in `.env`.
3. Start the web client in another terminal:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

   Open `http://localhost:5173`. Keycloak redirects you to sign in; use **Register** to create an account with email and password if needed. The imported `querydesk` realm and `querydesk-web` client are configured for this local URL.

The compose stack exposes the analytics database on port `5432` and the application database on port `5433`. Keycloak uses its own separate PostgreSQL database, which is not exposed on the host. Application tables are created automatically when the API starts. Do not use the example credentials outside local development.

The API requires the `sub` user identifier in access tokens. The `querydesk-api-audience` client scope includes a **Subject (sub)** mapper that adds it to regular and lightweight access tokens. If Keycloak was initialized before this mapper was added, realm import will not update the existing realm: in the admin console, open **Client scopes** → `querydesk-api-audience` → **Mappers** → **Add mapper** → **By configuration** → **Subject (sub)**. Enable **Add to access token** and, if shown, **Add to lightweight access token**, then save. Keep the existing realm and database; do not delete the Keycloak volume. Sign out and sign in again to receive a token with `sub`.

For a Vite host setup, the Keycloak URL, realm, client ID, and API URL default to the values above. Override them in `frontend/.env.local` if needed. If running FastAPI directly on the host instead of in Compose, set `KEYCLOAK_JWKS_URL=http://localhost:8081/realms/querydesk/protocol/openid-connect/certs` in the backend environment; the Compose default uses the internal Docker hostname.

Existing chats stored by the earlier SQLite version are retained in the old Docker volume if it exists, but are not automatically imported: those rows have no authenticated owner. The PostgreSQL application database starts a new user-scoped history.

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
