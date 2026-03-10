import os
from zoneinfo import ZoneInfo

GROUPME_TOKEN = os.environ.get("GROUPME_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BALLDONTLIE_API_KEY = os.environ.get("BALLDONTLIE_API_KEY", "")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLALCHEMY_TRACK_MODIFICATIONS = False

TIMEZONE = ZoneInfo(os.environ.get("TIMEZONE", "America/New_York"))
