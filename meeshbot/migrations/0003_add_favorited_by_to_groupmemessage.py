"""Auto-generated migration.

Created: 2026-04-17 22:05:38
"""

depends_on = "0002_drop_groupmebot_table"


def upgrade(ctx):
    """Apply migration."""
    ctx.execute(
        "ALTER TABLE groupmemessage ADD COLUMN favorited_by JSONB NOT NULL DEFAULT '[]'::jsonb"
    )


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_column("groupmemessage", "favorited_by")
