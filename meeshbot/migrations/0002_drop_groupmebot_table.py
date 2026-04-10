"""Auto-generated migration.

Created: 2026-04-10 12:52:55
"""

depends_on = "0001_create_groupmeuser_table"


def upgrade(ctx):
    """Apply migration."""
    ctx.drop_table("groupmebot")


def downgrade(ctx):
    """Revert migration."""
    ctx.create_table(
        "groupmebot",
        fields=[
                       {
                           'name': 'id',
                           'python_type': 'str',
                           'db_type': None,
                           'nullable': False,
                           'primary_key': True,
                           'unique': False,
                           'default': None,
                           'auto_increment': False
                       },
                       {
                           'name': 'group_id',
                           'python_type': 'str',
                           'db_type': None,
                           'nullable': False,
                           'primary_key': False,
                           'unique': False,
                           'default': None,
                           'auto_increment': False
                       }
                   ],
    )
