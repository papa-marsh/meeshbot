import uvicorn
from fastapi import FastAPI, Request
from structlog.stdlib import get_logger

log = get_logger()

app = FastAPI()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello, world!"}


@app.post("/groupme-webhook")
def groupme_webhook(request: Request, body: dict) -> dict[str, str]:
    log.info(f"Body: {body}")
    log.info(f"Headers: {dict(request.headers)}")
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
