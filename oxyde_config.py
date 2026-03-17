import os

DATABASES = {
    "default": os.environ.get(
        "DATABASE_URL", "postgresql://meeshbot:meeshbot@localhost:5432/meeshbot"
    ),
}

MODELS = [
    "meeshbot.models.group",
    "meeshbot.models.user",
    "meeshbot.models.bot",
    "meeshbot.models.message",
]

MIGRATIONS_DIR = "migrations"
