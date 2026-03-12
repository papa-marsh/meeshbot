import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response
from structlog.stdlib import get_logger

from meeshbot.config import GROUPME_WEBHOOK_TOKEN
from meeshbot.handlers.groupme import handle_groupme_webhook
from meeshbot.integrations.groupme.types import GroupMeWebhookPayload

log = get_logger()

app = FastAPI()


@app.api_route("/", methods=["GET", "HEAD"])
def root() -> Response:
    return Response(status_code=204)


@app.post("/groupme-webhook")
def groupme_webhook(body: GroupMeWebhookPayload, token: str = Query(default="")) -> Response:
    if token != GROUPME_WEBHOOK_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    log.info("GroupMe webhook received", group_id=body.group_id, name=body.name)

    handle_groupme_webhook(body)

    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
