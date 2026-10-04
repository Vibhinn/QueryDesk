# Requirements: SCHEMA.md Generator for NL2SQL

## 1. Goal

Build an interactive tool that helps a database owner create, review, and export a `SCHEMA.md` file that this NL2SQL application can parse. The generated file must tell an LLM what the database contains and, crucially, how the organization defines metrics, joins, time, status, and data quality.

The generator must distinguish:

- **Facts discovered from database metadata**: exact table/column names, data types, nullability, keys, constraints, and declared foreign keys.
- **Facts inferred from profiling**: observed null rates, distinct counts, ranges, and sample values. These are evidence, not business definitions.
- **Business meaning supplied or confirmed by a human**: what a field means, which statuses count as revenue, which records to exclude, and what “active customer” means.

Never silently turn an inference into a business rule. If meaning or join behavior is unknown, mark it as unknown and ask the user to decide.

## 2. Output and compatibility contract

The first version must export one UTF-8 Markdown file named `SCHEMA.md` in the format below. Keep the heading names, field labels, table heading structure, and column-table headers stable: the current application reads Markdown with a lightweight parser rather than a general Markdown AST.

The current parser recognizes:

1. `**Dialect:** ...` in the `## Database` section.
2. Table sections headed exactly like `### \`table_name\``. A table section ends at the next `###` table or `##` section.
3. A Markdown column table in each table section. It uses the first cell of each row as the column name and expects the current headers: `Column`, `Type`, `Nullable`, `Key / reference`, `Meaning`.
4. Sections named exactly `## Relationships`, `## Business definitions`, and `## Global data rules and caveats`.
5. Relationship and business-definition Markdown tables; global rules written as bullet lines beginning with `* ` or `- `.
6. Within table sections, `**Purpose:**` and `**Row grain:**` are used to build a bounded table overview.

Do not rely on unrecognized front matter, HTML, nested headings, arbitrary JSON blocks, or prose-only table layouts for information required by the current app. The generator may retain a richer internal representation, but it must render a compatible Markdown view.

### 2.1 Canonical document skeleton

```markdown
# Database Schema and Business Semantics

## Database

* **Dialect:** PostgreSQL
* **Database/schema name:** `analytics`
* **Default reporting timezone:** UTC
* **Currency policy:** Unknown; confirm before generating cross-currency monetary metrics.

## Tables

### `public.orders`

* **Purpose:** One sentence describing what this object represents.
* **Row grain:** One row per ... State the uniqueness/grain explicitly.
* **Object type:** Base table, view, materialized view, or other supported object.
* **Business aliases:** order, purchase, transaction (only confirmed synonyms).
* **Owner/source:** Optional operational owner or source system.
* **Data quality notes:** Known caveats, duplicates, delayed updates, or unknowns.

| Column | Type | Nullable | Key / reference | Meaning |
| ------ | ---- | -------- | --------------- | ------- |
| `order_id` | BIGINT | No | PK | Unique identifier for an order. |
| `created_at` | TIMESTAMP WITH TIME ZONE | Yes |  | Time the order record was created; stored in UTC. |

## Relationships

| From | To | Join condition | Cardinality / notes |
| ---- | -- | -------------- | ------------------- |
| `public.customers` | `public.orders` | `customers.customer_id = orders.customer_id` | One customer to zero or more orders; each order belongs to one customer. |

## Business definitions

| Term | Definition / formula | Required filters and caveats |
| ---- | -------------------- | ---------------------------- |
| Net revenue | `SUM(orders.net_amount)` | State eligible statuses, refund treatment, currency, and time basis. |

## Global data rules and caveats

* State rules that apply across tables, such as tenant isolation or soft deletion.
* State known unsupported concepts and unresolved definitions explicitly.

## Optional question-to-schema examples

| Natural-language question | Expected tables | Metric / filters / grouping |
| ------------------------- | --------------- | --------------------------- |
| Example question | `public.orders` | Expected calculation and filters, including important exclusions. |
```

The example fields `Object type`, `Business aliases`, `Owner/source`, and `Data quality notes` are useful content for the LLM even though the current parser does not extract them as structured fields. Keep them inside the table section. The parser still includes the text of that section in retrieved context.

## 3. Required database-level information

The generator must collect or request the following before marking a document ready:

### Required for current parser and query generation

