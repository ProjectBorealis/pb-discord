"""
Loads bot configuration from environment variables and `.env` files.

By default, the values defined in the classes are used, these can be overridden by an env var with the same name.

`.env` and `.env.server` files are used to populate env vars, if present.
"""

import os
from enum import Enum

from pydantic_settings import BaseSettings


class EnvConfig(
    BaseSettings,
    env_file=(".env.server", ".env"),
    env_file_encoding="utf-8",
    env_nested_delimiter="__",
    extra="ignore",
):
    """Our default configuration for models that should load from .env files."""


class _Miscellaneous(EnvConfig):
    debug: bool = True
    file_logs: bool = False


Miscellaneous = _Miscellaneous()


FILE_LOGS = Miscellaneous.file_logs
DEBUG_MODE = Miscellaneous.debug


class _Bot(EnvConfig, env_prefix="bot_"):

    prefix: str = "!"
    token: str
    trace_loggers: str = "*"


Bot = _Bot()


class _Channels(EnvConfig, env_prefix="channels_"):
    announcements: int = 350810790325911572
    github: int = 352463633219059712
    releases: int = 611957255566393359
    meetings: int = 657342682057801762
    introductions: int = 351324332833898509
    tech_support: int = 417775952605741057
    team_lead: int = 654378725697126412
    production: int = 654368648114339910
    strike_group: int = 811649445950914570
    email_config: int = 601134391850434570
    ravenholm_feedback: int = 379742050406498305
    playtest_feedback: int = 655180925688086528
    bot_test: int = 420850706136694786
    public_playtesters: int = 502887068783869952


Channels = _Channels()


class _Roles(EnvConfig, env_prefix="roles_"):
    on_leave: int = 800250529259061278
    support: int = 803741037557186632
    inviter: int = 966924781767237652
    public_manager: int = 461192768811827200
    public_moderator: int = 353372472546033664
    public_team: int = 353372472546033664
    public_former_team: int = 802949984637943849
    public_playtester: int = 554090450210783254
    public_playtest_admin: int = 625415837641080853


Roles = _Roles()

roles_to_teams = {
    "Director": "Directors",
    "Production": "Production",
    "Team Lead": "Team Leads",
    "Art Direction": "Art Directors",
    "Public Relations": "Public Relations",
    "Programmer": "Programming",
    "3D Artist": "3D Art",
    "Animator": "Animation",
    "Texture Artist": "Texture Art",
    "Effects Artist": "VFX",
    "Concept Artist": "Concept Art",
    "Composer": "Music Production",
    "Design": "Level Design",
    "Game Design": "Game Design",
    "Sound Designer": "Sound Design",
    "IT Department": "IT",
    "DevOps": "DevOps",
    "Voice Actor": "Voice Acting",
    "Writer": "Writing",
}


class _Guild(EnvConfig, env_prefix="guild_"):

    id: int
    public: int = 350643892447870976


Guild = _Guild()


class Event(Enum):
    """
    Discord.py event names.

    This does not include every event (for example, raw events aren't here).
    """

    guild_channel_create = "guild_channel_create"
    guild_channel_delete = "guild_channel_delete"
    guild_channel_update = "guild_channel_update"
    guild_role_create = "guild_role_create"
    guild_role_delete = "guild_role_delete"
    guild_role_update = "guild_role_update"
    guild_update = "guild_update"

    member_join = "member_join"
    member_remove = "member_remove"
    member_ban = "member_ban"
    member_unban = "member_unban"
    member_update = "member_update"

    message_delete = "message_delete"
    message_edit = "message_edit"

    voice_state_update = "voice_state_update"


class _RedirectOutput(EnvConfig, env_prefix="redirect_output_"):

    delete_delay: int = 15
    delete_invocation: bool = True


RedirectOutput = _RedirectOutput()


class _Emojis(EnvConfig, env_prefix="emojis_"):
    trashcan: str = "\U0001f5d1"

    bullet: str = "\u2022"
    check_mark: str = "\u2705"
    cross_mark: str = "\u274C"
    new: str = "\U0001F195"
    pencil: str = "\u270F"

    ok_hand: str = ":ok_hand:"


Emojis = _Emojis()


