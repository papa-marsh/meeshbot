import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response
from oxyde import db
from structlog.stdlib import get_logger

from meeshbot.config import DATABASE_URL, GROUPME_WEBHOOK_TOKEN
from meeshbot.handlers.groupme import handle_groupme_webhook
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

log = get_logger()

app = FastAPI(lifespan=db.lifespan(default=DATABASE_URL))


@app.api_route("/", methods=["GET", "HEAD"])
async def root() -> Response:
    return Response(status_code=204)


@app.post("/groupme-webhook")
async def groupme_webhook(body: GroupMeWebhookPayload, token: str = Query(default="")) -> Response:
    if token != GROUPME_WEBHOOK_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    log.info("GroupMe webhook received", group_id=body.group_id, name=body.name)

    await handle_groupme_webhook(body)

    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
