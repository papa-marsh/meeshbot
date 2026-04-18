"""Auto-generated migration.

Created: 2026-04-17 22:05:38
"""

depends_on = "0002_drop_groupmebot_table"


def upgrade(ctx):
    """Apply migration."""
    ctx.add_column(
        "groupmemessage",
        {
            "name": "favorited_by",
            "python_type": "str[]",
            "db_type": "JSONB",
            "nullable": False,
            "primary_key": False,
            "unique": False,
            "default": "[]",
            "auto_increment": False,
        },
    )


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_column("groupmemessage", "favorited_by")
