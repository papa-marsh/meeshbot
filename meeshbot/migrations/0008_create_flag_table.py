"""Auto-generated migration.

Created: 2026-07-01 17:14:24
"""

depends_on = "0007_create_ai_db_user"


def upgrade(ctx):
    """Apply migration."""
    ctx.create_table(
        "flag",
        fields=[
            {
                'name': 'key',
                'python_type': 'str',
                'db_type': None,
                'nullable': False,
                'primary_key': True,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'value',
                'python_type': 'bool',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'expires_at',
                'python_type': 'datetime',
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'updated_at',
                'python_type': 'datetime',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            }
        ],
    )


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_table("flag")
