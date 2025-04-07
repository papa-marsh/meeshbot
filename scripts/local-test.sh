#!/bin/bash

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 \"message text\""
  exit 1
fi

MESSAGE="$1"

curl -X POST http://localhost:8787 \
  -H "Content-Type: application/json" \
  -d '{
        "text": "'"$MESSAGE"'",
        "sender_type": "user",
        "user_id": "12345",
        "name": "Test User",
        "attachments": []
      }'
