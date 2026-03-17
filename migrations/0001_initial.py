"""Auto-generated migration.

Created: 2026-03-17 09:20:21
"""

depends_on = None


def upgrade(ctx):
    """Apply migration."""
    ctx.create_table(
        "groupmegroup",
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
                'name': 'name',
                'python_type': 'str',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'image_url',
                'python_type': 'str',
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'created_at',
                'python_type': 'int',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'members',
                'python_type': 'dict',
                'db_type': 'JSONB',
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            }
        ],
    )
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
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            }
        ],
        foreign_keys=[
            {
                'name': 'fk_groupmebot_group_id',
                'columns': [
                    'group_id'
                ],
                'ref_table': 'groupmegroup',
                'ref_columns': [
                    'id'
                ],
                'on_delete': 'CASCADE',
                'on_update': 'CASCADE'
            }
        ],
    )
    ctx.create_table(
        "groupmemessage",
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
                'name': 'text',
                'python_type': 'str',
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'system',
                'python_type': 'bool',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': 'FALSE',
                'auto_increment': False
            },
            {
                'name': 'attachments',
                'python_type': 'list',
                'db_type': 'JSONB',
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'timestamp',
                'python_type': 'int',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'group_id',
                'python_type': 'str',
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'sender_id',
                'python_type': 'str',
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            }
        ],
        foreign_keys=[
            {
                'name': 'fk_groupmemessage_group_id',
                'columns': [
                    'group_id'
                ],
                'ref_table': 'groupmegroup',
                'ref_columns': [
                    'id'
                ],
                'on_delete': 'CASCADE',
                'on_update': 'CASCADE'
            },
            {
                'name': 'fk_groupmemessage_sender_id',
                'columns': [
                    'sender_id'
                ],
                'ref_table': 'groupmeuser',
                'ref_columns': [
                    'id'
                ],
                'on_delete': 'SET NULL',
                'on_update': 'CASCADE'
            }
        ],
    )
    ctx.create_table(
        "groupmeuser",
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
                'name': 'name',
                'python_type': 'str',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'image_url',
                'python_type': 'str',
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False
            },
            {
                'name': 'muted',
                'python_type': 'bool',
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': 'FALSE',
                'auto_increment': False
            }
        ],
    )


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_table("groupmeuser")
    ctx.drop_table("groupmemessage")
    ctx.drop_table("groupmebot")
    ctx.drop_table("groupmegroup")
