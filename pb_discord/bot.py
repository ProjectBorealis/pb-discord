import asyncio
import contextlib
import socket
import types
from contextlib import suppress
from sys import exception

import aiohttp
import discord
from discord import app_commands
from discord.errors import Forbidden
from discord.ext import commands

from pb_discord import exts
from pb_discord.log import get_logger
from pb_discord.utils import scheduling
from pb_discord.utils._extensions import walk_extensions
from pb_discord.utils.error_handling import handle_forbidden_from_block
from pb_discord.utils.error_handling.commands import CommandErrorManager

log = get_logger("bot")


class StartupError(Exception):
    """Exception class for startup errors."""

    def __init__(self, base: Exception):
        super().__init__()
        self.exception = base


class CommandTreeBase(app_commands.CommandTree):
    """A sub-class of the Command tree that implements common features that Discord bots use."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Instance is None since discordpy only passes an instance of the client to the command tree in its constructor.
        self.command_error_manager: CommandErrorManager | None = None

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """A callback that is called when any command raises an :exc:`AppCommandError`."""
        if not self.command_error_manager:
            log.warning("Command error manager hasn't been loaded in the command tree.")
            await super().on_error(interaction, error)
            return
        await self.command_error_manager.handle_error(error, interaction)


class Bot(commands.Bot):
    def __init__(
        self,
        *args,
        guild_id: int,
        public_guild_id: int,
        http_session: aiohttp.ClientSession,
        **kwargs,
    ):
        super().__init__(
            *args,
            tree_cls=CommandTreeBase,
            **kwargs,
        )
        self.command_error_manager: CommandErrorManager | None = None
        self.guild_id = guild_id
        self.public_guild_id = public_guild_id
        self.http_session = http_session

        self._resolver: aiohttp.AsyncResolver | None = None
        self._connector: aiohttp.TCPConnector | None = None

        self._guild_available: asyncio.Event | None = None
        self._public_guild_available: asyncio.Event | None = None
        self._extension_loading_task: asyncio.Task | None = None

        self.all_extensions: frozenset[str] | None = None

    def register_command_error_manager(self, manager: CommandErrorManager) -> None:
        """
        Bind an instance of the command error manager to both the bot and the command tree.

        The reason this doesn't happen in the constructor is because error handlers might need an instance of the bot.
        So registration needs to happen once the bot instance has been created.
        """
        self.command_error_manager = manager
        self.tree.command_error_manager = manager

    async def _load_extensions(self, module: types.ModuleType) -> None:
        """Load all the extensions within the given module and save them to ``self.all_extensions``."""
        log.info(
            "Waiting for guilds %d and %d to be available before loading extensions.",
            self.guild_id,
            self.public_guild_id,
        )

        await self.wait_until_guild_available()
        log.info("Loading extensions...")
        self.all_extensions = walk_extensions(module)

        for extension in self.all_extensions:
            scheduling.create_task(self.load_extension(extension))

    async def _sync_app_commands(self) -> None:
        """Sync global & guild specific application commands after extensions are loaded."""
        await self._extension_loading_task
        await self.tree.sync()
        await self.tree.sync(guild=discord.Object(self.public_guild_id))
        await self.tree.sync(guild=discord.Object(self.guild_id))

    async def load_extensions(
        self, module: types.ModuleType, *, sync_app_commands: bool = True
    ) -> None:
        """
        Load all the extensions within the given ``module`` and save them to ``self.all_extensions``.

        Args:
            sync_app_commands: Whether to sync app commands after all extensions are loaded.
        """
        self._extension_loading_task = scheduling.create_task(
            self._load_extensions(module)
        )
        if sync_app_commands:
            scheduling.create_task(self._sync_app_commands())

    def _add_root_aliases(self, command: commands.Command) -> None:
        """Recursively add root aliases for ``command`` and any of its subcommands."""
        if isinstance(command, commands.Group):
            for subcommand in command.commands:
                self._add_root_aliases(subcommand)

        for alias in getattr(command, "root_aliases", ()):
            if alias in self.all_commands:
                raise commands.CommandRegistrationError(alias, alias_conflict=True)

            self.all_commands[alias] = command

    def _remove_root_aliases(self, command: commands.Command) -> None:
        """Recursively remove root aliases for ``command`` and any of its subcommands."""
        if isinstance(command, commands.Group):
            for subcommand in command.commands:
                self._remove_root_aliases(subcommand)

        for alias in getattr(command, "root_aliases", ()):
            self.all_commands.pop(alias, None)

    async def add_cog(self, cog: commands.Cog) -> None:
        """Add the given ``cog`` to the bot and log the operation."""
        await super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")

    def add_command(self, command: commands.Command) -> None:
        """Add ``command`` as normal and then add its root aliases to the bot."""
        super().add_command(command)
        self._add_root_aliases(command)

    def remove_command(self, name: str) -> commands.Command | None:
        """
        Remove a command/alias as normal and then remove its root aliases from the bot.

        Individual root aliases cannot be removed by this function.
        To remove them, either remove the entire command or manually edit `bot.all_commands`.
        """
        command = super().remove_command(name)
        if command is None:
            # Even if it's a root alias, there's no way to get the Bot instance to remove the alias.
            return None

        self._remove_root_aliases(command)
        return command

    def clear(self) -> None:
        """Not implemented! Re-instantiate the bot instead of attempting to re-use a closed one."""
        raise NotImplementedError(
            "Re-using a Bot object after closing it is not supported."
        )

    async def on_guild_unavailable(self, guild: discord.Guild) -> None:
        """Clear the internal guild available event when self.guild_id becomes unavailable."""
        if guild.id == self.guild_id:
            self._guild_available.clear()

        if guild.id == self.public_guild_id:
            self._public_guild_available.clear()

    async def on_guild_available(self, guild: discord.Guild) -> None:
        """
        Set the internal guild available event when self.guild_id becomes available.

        If the cache appears to still be empty (no members, no channels, or no roles), the event
        will not be set and `guild_available_but_cache_empty` event will be emitted.
        """
        if guild.id != self.guild_id and guild.id != self.public_guild_id:
            return

        if not guild.roles or not guild.members or not guild.channels:
            msg = "Guild available event was dispatched but the cache appears to still be empty!"
            await self.log_to_dev_log(msg)
            return

        if guild.id == self.guild_id:
            self._guild_available.set()

        if guild.id == self.public_guild_id:
            self._public_guild_available.set()

    async def wait_until_guild_available(self, key: str | None = None) -> None:
        """
        Wait until the guild that matches the ``guild_id`` given at init is available (and the cache is ready).

        The on_ready event is inadequate because it only waits 2 seconds for a GUILD_CREATE
        gateway event before giving up and thus not populating the cache for unavailable guilds.
        """
        if not key or key == "private":
            await self._guild_available.wait()
        if not key or key == "public":
            await self._public_guild_available.wait()

    async def process_commands(self, message: discord.Message) -> None:
        """
        Overwrite default Discord.py behaviour to process commands only after ensuring extensions are loaded.

        This extension check is only relevant for clients that make use of :obj:`pb_discord.BotBase.load_extensions`.
        """
        if self._extension_loading_task:
            await self._extension_loading_task
        await super().process_commands(message)

    async def setup_hook(self) -> None:
        """
        An async init to startup generic services.
        """
        self._guild_available = asyncio.Event()
        self._public_guild_available = asyncio.Event()

        self._resolver = aiohttp.AsyncResolver()
        self._connector = aiohttp.TCPConnector(
            resolver=self._resolver,
            family=socket.AF_INET,
        )
        self.http.connector = self._connector

        await self.load_extensions(exts)

    async def close(self) -> None:
        """Close the Discord connection, and the aiohttp session, connector, and resolver."""
        # Done before super().close() to allow tasks finish before the HTTP session closes.
        for ext in list(self.extensions):
            with suppress(Exception):
                await self.unload_extension(ext)

        for cog in list(self.cogs):
            with suppress(Exception):
                await self.remove_cog(cog)

        # Now actually do full close of bot
        await super().close()

        if self.http_session:
            await self.http_session.close()

        if self._connector:
            await self._connector.close()

        if self._resolver:
            await self._resolver.close()

    async def on_error(self, event: str, *args, **kwargs) -> None:
        """Log errors raised in event listeners rather than printing them to stderr."""
        e_val = exception()

        if isinstance(e_val, Forbidden):
            message = (
                args[0]
                if event == "on_message"
                else args[1] if event == "on_message_edit" else None
            )

            with contextlib.suppress(Forbidden):
                # Attempt to handle the error. This reraises the error if's not due to a block,
                # in which case the error is suppressed and handled normally. Otherwise, it was
                # handled so return.
                await handle_forbidden_from_block(e_val, message)
                return

        log.exception(f"Unhandled exception in {event}.")
