"""Auto-generated migration.

Created: 2026-04-21 11:07:49
"""

depends_on = "0004_create_reminder_table"


def upgrade(ctx):
    """Apply migration."""
    ctx.drop_column("groupmemessage", "favorited_by")  # Added manually bc of migration 0003

    ctx.add_column(
        "groupmemessage",
        {
            "name": "favorited_by",
            "python_type": "str[]",
            "db_type": "JSONB",
            "nullable": False,
            "primary_key": False,
            "unique": False,
            "default": "'[]'",
            "auto_increment": False,
        },
    )
    ctx.alter_column("groupmemessage", "group_id", nullable=True)
    ctx.alter_column("reminder", "group_id", nullable=True)
    ctx.alter_column("reminder", "sender_id", nullable=True)


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_column("groupmemessage", "favorited_by")
