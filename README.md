# MeeshBot

GroupMe bot powered by Anthropic or OpenAI. Receives webhook events, responds to messages, and handles slash commands. Runs in Docker on a mac mini.

Built with Python 3.14, FastAPI, Postgres, APScheduler, and uv.

## Features

**AI replies:** evaluates eligible incoming messages with a cheap classifier before generating a reply with a stronger model. The responder has web access, database queries in private groups, and reminder creation tied to the sender's message.

**Slash commands:** extensible command dispatch. Current commands:

| Command | Description |
|---|---|
| `/remindme <time> - <message>` | Set a reminder; time is parsed via LLM (natural language works) |
| `/reminders` | List pending reminders |
| `/scoreboard` | Message count leaderboard for the current group |
| `/scoreboard-all` | All-time leaderboard across all groups |
| `/roll` | Roll a dice |
| `/ping` | Health check |
| `/help` | List available commands |

**Message persistence:** all messages are synced to Postgres on receipt, providing history for AI context windows and scoreboard queries. A nightly job backfills the last 7 days from the GroupMe API.

## AI configuration

Set `AI_PROVIDER=anthropic` (the default) with `ANTHROPIC_API_KEY`, or `AI_PROVIDER=openai` with `OPENAI_API_KEY` in `.env`. Only the selected provider's key is required. This selection covers replies, classification, and natural-language time parsing. See `.env.example` for the other service settings.

Application code chooses `AIModel.CHEAP`, `BASIC`, `POWERFUL`, or `FRONTIER`. Providers map these to Haiku/Luna, Sonnet/Terra, Opus/Sol, and Fable/Astra respectively. Classification uses `CHEAP`, replies default to `BASIC`, and time parsing uses `POWERFUL`. API model IDs live in `meeshbot/integrations/ai/providers/`.

Anthropic provides native web search and fetch; OpenAI uses native web search with page-opening support and inline citation URLs. Frontier models require reasoning and use a larger output budget allowance.

## Running

```bash
just deploy       # build and start (runs migrations automatically)
just logs         # tail logs
just shell        # IPython shell inside the running container
just pull-deploy  # git pull + deploy (used in production)
```