- **SQL dialect**: use an unambiguous name, such as `PostgreSQL`, `MySQL`, `SQLite`, `Snowflake`, `BigQuery`, or `SQL Server`. The running app must also support that dialect and driver; writing a dialect name in Markdown does not install support.
- **Database/schema name**: catalog/database and schema where possible. State the default schema/search path if object names are not fully qualified.
- **Table/view inventory**: exact names and each object's type.
- **Every included column**: exact name, database type, nullability, key/reference status, and a plain-language meaning.
- **Row grain** for every included table or view.
- **Declared relationships** and join semantics for joins the user is expected to ask about.
- **Business definitions** for any metrics or domain terms the app is expected to calculate.
- **Global caveats**: timezone, currencies, tenancy, soft deletes, test data, archive behavior, and other rules that could change query results.

### Strongly recommended database-level fields

- Product/application name and short database purpose.
- Database engine and version, if known.
- Default schema and whether identifiers are case-sensitive or require quoting.
- Default reporting timezone and whether timestamps are stored in UTC, local time, or mixed timezones.
- Currency codes, conversion policy, and whether currency conversion data exists.
- Tenant/account boundary and the approved tenant key(s). Do not expose secrets or credentials.
- “As of” or freshness expectations, ingestion delay, and whether data is current, historical, or a snapshot.
- Known database-wide exclusions, for example test tenants, internal accounts, deleted rows, or demo records.
- Contact/owner for unresolved semantics.

## 4. Required table-level information

For every object included in NL2SQL context, generate or request:

- Exact object name, preserving catalog, schema, case, and quoting where relevant.
- Object kind: base table, view, materialized view, external table, or synonym. Flag unsupported object kinds rather than presenting them as ordinary tables.
- Purpose: what business entity/event/process it represents.
- Row grain: what one row represents and the key that makes it unique. If uniqueness is not guaranteed, say so.
- Business aliases and common user language, only when confirmed.
- Row lifecycle: current-state versus event/history/snapshot table, retention window, and update/delete behavior.
- Data quality caveats: duplicates, missing periods, late arriving records, unreliable fields, or known backfills.
- Whether the object has access restrictions or contains sensitive fields that must not be selected or displayed.

The generated table heading must be parseable by the current parser: `### \`simple_identifier\`` or, where supported by its name rules, `### \`schema.simple_identifier\``. The current parser strips schema qualification internally and does not safely distinguish two schemas that contain the same table name. The generator must detect duplicate unqualified names and warn/block export for this app until the parser is upgraded or the objects are unambiguously renamed/selected.

## 5. Required column-level information

Create one Markdown row for every column in each included object. Preserve the exact database column name. Do not rename or “clean up” identifiers in the schema file.

| Attribute | Requirement |
| --------- | ----------- |
| Name | Exact identifier, including capitalization when meaningful. |
| Type | Exact database type, including precision/scale, array/JSON details, and timezone qualification where available. |
| Nullable | `Yes`, `No`, or `Unknown`; do not infer non-nullability from sample data. |
| Key/reference | PK, composite PK component, FK target, unique constraint, indexed-only, or blank/unknown. Distinguish constraints from indexes. |
| Meaning | Plain language purpose, grain within the row, and important semantic distinctions. |

In the **Meaning** cell, include as applicable:

- Units and scale: cents versus dollars, meters versus feet, integer minor units, basis points, and so on.
- Date/time meaning: event time versus ingestion time versus update time; timezone and boundary semantics.
- Domain/value meanings: allowed values and their meanings, including null/unknown/other behavior.
- Identifier semantics: source-system ID, globally unique ID, natural key, surrogate key, tenant-scoped key, or external reference.
- Snapshot/history semantics: whether old values are retained or overwritten.
- Sensitive-data classification: personal, financial, health, authentication, confidential, or safe for display. Prefer marking fields as restricted rather than including actual sensitive values.
- Known quality limitations, such as sparsity, stale values, inconsistent casing, or unreliable historical coverage.
- Whether the field is suitable for filtering, grouping, or aggregation when this is not obvious from its type/name.

Do not put secrets, credentials, access tokens, connection strings, raw personal data, or large raw value dumps in `SCHEMA.md`.

## 6. Relationships and joins

Every relationship row must make the join safe to construct and explain its effect on row counts.

For each relationship, capture:

