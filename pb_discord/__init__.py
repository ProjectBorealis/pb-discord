import asyncio
import os
from typing import TYPE_CHECKING

from pb_discord import log
from pb_discord.utils import apply_monkey_patches

if TYPE_CHECKING:
    from pb_discord.bot import Bot

log.setup()

# On Windows, the selector event loop is required for aiodns.
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

apply_monkey_patches()

instance: "Bot" = None  # Global Bot instance.
