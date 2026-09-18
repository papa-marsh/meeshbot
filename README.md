# MeeshBot

GroupMe bot powered by Anthropic or OpenAI. Receives webhook events, responds to messages, and handles slash commands. Runs in Docker on a mac mini.

Built with Python 3.14, FastAPI, Postgres, APScheduler, and uv.

## Features

**AI replies:** evaluates eligible incoming messages with a cheap classifier before generating a reply with a stronger model. Messages starting with `/` skip AI response evaluation, including unknown commands. The responder has web access, database queries in private groups, reminder creation tied to the sender's message, and a tool to adjust the group's volume on request.

**Volume:** each group has a persistent talkativeness level from 1 (quietest) to 10 (most talkative), defaulting to 5. Any member can set it with `/volume 7`, check it with `/volume`, or ask MeeshBot to talk more or less. Decimals are supported. Volume maps to a response score cutoff of `100 - volume × 10`, not a response probability. Direct requests still pass through that cutoff; `/volume` works even while AI replies are paused.

**Slash commands:** extensible command dispatch. Current commands:

| Command | Description |
|---|---|
| `/remindme <time> - <message>` | Set a reminder; time is parsed via LLM (natural language works) |
| `/reminders` | List pending reminders |
| `/volume [1-10]` | Show or set this group's talkativeness; decimals allowed |
| `/scoreboard` | Message count leaderboard for the current group |
| `/scoreboard-all` | All-time leaderboard across all groups |
| `/roll` | Roll a dice |
| `/ping` | Health check |
| `/help` | List available commands |

**Message persistence:** all messages are synced to Postgres on receipt, providing history for AI context windows and scoreboard queries. A nightly job backfills the last 7 days from the GroupMe API.

**Image understanding:** images are described in the background and saved alongside their attachment URLs. Descriptions appear in AI conversation history, with explicit placeholders while analysis is pending or if it fails. Other content attachments are labeled but not analyzed. Live, nightly, and manual sync share the same rules: completed descriptions are preserved, failed analysis is retried, and in-progress analysis can be retried after five minutes. Replies do not wait for image analysis, and completing it does not trigger a reply.

## AI configuration

Set `AI_PROVIDER=anthropic` (the default) with `ANTHROPIC_API_KEY`, or `AI_PROVIDER=openai` with `OPENAI_API_KEY` in `.env`. Only the selected provider's key is required. This selection covers replies, classification, image descriptions, and natural-language time parsing. Image URLs are sent to that provider for analysis. See `.env.example` for the other service settings.

Application code chooses `AIModel.CHEAP`, `BASIC`, `POWERFUL`, or `FRONTIER`. Providers map these to Haiku/Luna, Sonnet/Terra, Opus/Sol, and Fable/Astra respectively. Image descriptions use `CHEAP`, classification uses `BASIC`, replies default to `POWERFUL`, and time parsing uses `POWERFUL`. API model IDs live in `meeshbot/integrations/ai/providers/`.

Anthropic provides native web search and fetch; OpenAI uses native web search with page-opening support and inline citation URLs. Frontier models require reasoning and use a larger output budget allowance.

## Running

```bash
just deploy       # build and start (runs migrations automatically)
just logs         # tail logs
just shell        # IPython shell inside the running container
just pull-deploy  # git pull + deploy (used in production)
```
