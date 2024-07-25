import asyncio

import aiohttp
import discord
from discord.ext import commands

import pb_discord
from pb_discord import constants
from pb_discord.bot import Bot
from pb_discord.log import get_logger


async def main():
    """Entry async method for starting the bot."""
    intents = discord.Intents.all()
    intents.presences = False
    intents.dm_typing = False
    intents.dm_reactions = False
    intents.invites = False
    intents.webhooks = False
    intents.integrations = False

    async with aiohttp.ClientSession() as session:
        pb_discord.instance = Bot(
            guild_id=constants.Guild.id,
            public_guild_id=constants.Guild.public,
            http_session=session,
            command_prefix=commands.when_mentioned_or(constants.Bot.prefix),
            # activity=discord.Game(name=f"Commands: {constants.Bot.prefix}help"),
            case_insensitive=True,
            max_messages=10_000,
            allowed_mentions=discord.AllowedMentions(everyone=False),
            intents=intents,
        )
        async with pb_discord.instance as _bot:
            await _bot.start(constants.Bot.token)


def start():
    try:
        asyncio.run(main())
    except Exception as e:
        message = "Unknown Startup Error Occurred."

        # The exception is logged with an empty message so the actual message is visible at the bottom
        log = get_logger("bot")
        log.fatal("", exc_info=e)
        log.fatal(message)

        exit(69)
