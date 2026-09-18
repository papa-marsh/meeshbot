# meeshbot

GroupMe bot that receives webhook events, persists messages, dispatches slash commands, and generates LLM-driven chat replies via Anthropic or OpenAI. Runs in Docker on a mac mini. Python 3.14, FastAPI, Oxyde ORM, APScheduler, structlog, uv.

## Architecture

A FastAPI endpoint (`POST /groupme-webhook`) receives all inbound GroupMe messages. The handler runs three steps sequentially:

1. **Persist** — every message is synced to Postgres (group, user, and message records created or updated)
2. **Slash command dispatch** — if the message starts with `/`, look up and execute the matching command function
3. **AI response evaluation:** for non-command messages not from MeeshBot itself, run a two-stage LLM pipeline to decide whether and how to reply. Skipped entirely (including the classifier) while the `ai_responses_paused` flag is enabled, set globally via `/timeout <how long>` and cleared via `/timeout done`.

This chain lives in `meeshbot/handlers/groupme.py`. Every message starting with `/` skips AI response evaluation, including unknown commands. Command handlers can still use AI directly, such as timestamp parsing for reminders and timeouts.

### Data flow

GroupMe is the source of truth for messages. The webhook delivers them; meeshbot persists a local copy to Postgres for history queries (LLM context windows, scoreboards). The bot posts replies back to GroupMe via bot IDs — each GroupMe group has a dedicated bot ID mapped in `meeshbot/integrations/groupme/secrets.py`.

**Image history:** Image attachments carry app-owned `metadata` in the message's JSONB array: `status` (`in_progress`, `complete`, `failed`), `updated` (UTC ISO 8601), and a description on completion. Webhook, nightly, and manual sync dispatch background analysis after persistence. Complete images are skipped; missing/failed analysis and `in_progress` metadata at least five minutes old are eligible. Missing or invalid `updated` timestamps are retryable. Retry eligibility uses metadata time, not message age, and is checked only when the message is synced.

`integrations/groupme/image_analysis.py` runs in-process tasks with bounded concurrency and an API-call timeout. Tasks use `AIModel.CHEAP` with the configured provider's image-URL input, do not delay replies, and do not trigger replies on completion. Task references are retained only for lifetime management; persisted metadata determines eligibility. Sync preserves image metadata by URL, and conditional JSONB updates protect concurrent attachment writes. Results apply only to the analysis attempt that started them. No image bytes are downloaded by Meeshbot. Attachment-only messages do not trigger AI response evaluation.

### AI providers and two-prompt pipeline

`meeshbot/integrations/ai/client.py` exposes `AIClient` to application code. It constructs the provider selected by `AI_PROVIDER` (`anthropic` by default, or `openai`). Only the selected provider's API key is required. Unknown provider values fail explicitly. All AI operations, including reminder and `/timeout` timestamp parsing, use this selection.

`AIProvider` in `ai/provider.py` is a protocol for text generation with tools and typed structured generation with an optional image URL. `providers/anthropic.py` and `providers/openai.py` own SDK types, native web tools, image content blocks, and continuation state. Each operation opens and closes its SDK client; an `AIClient` can be reused. Application prompts, output models, history formatting, and tool availability belong to `AIClient`, not the providers.

Callers select capability tiers from `AIModel` in `ai/types.py`: `CHEAP` (Haiku/Luna), `BASIC` (Sonnet/Terra), `POWERFUL` (Opus/Sol), and `FRONTIER` (Fable/Astra). Concrete API model IDs live in each provider's `MODELS` mapping. `POWERFUL` is the client default. Tiers describe model capabilities, not application jobs.

The two-prompt pipeline in `ai/chat.py` keeps the more expensive responder off the ordinary message path:

1. **Classifier (`should_respond`):** selects `BASIC`, scores response likelihood, and checks the configured threshold.
2. **Responder (`send_ai_response`):** selects the default `POWERFUL` tier and generates a reply with web access and eligible client-side tools.

Prompts live in `ai/context/`, one prompt per module, re-exported through the package. History windows live in `ai/chat.py`. Timestamp resolution selects `POWERFUL`.

**Volume:** `GroupMeGroup.response_threshold` persists each group's classifier cutoff, defaulting to 50 (volume 5). `utils/volume.py` shares validation and persistence for `/volume [1-10]` and the `set_volume` tool. Decimals are allowed; the mapping is `threshold = 100 - volume * 10`, with an inclusive score comparison. Any member can change it. Direct requests remain threshold-gated, and volume does not override the global pause. The responder receives the current volume and may choose a target for vague member requests. The volume tool binds `context.group_id` in its executor closure; model arguments cannot select a group. Group sync saves only GroupMe-owned fields so it cannot overwrite concurrent volume changes.

**Tools and continuation:** Client-side tool definitions and executors live in `ai/tools/`. `AIClient` binds them into `AITool` objects, including trusted context in executor closures. Providers dispatch only through the supplied tool list. Unknown/unavailable tools, malformed inputs, and executor failures produce error results for the model. Database queries are unavailable in public groups; `AI_DATABASE_URL` must use a read-only Postgres role. Tool loops have no application iteration cap.

