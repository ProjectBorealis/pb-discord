import copy
import difflib

import discord
from discord import ButtonStyle, Embed, Forbidden, Interaction, Member, User
from discord.ext.commands import (
    ChannelNotFound,
    Cog,
    Context,
    TextChannelConverter,
    VoiceChannelConverter,
    errors,
)

from pb_discord.bot import Bot
from pb_discord.constants import Colours, Icons
from pb_discord.log import get_logger
from pb_discord.utils.error_handling import handle_forbidden_from_block
from pb_discord.utils.interactions import DeleteMessageButton, ViewWithUserAndRoleCheck

log = get_logger(__name__)


class HelpEmbedView(ViewWithUserAndRoleCheck):
    """View to allow showing the help command for command error responses."""

    def __init__(self, help_embed: Embed, owner: User | Member):
        super().__init__(allowed_users=[owner.id])
        self.help_embed = help_embed

        self.delete_button = DeleteMessageButton()
        self.add_item(self.delete_button)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Overriden check to allow anyone to use the help button."""
        if (interaction.data or {}).get("custom_id") == self.help_button.custom_id:
            log.trace(
                "Allowed interaction by %s (%d) on %d as interaction was with the help button.",
                interaction.user,
                interaction.user.id,
                interaction.message.id,
            )
            return True

        return await super().interaction_check(interaction)

    @discord.ui.button(label="Help", style=ButtonStyle.primary)
    async def help_button(
        self, interaction: Interaction, button: discord.ui.Button
    ) -> None:
        """Send an ephemeral message with the contents of the help command."""
        await interaction.response.send_message(embed=self.help_embed, ephemeral=True)


class ErrorHandler(Cog):
    """Handles errors emitted from commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    def _get_error_embed(self, title: str, body: str) -> Embed:
        """Return an embed that contains the exception."""
        return Embed(title=title, colour=Colours.soft_red, description=body)

    @Cog.listener()
    async def on_command_error(self, ctx: Context, e: errors.CommandError) -> None:
        """
        Provide generic command error handling.

        Error handling is deferred to any local error handler, if present. This is done by
        checking for the presence of a `handled` attribute on the error.

        Error handling emits a single error message in the invoking context `ctx` and a log message,
        prioritised as follows:

        1. If the name fails to match a command:
            * If it matches shh+ or unshh+, the channel is silenced or unsilenced respectively.
              Otherwise if it matches a tag, the tag is invoked
            * If CommandNotFound is raised when invoking the tag (determined by the presence of the
              `invoked_from_error_handler` attribute), this error is treated as being unexpected
              and therefore sends an error message
        2. UserInputError: see `handle_user_input_error`
        3. CheckFailure: see `handle_check_failure`
        4. CommandOnCooldown: send an error message in the invoking context
        5. Otherwise, if not a DisabledCommand, handling is deferred to `handle_unexpected_error`
        """
        command = ctx.command

        if hasattr(e, "handled"):
            log.trace(
                f"Command {command} had its error already handled locally; ignoring."
            )
            return

        debug_message = (
            f"Command {command} invoked by {ctx.message.author} with error "
            f"{e.__class__.__name__}: {e}"
        )

        if isinstance(e, errors.CommandNotFound) and not getattr(
            ctx, "invoked_from_error_handler", False
        ):
            # We might not invoke a command from the error handler, but it's easier and safer to ensure
            # this is always set rather than trying to get it exact, and shouldn't cause any issues.
            ctx.invoked_from_error_handler = True

            # All errors from attempting to execute these commands should be handled by the error handler.
            # We wrap non CommandErrors in CommandInvokeError to mirror the behaviour of normal commands.
            try:
                if await self.try_silence(ctx):
                    return
                if await self.try_run_fixed_codeblock(ctx):
                    return
                await self.try_get_tag(ctx)
            except Exception as err:
                log.info("Re-handling error raised by command in error handler")
                if isinstance(err, errors.CommandError):
                    await self.on_command_error(ctx, err)
                else:
                    await self.on_command_error(ctx, errors.CommandInvokeError(err))
        elif isinstance(e, errors.UserInputError):
            log.debug(debug_message)
            await self.handle_user_input_error(ctx, e)
        elif isinstance(e, errors.CheckFailure):
            log.debug(debug_message)
            await self.handle_check_failure(ctx, e)
        elif isinstance(e, errors.CommandOnCooldown | errors.MaxConcurrencyReached):
            log.debug(debug_message)
            await ctx.send(e)
        elif isinstance(e, errors.CommandInvokeError):
            if isinstance(e.original, Forbidden):
                try:
                    await handle_forbidden_from_block(e.original, ctx.message)
                except Forbidden:
                    await self.handle_unexpected_error(ctx, e.original)
            else:
                await self.handle_unexpected_error(ctx, e.original)
        elif isinstance(e, errors.ConversionError):
            await self.handle_unexpected_error(ctx, e.original)
        elif isinstance(e, errors.DisabledCommand):
            log.debug(debug_message)
        else:
            # ExtensionError
            await self.handle_unexpected_error(ctx, e)

    async def try_silence(self, ctx: Context) -> bool:
        """
        Attempt to invoke the silence or unsilence command if invoke with matches a pattern.

        Respecting the checks if:
        * invoked with `shh+` silence channel for amount of h's*2 with max of 15.
        * invoked with `unshh+` unsilence channel
        Return bool depending on success of command.
        """
        silence_command = self.bot.get_command("silence")
        if not silence_command:
            log.debug(
                "Not attempting to parse message as `shh`/`unshh` as could not find `silence` command."
            )
            return False

        command = ctx.invoked_with.lower()
        args = ctx.message.content.lower().split(" ")

        try:
            if not await silence_command.can_run(ctx):
                log.debug(
                    "Cancelling attempt to invoke silence/unsilence due to failed checks."
                )
                return False
        except errors.CommandError:
            log.debug(
                "Cancelling attempt to invoke silence/unsilence due to failed checks."
            )
            return False

        # Parse optional args
        channel = None
        duration = min(command.count("h") * 2, 15)
        kick = False

        if len(args) > 1:
            # Parse channel
            for converter in (TextChannelConverter(), VoiceChannelConverter()):
                try:
                    channel = await converter.convert(ctx, args[1])
                    break
                except ChannelNotFound:
                    continue

        if len(args) > 2 and channel is not None:
            # Parse kick
            kick = args[2].lower() == "true"

        if command.startswith("shh"):
            await ctx.invoke(
                silence_command,
                duration_or_channel=channel,
                duration=duration,
                kick=kick,
            )
            return True
        if command.startswith("unshh"):
            await ctx.invoke(self.bot.get_command("unsilence"), channel=channel)
            return True
        return False

    async def try_get_tag(self, ctx: Context) -> None:
        """Attempt to display a tag by interpreting the command name as a tag name."""
        tags_cog = self.bot.get_cog("Tags")
        if not tags_cog:
            log.debug(
                "Not attempting to parse message as a tag as could not find `Tags` cog."
            )
            return
        tags_get_command = tags_cog.get_command_ctx

        maybe_tag_name = ctx.invoked_with
        if not maybe_tag_name or not isinstance(ctx.author, Member):
            return

        try:
            if not await self.bot.can_run(ctx):
                log.debug(
                    "Cancelling attempt to fall back to a tag due to failed checks."
                )
                return
        except errors.CommandError:
            log.debug("Cancelling attempt to fall back to a tag due to failed checks.")
            return

        if await tags_get_command(ctx, maybe_tag_name):
            return

        await self.send_command_suggestion(ctx, maybe_tag_name)

    async def try_run_fixed_codeblock(self, ctx: Context) -> bool:
        """
        Attempt to run eval or timeit command with triple backticks directly after command.

        For example: !eval```print("hi")```

        Return True if command was invoked, else False
        """
        msg = copy.copy(ctx.message)

        command, sep, end = msg.content.partition("```")
        msg.content = command + " " + sep + end
        new_ctx = await self.bot.get_context(msg)

        if new_ctx.command is None:
            return False

        allowed_commands = [
            self.bot.get_command("eval"),
            self.bot.get_command("timeit"),
        ]

        if new_ctx.command not in allowed_commands:
            return False

        log.debug(
            "Running %r command with fixed codeblock.", new_ctx.command.qualified_name
        )
        new_ctx.invoked_from_error_handler = True
        await self.bot.invoke(new_ctx)

        return True

    async def send_command_suggestion(self, ctx: Context, command_name: str) -> None:
        """Sends user similar commands if any can be found."""
        # No similar tag found, or tag on cooldown -
        # searching for a similar command
        raw_commands = []
        for cmd in self.bot.walk_commands():
            if not cmd.hidden:
                raw_commands += (cmd.name, *cmd.aliases)
        if similar_command_data := difflib.get_close_matches(
            command_name, raw_commands, 1
        ):
            similar_command_name = similar_command_data[0]
            similar_command = self.bot.get_command(similar_command_name)

            if not similar_command:
                return

            log_msg = "Cancelling attempt to suggest a command due to failed checks."
            try:
                if not await similar_command.can_run(ctx):
                    log.debug(log_msg)
                    return
            except errors.CommandError as cmd_error:
                log.debug(log_msg)
                await self.on_command_error(ctx, cmd_error)
                return

            misspelled_content = ctx.message.content
            e = Embed()
            e.set_author(name="Did you mean:", icon_url=Icons.questionmark)
            e.description = (
                f"{misspelled_content.replace(command_name, similar_command_name, 1)}"
            )
            await ctx.send(embed=e, delete_after=10.0)

    async def handle_user_input_error(
        self, ctx: Context, e: errors.UserInputError
    ) -> None:
        """
        Send an error message in `ctx` for UserInputError, sometimes invoking the help command too.

        * MissingRequiredArgument: send an error message with arg name and the help command
        * TooManyArguments: send an error message and the help command
        * BadArgument: send an error message and the help command
        * BadUnionArgument: send an error message including the error produced by the last converter
        * ArgumentParsingError: send an error message
        * Other: send an error message and the help command
        """
        if isinstance(e, errors.MissingRequiredArgument):
            embed = self._get_error_embed("Missing required argument", e.param.name)
        elif isinstance(e, errors.TooManyArguments):
            embed = self._get_error_embed("Too many arguments", str(e))
        elif isinstance(e, errors.BadArgument):
            embed = self._get_error_embed("Bad argument", str(e))
        elif isinstance(e, errors.BadUnionArgument):
            embed = self._get_error_embed("Bad argument", f"{e}\n{e.errors[-1]}")
        elif isinstance(e, errors.ArgumentParsingError):
            embed = self._get_error_embed("Argument parsing error", str(e))
            await ctx.send(embed=embed)
            return
        else:
            embed = self._get_error_embed(
                "Input error",
                "Something about your input seems off. Check the arguments and try again.",
            )

        await self.send_error_with_help(ctx, embed)

    async def send_error_with_help(self, ctx: Context, error_embed: Embed) -> None:
        """Send error message, with button to show command help."""
        # Fall back to just sending the error embed if the custom help cog isn't loaded yet.
        # ctx.command shouldn't be None here, but check just to be safe.
        help_embed_creator = getattr(self.bot.help_command, "command_formatting", None)
        if not help_embed_creator or not ctx.command:
            await ctx.send(embed=error_embed)
            return

        self.bot.help_command.context = ctx
        help_embed, _ = await help_embed_creator(ctx.command)
        view = HelpEmbedView(help_embed, ctx.author)
        view.message = await ctx.send(embed=error_embed, view=view)

    @staticmethod
    async def handle_check_failure(ctx: Context, e: errors.CheckFailure) -> None:
        """
        Send an error message in `ctx` for certain types of CheckFailure.

        The following types are handled:

        * BotMissingPermissions
        * BotMissingRole
        * BotMissingAnyRole
        * NoPrivateMessage
        * InWhitelistCheckFailure
        """
        bot_missing_errors = (
            errors.BotMissingPermissions,
            errors.BotMissingRole,
            errors.BotMissingAnyRole,
        )

        if isinstance(e, bot_missing_errors):
            await ctx.send(
                "Sorry, it looks like I don't have the permissions or roles I need to do that."
            )
        elif isinstance(e, errors.NoPrivateMessage):
            await ctx.send(e)

    @staticmethod
    async def handle_unexpected_error(ctx: Context, e: errors.CommandError) -> None:
        """Send a generic error message in `ctx` and log the exception as an error with exc_info."""
        await ctx.send(
            f"Sorry, an unexpected error occurred.\n\n"
            f"```{e.__class__.__name__}: {e}```"
        )

        log.error(
            f"Error executing command invoked by {ctx.message.author}: {ctx.message.content}",
            exc_info=e,
        )


async def setup(bot: Bot) -> None:
    """Load the ErrorHandler cog."""
    await bot.add_cog(ErrorHandler(bot))