- Exact source and target objects and columns.
- Full join predicate, including all columns in composite keys.
- Directional cardinality: one-to-one, one-to-many, many-to-one, many-to-many, or unknown.
- Optionality: whether the foreign key can be null, and whether unmatched rows are possible.
- Whether the relationship is declared in the database or manually confirmed. A matching type/name is not proof of a relationship.
- Correct join path where there are multiple possible paths.
- Whether the join is temporal/as-of, tenant-scoped, filtered, or requires extra predicates.
- Fanout effects: which side duplicates rows and which measures become unsafe after joining.
- Preferred join type only if there is a real business default; otherwise leave it to the question.
- Known invalid, orphaned, or duplicated keys.

Do not create a direct relationship merely because two columns share a name or type. For many-to-many bridges, document the bridge and its grain. If two valid join paths exist, explicitly describe the intended path or mark the path ambiguous so the UI can ask the user.

The current parser extracts relationship rows from the table under `## Relationships`. Use the exact four-column shape shown in the skeleton. Keep the Markdown separator row. Put extra detail in the final cardinality/notes cell.

## 7. Business definitions and measures

This section is essential for useful analytics. A catalog reveals types and constraints, but cannot define “revenue,” “active,” “customer,” “conversion,” or “month-to-date.”

For every expected metric or domain term, specify:

- Canonical term and confirmed synonyms users might say.
- Exact formula, with table and column names.
- Aggregation behavior: additive, semi-additive, non-additive, distinct-count, ratio, average-of-ratios, or other.
- Required status/type/tenant/soft-delete filters.
- Numerator and denominator for rates; behavior when denominator is zero.
- De-duplication key and treatment of duplicate source records.
- Time basis: which timestamp/date column controls inclusion and which timezone/calendar applies.
- Currency and unit conversion behavior.
- Refund, cancellation, reversal, tax, shipping, discount, and adjustment treatment.
- Whether the metric can be safely computed after joining other objects. State when pre-aggregation or distinct counting is required.
- Inclusion of zero-activity entities and entities with missing data.
- Whether the definition is official, provisional, deprecated, or unresolved, plus owner/effective date if known.

Use separate rows for terms that sound alike but differ, for example order count versus item count, booked revenue versus recognized revenue, registered country versus shipping destination, or current customers versus customers active on a given historical date.

Do not publish a metric as definitive if its owner has not confirmed the formula. Mark it **Unresolved** and give the competing interpretations so the NL2SQL app can request clarification.

## 8. Global data rules and caveats

Write each rule as a short, explicit bullet. Include rules that affect multiple tables or are easy for an LLM to miss:

- Tenant isolation and required tenant predicates.
- Soft-deleted, archived, test, demo, employee, internal, or suppressed records.
- Whether inactive entities retain valid historical activity.
- Timezone, fiscal calendar, week start, inclusive/exclusive date boundaries, and daylight-saving behavior.
- Currency storage, conversion rates, and whether values across currencies may be summed.
- Row multiplication caused by joins and safe aggregation patterns.
- Snapshot validity/effective dates and how to select the current record.
- Data freshness, late-arriving data, incomplete periods, and backfill behavior.
- Null interpretation and sentinel values (for example, zero, empty string, `UNKNOWN`, or a special date).
- Known missing concepts. Explicitly say when the schema has no state, shipping address, payment time, product master, or other commonly assumed field.
- Any metric or query that must not be generated, and why.

Rules should say what to do, not just describe risk: “Filter to `is_deleted = FALSE` for current customer counts” is more actionable than “Some customers are deleted.” Never provide a tenant ID as an example if it is sensitive; document the column and policy instead.

## 9. Optional question-to-schema examples

Include reviewed examples for high-value or error-prone user questions. Each example should record:

- Natural-language request, including realistic synonyms.
- Expected tables and join path.
- Expected metric/formula, filters, grouping, ordering, and date interpretation.
- Important exclusions and fanout handling.
- Whether the request is answerable, needs clarification, or is out of scope.

Examples are guidance, not a substitute for the actual column definitions and business rules. Do not include an example that encodes an unapproved assumption. The current parser does not separately retrieve this optional section; it is still useful for future retrieval/evaluation tooling, but do not rely on it as the only source of a required rule.

## 10. Requirements for messy production databases

The generator must assume that catalogs can contain hundreds or thousands of objects, overlapping names, legacy fields, inconsistent conventions, and sparse documentation.

### 10.1 Discovery and selection