class Icons:
    """URLs to commonly used icons."""

    crown_blurple = "https://cdn.discordapp.com/emojis/469964153289965568.png"
    crown_green = "https://cdn.discordapp.com/emojis/469964154719961088.png"
    crown_red = "https://cdn.discordapp.com/emojis/469964154879344640.png"

    defcon_denied = "https://cdn.discordapp.com/emojis/472475292078964738.png"
    defcon_shutdown = "https://cdn.discordapp.com/emojis/470326273952972810.png"
    defcon_unshutdown = "https://cdn.discordapp.com/emojis/470326274213150730.png"
    defcon_update = "https://cdn.discordapp.com/emojis/472472638342561793.png"

    filtering = "https://cdn.discordapp.com/emojis/472472638594482195.png"

    green_checkmark = "https://raw.githubusercontent.com/python-discord/branding/main/icons/checkmark/green-checkmark-dist.png"
    green_questionmark = "https://raw.githubusercontent.com/python-discord/branding/main/icons/checkmark/green-question-mark-dist.png"
    guild_update = "https://cdn.discordapp.com/emojis/469954765141442561.png"

    hash_blurple = "https://cdn.discordapp.com/emojis/469950142942806017.png"
    hash_green = "https://cdn.discordapp.com/emojis/469950144918585344.png"
    hash_red = "https://cdn.discordapp.com/emojis/469950145413251072.png"

    message_bulk_delete = "https://cdn.discordapp.com/emojis/469952898994929668.png"
    message_delete = "https://cdn.discordapp.com/emojis/472472641320648704.png"
    message_edit = "https://cdn.discordapp.com/emojis/472472638976163870.png"

    pencil = "https://cdn.discordapp.com/emojis/470326272401211415.png"

    questionmark = "https://cdn.discordapp.com/emojis/512367613339369475.png"

    remind_blurple = "https://cdn.discordapp.com/emojis/477907609215827968.png"
    remind_green = "https://cdn.discordapp.com/emojis/477907607785570310.png"
    remind_red = "https://cdn.discordapp.com/emojis/477907608057937930.png"

    sign_in = "https://cdn.discordapp.com/emojis/469952898181234698.png"
    sign_out = "https://cdn.discordapp.com/emojis/469952898089091082.png"

    superstarify = "https://cdn.discordapp.com/emojis/636288153044516874.png"
    unsuperstarify = "https://cdn.discordapp.com/emojis/636288201258172446.png"

    token_removed = (
        "https://cdn.discordapp.com/emojis/470326273298792469.png"  # noqa: S105
    )

    user_ban = "https://cdn.discordapp.com/emojis/469952898026045441.png"
    user_timeout = "https://cdn.discordapp.com/emojis/472472640100106250.png"
    user_unban = "https://cdn.discordapp.com/emojis/469952898692808704.png"
    user_untimeout = "https://cdn.discordapp.com/emojis/472472639206719508.png"
    user_update = "https://cdn.discordapp.com/emojis/469952898684551168.png"
    user_verified = "https://cdn.discordapp.com/emojis/470326274519334936.png"
    user_warn = "https://cdn.discordapp.com/emojis/470326274238447633.png"

    voice_state_blue = "https://cdn.discordapp.com/emojis/656899769662439456.png"
    voice_state_green = "https://cdn.discordapp.com/emojis/656899770094452754.png"
    voice_state_red = "https://cdn.discordapp.com/emojis/656899769905709076.png"


class Colours:
    """Colour codes, mostly used to set discord.Embed colours."""

    blue: int = 0x3775A8
    bright_green: int = 0x01D277
    orange: int = 0xE67E22
    pink: int = 0xCF84E0
    purple: int = 0xB734EB
    soft_green: int = 0x68C290
    soft_orange: int = 0xF9CB54
    soft_red: int = 0xCD6D6D
    white: int = 0xFFFFFE
    yellow: int = 0xFFD241


class _BaseURLs(EnvConfig, env_prefix="urls_"):

    # Discord API
    discord_api: str = "https://discordapp.com/api/v7/"

    # GitHub
    github_api: str = "https://api.github.com"

    # Site
    site_api: str = "https://api.projectborealis.com"


BaseURLs = _BaseURLs()


class _URLs(_BaseURLs):
    pass


URLs = _URLs()


class _Keys(EnvConfig, env_prefix="api_keys_"):

    github: str
    site_api: str
    game_project_id: str
    appplications_project_id: str


Keys = _Keys()

BOT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BOT_DIR, os.pardir))
GIT_SHA = os.environ.get("GIT_SHA", "development")
