import discord
from discord.ext import commands

from pb_discord.log import get_logger

log = get_logger(__name__)


class Accounts(commands.Cog):
    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        pass