- Support browsing/searching large catalogs without loading every object into one editing screen.
- Allow users to select schemas, tables, views, and columns for inclusion. Default to explicit inclusion; offer bulk selection and filters.
- Show object kind, schema, owner, row-count estimate if safely available, last-modified/freshness hints if available, and dependency information.
- Detect duplicate names across schemas, case-only name differences, reserved words, unusual characters, very long identifiers, and names requiring quoting.
- Show view definitions/dependencies where permitted, but never assume a view definition is a business definition.
- Allow users to include curated views instead of raw operational tables and explain the trade-off.
- Allow incomplete catalogs to be saved as drafts, with missing/unknown fields clearly listed.

### 10.2 Safe introspection and profiling

- Use read-only, least-privilege credentials for metadata discovery. Never require write permissions.
- Keep credentials in a secret store or environment configuration, never in the exported document, browser bundle, logs, or generated examples.
- Make data profiling optional, separately permissioned, bounded, cancellable, and query-time limited. Metadata-only generation must remain available.
- Profile only selected objects/columns, using bounded aggregates/samples; avoid full table scans by default.
- Mask, redact, or suppress likely PII and secrets in samples. Do not put raw sample rows in `SCHEMA.md`.
- Label every profiled statistic with observation time and source; explain that profiles can become stale.
- Do not infer business meanings, foreign keys, metric formulas, tenant rules, or status policy solely from correlations or sample values.
- Show estimated cost/impact and provide a preview of profiling queries when practical.

### 10.3 Documentation assistance

- Pre-fill facts directly available from catalog metadata and label their source.
- Suggest likely descriptions or relationships only as editable, unconfirmed suggestions.
- Ask targeted questions for missing purpose, row grain, metric definitions, lifecycle, exclusions, and ambiguous joins.
- Support review by data owners and retain who confirmed a definition and when in generator metadata. The exported Markdown can include a concise owner/status note where useful.
- Distinguish “not documented,” “unknown,” “not applicable,” and “does not exist.” Never use an empty cell to imply these are equivalent.

### 10.4 Large-schema context strategy

- Export all selected schema documentation, but do not send the whole file to the model for every question.
- Build a searchable catalog/index from table purpose, column names/meanings, aliases, relationships, and business definitions.
- Retrieve a small relevant set of tables and all necessary join-path/metric rules; preserve mandatory global constraints such as tenant isolation.
- Detect when retrieval omitted a required join or metric definition and ask for clarification or fail closed.
- Provide a preview of the context that would be sent for representative questions.
- Track token/context size and warn before exporting extremely verbose documentation.

The current app uses lexical word overlap for retrieval and selects a bounded number of table sections. Therefore, generator output should keep descriptions precise and avoid duplicating lengthy prose in every column. Mandatory rules should be concise and placed in the recognized global or business-definition sections.

## 11. Validation and linting before export

The generator must validate the generated file before offering it as ready for this application.

### Structural checks

- Required headings and the exact required labels are present.
- At least one parseable `### \`table_name\`` section exists.
- Every included table has a Markdown column table with all five expected headers.
- Each column row has five cells and a parseable first-cell identifier.
- Table and column identifiers do not contain unsupported Markdown table delimiters, or are correctly escaped and tested with the app parser.
- Relationships and definitions use a Markdown table with header and separator rows.
- Global rules are bullets, not paragraphs that the current parser silently misses.
- No duplicate unqualified table names exist for the current parser.
- Dialect is non-empty and supported by the configured SQLGlot/database stack.

### Semantic/completeness checks

- Every object has a purpose and row grain, or is explicitly marked unknown and blocks “production-ready” status.
- Every column has exact type/nullability and a meaningful description, or an explicit unknown marker.
- Every declared foreign key has a matching target and compatible types; inferred relationships are visibly marked unconfirmed.
- Composite keys and composite foreign keys include every component.
- Metric definitions reference columns that exist in selected objects.
- Formula filters, date basis, units/currency, duplicate behavior, and join fanout are documented when applicable.
- Rules that conflict are highlighted for human resolution.
- Dangerous universal assumptions (e.g., “all rows are valid,” “all amounts are USD”) require confirmation.
- Unknowns, stale profiling, sensitive fields, and unsupported object types are shown in a readiness report.

The tool should offer at least two export states:

- **Draft / prototype**: structurally parseable, with unresolved semantics visibly reported.
- **Reviewed / production candidate**: critical definitions and access policies confirmed by an authorized owner.

Do not describe a document as guaranteed correct merely because it passes structural validation.

## 12. UX requirements for the generator

