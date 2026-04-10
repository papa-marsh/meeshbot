"""
Interactive shell with pre-loaded meeshbot context.
Run with: make shell
"""

import asyncio

from oxyde import db

from meeshbot.config import DATABASE_URL, TESTING_GROUP_ID
from meeshbot.integrations.groupme.client import GroupMeClient
from meeshbot.models import GroupMeGroup, GroupMeMessage, GroupMeUser

asyncio.run(db.init(default=DATABASE_URL))

client = GroupMeClient()
