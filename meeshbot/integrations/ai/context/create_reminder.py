CREATE_REMINDER_TOOL_DESCRIPTION = """
Create a reminder that MeeshBot will deliver to the group chat at a future time.

This is the same mechanism as the /remindme slash command. The reminder is attributed
to the sender of the most recent message (the one you are responding to): when it fires,
MeeshBot posts the reminder text as a reply to that message and @-mentions that person.

## Guidelines

- Use this only when someone clearly asks to be reminded of something. Never create
  reminders speculatively.
- **The time is resolved server-side** so pass the requester's natural-language phrasing
  (e.g. "in 20 minutes", "tomorrow morning"). Do not attempt to parse the time yourself.
- The tool result includes the resolved delivery time on success. Confirm it to the
  requester in your reply so they can catch a misinterpreted time.
- If the tool returns an error (unresolvable or past time), tell the requester
  conversationally; don't retry with a guessed time.
- To look up existing reminders instead of creating one, use the query_database tool.
"""