Anthropic replays complete assistant content and appends tool results, including continuation after server-tool `pause_turn`. Its native web search/fetch tools use direct invocation for Haiku. OpenAI uses the Responses API with `store=False`, replays all native output items including encrypted reasoning, and matches function results by `call_id`. Its native web search can open pages; citation URLs are rendered inline in GroupMe text. Neither provider relies on a stored remote conversation.

**Tool identity and trust:** `AIClient.generate_response` requires `context: Context` from `ai/types.py`; prompt text is passed separately as `system_prompt`. Context carries a required group ID and optional sender and triggering-message IDs. `send_ai_response` builds it from the group and webhook; CLI calls without a webhook carry only the group ID. `create_reminder` is available only when both sender and triggering-message IDs are present, and takes only a natural-language time and message from the model. Both AI and slash-command reminders share timestamp resolution, future validation, and persistence in `utils/reminders.py`. Resolving an AI-created reminder invokes a separate `POWERFUL` AI call through that shared core.

**History framing:** `AIClient.build_message_history_entry` emits provider-neutral `AIMessage` values. Human messages have the `user` role, and messages named `MeeshBot` have the `assistant` role. Both carry a `"Sender Name (timestamp): text"` prefix. The responder receives these role-tagged messages as a participant. The classifier receives a single user text block as evidence, with the final message explicitly marked. Preserve this distinction when adding AI features.

Image descriptions follow the message text as `[Image: description]`; missing, in-progress, and failed analysis have explicit placeholders. Unsupported content attachments render an inability-to-analyze placeholder; mentions and reply references are omitted. Both classifier and responder use this shared rendering. Image descriptions are untrusted attachment content, not instructions.

**Structured outputs and budgets:** `AIClient` supplies Pydantic models to `provider.generate_structured`, implemented with Anthropic `messages.parse` or OpenAI `responses.parse`. Missing or incomplete parsed output raises; it never silently becomes a result. Keep output models private when callers receive an extracted value. Put justification fields before answer fields when reasoning-first generation helps. Non-frontier structured calls disable thinking/reasoning to keep small output budgets usable. Frontier calls use low effort and an 8,192-token budget floor because reasoning shares the output limit; this is an allowance, not a completion guarantee. OpenAI rejects incomplete text responses. Anthropic text generation returns the latest nonempty text on a terminal stop, including truncation. There is no application retry with a larger budget.

### Scheduler

APScheduler runs independent cron jobs registered in `scheduled/scheduler.py`. The scheduler starts and stops via `scheduler_lifespan()`, composed into the app lifespan alongside the database connection in `app.py`.

- **`scheduler_heartbeat`** — runs hourly; logs a heartbeat for observability
- **`send_due_reminders`** — runs every minute; queries and dispatches due reminders
- **`sync_recent_messages`** — runs nightly at 4 AM; backfills the last 7 days of messages across all groups from the GroupMe API

## Codebase

All application code lives in `meeshbot/`.

- **`app.py`** — FastAPI app, lifespan management (DB + scheduler), route definitions
- **`config.py`** — environment variable reads (API keys, database URL, timezone)
- **`handlers/`** — webhook handler that orchestrates persist → command → AI response
- **`commands/`** — one module per slash command. Each exports an async function taking `GroupMeWebhookPayload`. Registered in `commands/registry.py`, re-exported from `commands/__init__.py`.
- **`integrations/groupme/`** — `client.py` (GroupMe API client, posts via bot IDs), `types.py` (Pydantic models for webhook payloads, messages, groups), `queries.py` (DB operations for messages/users/groups), `secrets.py` (bot ID mappings, admin user IDs, public group IDs)
- **`integrations/ai/`:** application-facing client and pipeline, provider protocol and neutral types, shared tools, and concrete SDK adapters under `providers/`
- **`models/`** — Oxyde ORM models: `GroupMeGroup`, `GroupMeUser`, `GroupMeMessage`, `Reminder`, `Flag`. Each has a corresponding `.pyi` stub auto-generated by Oxyde.
- **`scheduled/`** — `scheduler.py` (APScheduler config, job registration), `reminders.py` (queries for due reminders, dispatches them to GroupMe), `message_sync.py` (nightly backfill of recent messages from GroupMe API)
- **`utils/`** — `logging.py` (structlog configuration), `dates.py` (timezone-aware datetime helpers), `flags.py` (persistent boolean flags with optional expiry, backed by the `Flag` model; add new keys to `FlagKey`), `reminders.py` (reminder creation core shared by the `/remindme` command and the `create_reminder` tool)
- **`migrations/`** — auto-generated by Oxyde. Excluded from linting and type checking.

## Extending

### Adding a command

1. Create `meeshbot/commands/<name>.py` with an async function taking `GroupMeWebhookPayload`:

