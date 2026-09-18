"""Auto-generated migration.

Created: 2026-09-18 10:47:56
"""

depends_on = "0008_create_flag_table"


def upgrade(ctx):
    """Apply migration."""
    ctx.add_column("groupmegroup", {
    'name': 'response_threshold',
    'python_type': 'float',
    'db_type': None,
    'nullable': False,
    'primary_key': False,
    'unique': False,
    'default': '50.0',
    'auto_increment': False
})


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_column("groupmegroup", "response_threshold")
