import os

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request

AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")


def require_auth_token(request: Request) -> None:
    """Reject requests that are missing or present an invalid X-Auth-Token header."""
    token = request.headers.get("X-Auth-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="X-Auth-Token header required")
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


app = FastAPI(dependencies=[Depends(require_auth_token)])


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello, world!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
