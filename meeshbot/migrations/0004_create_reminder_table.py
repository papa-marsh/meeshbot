"""Auto-generated migration.

Created: 2026-04-19 07:55:07
"""

depends_on = "0003_add_favorited_by_to_groupmemessage"


def upgrade(ctx):
    """Apply migration."""
    ctx.create_table(
        "reminder",
        fields=[
            {
                "name": "id",
                "python_type": "str",
                "db_type": None,
                "nullable": False,
                "primary_key": True,
                "unique": False,
                "default": None,
                "auto_increment": False,
            },
            {
                "name": "command_message_id",
                "python_type": "str",
                "db_type": None,
                "nullable": False,
                "primary_key": False,
                "unique": False,
                "default": None,
                "auto_increment": False,
            },
            {
                "name": "message",
                "python_type": "str",
                "db_type": None,
                "nullable": False,
                "primary_key": False,
                "unique": False,
                "default": None,
                "auto_increment": False,
            },
            {
                "name": "eta",
                "python_type": "datetime",
                "db_type": None,
                "nullable": False,
                "primary_key": False,
                "unique": False,
                "default": None,
                "auto_increment": False,
            },
            {
                "name": "created_at",
                "python_type": "datetime",
                "db_type": None,
                "nullable": False,
                "primary_key": False,
                "unique": False,
                "default": None,
                "auto_increment": False,
            },
            {
                "name": "sent",
                "python_type": "bool",
                "db_type": None,
                "nullable": False,
                "primary_key": False,
                "unique": False,
                "default": "FALSE",
                "auto_increment": False,
            },
            {
                "name": "group_id",
                "python_type": "str",
                "db_type": None,
                "nullable": False,
                "primary_key": False,
                "unique": False,
                "default": None,
                "auto_increment": False,
            },
            {
                "name": "sender_id",
                "python_type": "str",
                "db_type": None,
                "nullable": False,
                "primary_key": False,
                "unique": False,
                "default": None,
                "auto_increment": False,
            },
        ],
        foreign_keys=[
            {
                "name": "fk_reminder_group_id",
                "columns": ["group_id"],
                "ref_table": "groupmegroup",
                "ref_columns": ["id"],
                "on_delete": "CASCADE",
                "on_update": "CASCADE",
            },
            {
                "name": "fk_reminder_sender_id",
                "columns": ["sender_id"],
                "ref_table": "groupmeuser",
                "ref_columns": ["id"],
                "on_delete": "CASCADE",
                "on_update": "CASCADE",
            },
        ],
    )


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_table("reminder")
