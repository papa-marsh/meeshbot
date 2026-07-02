from meeshbot.config import DATABASE_URL

DATABASES = {
    "default": DATABASE_URL,
}

MODELS = [
    "meeshbot.models.group",
    "meeshbot.models.user",
    "meeshbot.models.message",
    "meeshbot.models.reminder",
    "meeshbot.models.flag",
]

MIGRATIONS_DIR = "meeshbot/migrations"
