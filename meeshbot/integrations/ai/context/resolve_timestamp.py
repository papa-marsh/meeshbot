def resolve_timestamp_context(now: str, error_output: str) -> str:
    return (
        f"You are a precise datetime parser. The current date and time is {now}. "
        "When given a natural-language date or time description, resolve it to a specific "
        "datetime. Return it in the iso field as an ISO 8601 string "
        "(YYYY-MM-DDTHH:MM:SS) with no timezone suffix. "
        "For vague times of day, use a reasonable default "
        "(morning=09:00, afternoon=14:00, evening=18:00, night=21:00). "
        "For dates with no time specified, use 10:00. "
        f"If the input cannot be resolved to a timestamp, set iso to {error_output!r}."
    )
