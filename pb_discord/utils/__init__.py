"""Useful utilities and tools for Discord bot development."""

from pb_discord.utils import _monkey_patches


def apply_monkey_patches() -> None:
    """
    Applies all common monkey patches for our bots.

    Patches :obj:`discord.ext.commands.Command` and :obj:`discord.ext.commands.Group` to support root aliases.
        A ``root_aliases`` keyword argument is added to these two objects, which is a sequence of alias names
        that will act as top-level groups rather than being aliases of the command's group.

        It's stored as an attribute also named ``root_aliases``

    Patches discord's internal ``send_typing`` method so that it ignores 403 errors from Discord.
        When under heavy load Discord has added a CloudFlare worker to this route, which causes 403 errors to be thrown.
    """
    _monkey_patches._apply_monkey_patches()  # noqa: SLF001
