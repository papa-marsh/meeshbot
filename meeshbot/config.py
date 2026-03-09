import os
from zoneinfo import ZoneInfo

AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLALCHEMY_TRACK_MODIFICATIONS = False

TIMEZONE = ZoneInfo(os.environ.get("TIMEZONE", "America/New_York"))
