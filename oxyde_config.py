from meeshbot.config import DATABASE_URL

DATABASES = {
    "default": DATABASE_URL,
}

MODELS = [
    "meeshbot.models.group",
    "meeshbot.models.user",
    "meeshbot.models.bot",
    "meeshbot.models.message",
]

MIGRATIONS_DIR = "meeshbot/migrations"
