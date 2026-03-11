"""
Interactive shell with pre-loaded meeshbot context.
Run with: uv run --env-file .env ipython -i meeshbot/shell.py
"""

from meeshbot.config import TESTING_GROUP_ID
from meeshbot.integrations.groupme.client import GroupMeClient

client = GroupMeClient()
