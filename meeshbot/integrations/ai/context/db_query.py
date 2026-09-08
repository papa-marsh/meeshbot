DB_QUERY_TOOL_DESCRIPTION = """
Execute a read-only SQL SELECT query against the meeshbot Postgres database.

MeeshBot's database persists relational data for group chat groups, users, and messages.
Use this tool for read-only queries for any info relevant to the task at hand.

## Guidelines

- Only SELECT statements are permitted; any data mutation will be rejected.
- You may invoke this tool multiple times if you need to orient yourself (e.g. which groups exist).
- Listing all users and groups is cheap; query them liberally to improve your contextual awareness.
- The current group's ID is available in the conversation context; you can use it to scope queries if needed.
- Limit `groupmemessage` queries to a reasonable number of rows (e.g. LIMIT 200) per query.
- Results are returned as a JSON array of row objects.
- You do not need to use this for querying recent message context; this is provided in the prompt's conversation history.

## Schema

### groupmegroup
Represents a GroupMe chat group (Table size: 5-10 rows).
- id (text, PK): GroupMe's group ID
- name (text): display name of the group
- image_url (text, nullable): group avatar URL
- created_at (timestamptz): when the group was first seen by meeshbot

### groupmeuser
Represents a GroupMe chat member (Table size: 10-20 rows).
- id (text, PK): GroupMe's user ID
- name (text): display name
- image_url (text, nullable): avatar URL
- muted (boolean): whether the bot ignores this user's messages

### groupmemessage
Every message sent in any tracked group (Table size: 10k-100k).
- id (text, PK): GroupMe's message ID
- group_id (text, FK → groupmegroup.id): which group the message was sent in (JOIN to get group name)
- sender_id (text, FK → groupmeuser.id): who sent the message (JOIN to get user name)
- text (text, nullable): message body (null for attachment-only messages)
- system (boolean): true for system events (membership changes, etc.), false for user messages
- attachments (jsonb): array of attachment objects from GroupMe (images, mentions, etc.)
- timestamp (timestamptz): when the message was sent (stored in UTC but the group is in the Eastern US)

### reminder
Scheduled reminders, created via the /remindme command or the create_reminder tool (Table size: 10-100 rows).
- id (text, PK): UUID
- group_id (text, FK → groupmegroup.id): group the reminder will be delivered in
- sender_id (text, FK → groupmeuser.id): who the reminder is for (JOIN to get user name)
- command_message_id (text): ID of the message that requested the reminder
- message (text): reminder body text
- eta (timestamp): when the reminder fires (stored in UTC but the group is in the Eastern US)
- created_at (timestamp): when the reminder was created (stored in UTC)
- sent (boolean): true once the reminder has been delivered; pending reminders are sent=false
"""
