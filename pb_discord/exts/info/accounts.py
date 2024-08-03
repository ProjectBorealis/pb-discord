import aiohttp
import discord
from discord.ext import commands

from pb_discord import constants
from pb_discord.bot import Bot
from pb_discord.log import get_logger

log = get_logger(__name__)


class Accounts(commands.Cog):
    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        pass

    async def cog_load(self) -> None:
        async with aiohttp.ClientSession(
            base_url=constants.BaseURLs.github_api
        ) as github_api, aiohttp.ClientSession(
            base_url=constants.BaseURLs.site_api,
            headers={"Authorization": f"Bearer {constants.Keys.site_api}"},
        ) as site_api:
            pass


async def setup(bot: Bot) -> None:
    """Load the Accounts cog."""
    await bot.add_cog(Accounts(bot))
