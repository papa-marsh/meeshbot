"""Auto-generated migration.

Created: 2026-04-21 21:56:44
"""

depends_on = "0005_add_favorited_by_to_groupmemessage"


def upgrade(ctx):
    """Apply migration."""
    ctx.drop_column("groupmemessage", "favorited_by")


def downgrade(ctx):
    """Revert migration."""
    ctx.add_column("groupmemessage", {
    'name': 'favorited_by',
    'python_type': 'str[]',
    'db_type': 'JSONB',
    'nullable': False,
    'primary_key': False,
    'unique': False,
    'default': "'[]'",
    'auto_increment': False
})