```python
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

async def mycommand(webhook: GroupMeWebhookPayload) -> None:
    await GroupMeClient().post_message(group_id=webhook.group_id, text="response")
```

2. Re-export from `meeshbot/commands/__init__.py`
3. Register in `meeshbot/commands/registry.py` under `COMMAND_REGISTRY`

Two decorators are available in `registry.py`: `admin_only` (gates on `ADMIN_USER_IDS`) and `no_public` (blocks in public groups). They compose: `no_public(admin_only(func))`.

### Adding a model

1. Create `meeshbot/models/<name>.py` with an Oxyde `Model` subclass
2. Export from `meeshbot/models/__init__.py`
3. Register the module path in `oxyde_config.py` under `MODELS`
4. Run `uv run oxyde makemigrations` to generate migration files and `.pyi` stubs

### Adding LLM features

- New system prompts belong in their own modules in `integrations/ai/context/`.
- New structured-output features belong on `AIClient`, with a Pydantic output model and a call to `provider.generate_structured`. Keep SDK types inside concrete providers.
- History fetching, prompt assembly, and output dispatch belong in `ai/chat.py`.
- New client-side tools need a `ToolDefinition` and async executor in `ai/tools/`, then an `AITool` binding in `AIClient.generate_response`. The shared schema supports required string parameters. Bind identity server-side using `Context`; never take trusted IDs from model arguments. Both providers dispatch generically, so adding a client-side tool does not require editing their loops.
- New providers implement `AIProvider`, map every `AIModel` tier, and are wired into `AIClient` selection. Native web tools and their limits stay provider-specific.

### Adding a scheduled job

Add the job function in `scheduled/` and register it with the scheduler in `scheduled/scheduler.py` using `scheduler.add_job`. Use the existing jobs as reference for trigger config.

## Operations

### Dependencies

Uses **uv**. Do not use `pip` directly.

```bash
uv add <package>            # add runtime dep
uv add --dev <package>      # add to [dependency-groups.dev]
uv sync                     # install all deps
uv run <command>            # run in venv
```

### Running / deploying

Runs in Docker Compose (FastAPI + Postgres). Both services use `restart: unless-stopped` to recover after process exits and Docker daemon restarts; explicitly stopped containers stay stopped. The `meeshbot/` directory is volume-mounted; restart the application container to load code edits. Uvicorn runs without a reloader so application startup failures exit the container and allow Docker to retry.

```bash
just deploy                 # docker down → build → up → migrate → tail logs
just logs                   # tail logs
just shell                  # IPython shell inside the running container
just pull-deploy            # git pull + just deploy (used on mac mini)
```

`just deploy` runs `uv run oxyde migrate` inside the container after startup — migrations are applied automatically on every deploy.

### Linting & types

```bash
uv run ruff check meeshbot     # lint
uv run ruff format meeshbot    # format
uv run mypy meeshbot           # type check
```

AI tests run with `uv run pytest tests`. They use `asyncio.run` and real SDKs backed by mocked HTTP transports, with no API credentials, database, or GroupMe calls required. Run `uv run ruff check meeshbot tests` to lint both application and test code.

Ruff and mypy both exclude `meeshbot/migrations/`. Ruff also excludes model `.pyi` stubs; mypy ignores errors in `meeshbot.models.*` via a pyproject override because the auto-generated stubs don't type-check cleanly (model usage is still checked at call sites). Strict mypy — all functions must be fully typed.

Custom logic must not live on model classes — the generated `.pyi` stubs shadow the module for mypy, so any methods added to a model are invisible to the type checker. Put model-adjacent logic in a separate module (e.g. `utils/flags.py` for `Flag`).

### Oxyde ORM

Django-style async ORM with a Rust core ([docs](https://github.com/mr-fatalyst/oxyde)). Config is in `oxyde_config.py` at the repo root. Use existing model definitions and query patterns as reference when adding or extending DB operations.

Oxyde is in alpha. The fork at `~/Repositories/oxyde` can be used for simple fixes — the upstream maintainer is responsive to PRs.

### Datetimes and Oxyde

Datetime columns are `timestamp` (no timezone). Oxyde serializes datetime values as ISO strings, and its Rust core normalizes offset-aware values to UTC before binding, so the database stores UTC wall time. On read, Oxyde decodes `timestamp` columns as **naive UTC** datetimes. Application code uses timezone-aware datetimes (`local_now()` in `utils/dates.py`). Rules that follow:

- **SQL-side comparisons are safe with aware values** (e.g. `eta__lte=local_now()`): filter values pass through the same UTC normalization as stored values
- **Python-side comparisons against a loaded datetime must attach UTC first**: `loaded_dt.replace(tzinfo=UTC) <= local_now()`. Comparing naive to aware raises `TypeError`. See `flag_enabled` in `utils/flags.py`.
- **Formatting loaded datetimes for display works via `.astimezone(TIMEZONE)`** (`verbose_datetime`): Python interprets naive datetimes as system-local time, and the container runs in UTC

### Primary branch

`main`