- Guided steps: connect/discover (optional), select objects, document semantics, review joins and metrics, validate, preview, export.
- Keep a persistent list of unanswered questions and let users return to incomplete work.
- Show exact proposed Markdown alongside structured form inputs.
- Provide a “copy/download `SCHEMA.md`” action and a clear instruction for configuring `SCHEMA_PATH`.
- Provide before/after diffs when updating an existing schema file.
- Preserve human-written descriptions and definitions when refreshing catalog-derived fields.
- Make stale metadata/profiling obvious; refresh must not silently overwrite reviewed business definitions.
- Provide a test panel where users enter representative NL questions and inspect retrieved context and expected tables/metric logic. If connected to the NL2SQL app, display generated SQL and validation outcome, but require explicit user execution permissions for any query.
- Support useful errors: identify the exact table/column/section and what needs correction; do not show raw database credentials or stack traces.
- Provide accessible keyboard navigation, screen-reader labels, responsive layouts, and readable long-table editors.

## 13. Security and privacy requirements

- Enforce TLS for remote database connections and use least-privilege, read-only credentials.
- Do not store database credentials in `SCHEMA.md` or client-side configuration.
- Redact credentials, connection URLs, personal data, and secret-like values from previews and logs.
- Treat table comments, column comments, and database values as untrusted text. They may contain prompt-injection instructions; pass them to an LLM as data, not system instructions.
- Require explicit user approval before profiling sensitive data or sending sensitive metadata to an external LLM.
- Allow column exclusion and sensitivity tags so fields can be omitted from model context and result display.
- Provide audit events for schema export, metadata refresh, profiling, and definition approval.

## 14. Versioning and maintenance

- Include generator/version and schema revision metadata in a human-readable top section or HTML comment that does not interfere with the current parser.
- Record database catalog snapshot time and reviewed business-definition time separately.
- Make repeated generation deterministic: stable ordering of schemas, tables, columns, relationships, definitions, and bullets.
- Support diffing a refreshed catalog against the last export: added, removed, renamed, changed type/nullability/key, and changed view definition.
- Never delete user-authored business meaning simply because a catalog refresh no longer provides it.
- Warn that renames can be hard to distinguish from drop-and-add; request human mapping.

## 15. Acceptance criteria for the first generator release

1. Given a supported database/catalog or a manually entered schema, the user can select objects and export the exact Markdown structure supported by this app.
2. Exported table and column names match the database identifiers exactly.
3. Exported files pass the application’s parser for all included tables, columns, relationships, definitions, and global bullets.
4. The generator differentiates catalog facts, profile observations, user-confirmed semantics, suggestions, and unknowns.
5. It identifies duplicate names, unsupported identifier syntax, unresolved joins, missing row grain, sensitive fields, and unconfirmed metric definitions before marking a schema ready.
6. No credentials or raw sensitive sample rows appear in the exported file.
7. The user can preview the generated file and fix lint errors without manually editing Markdown.
8. A schema can be downloaded and tested with this NL2SQL setup using `SCHEMA_PATH`, while the UI clearly explains that the live database URL, driver, and SQL dialect must also match.
9. A refresh preserves reviewed human-authored semantics and provides a diff rather than silently overwriting them.
10. Representative question tests show retrieved schema context, expected tables, and any known ambiguity; the tool does not claim LLM semantic checks are formal correctness proofs.

## 16. Current NL2SQL application limitations the generator must disclose

- The current parser supports a specific Markdown layout; arbitrary well-formed Markdown is not sufficient.
- It strips a schema prefix from table names internally. Same-name tables in multiple schemas are ambiguous in the current version.
- Its identifier parser handles ordinary ASCII-style object/column names only. Quoted names with spaces, punctuation, or case-sensitive forms need parser/application enhancement before reliable NL2SQL support.
- It performs lexical retrieval, not semantic vector retrieval, and sends only a bounded number of table definitions into a given context. Large schemas require relevance-aware retrieval and mandatory-rule handling.
- SQL dialect text in `SCHEMA.md` informs generation and parsing, but actual support also depends on SQLGlot dialect mapping, SQLAlchemy driver, database connection configuration, and dialect-specific execution behavior.
- The current application validates table names, not a complete column-level catalog binding or formal query equivalence. Semantic validation remains model-based.
- A schema file cannot grant database access or guarantee that its descriptions reflect the live database. The connected database and file must be kept consistent.
- The current app uses PostgreSQL-specific execution controls (`SET TRANSACTION READ ONLY`, `statement_timeout`, and `EXPLAIN`) and is not yet database-agnostic merely because a different dialect is written in the file.

