from __future__ import annotations

import asyncio
import contextlib
import datetime
import enum
import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict, override

import discord
import steam
import twitchio
from twitchio import eventsub
from twitchio.ext import commands
from twitchio.web import StarletteAdapter

from config import env
from modules import PUBLIC_D9MMRBOT, get_modules
from shared import errors, fmt, globs
from shared.other import MISSING
from shared.seven_tv_gql import GraphQL7TVClient, exceptions as stv_errors
from utils import const
from utils.dota2 import IreDota2Client

from .bases import IreContext
from .error_manager import ErrorManager
from .subscriptions import get_all_oauth_urls, get_user_subscriptions

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from aiohttp import ClientSession
    from twitchio.user import PartialUser

    from shared.types_.database import PoolTypedWithAny

    class LoadTokensQueryRow(TypedDict):
        user_id: str
        token: str
        refresh: str


__all__ = (
    "AdapterEnum",
    "IreBot",
    "Streamer",
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@dataclass
class Streamer:
    """Streamer dataclass.

    Object of such class are stored in `IreBot.streamers` index.
    """

    id: str
    online: bool = False
    started_dt: datetime.datetime | None = None


class AdapterEnum(enum.Enum):
    """Adapter Enum."""

    local = enum.auto()
    remote = enum.auto()


class IreBot(commands.AutoBot):
    """Main class for IreBot.

    Essentially subclass over TwitchIO's Client.
    Used to interact with the Twitch API, EventSub and more.
    Includes TwitchIO's `ext.commands` extension to organize components/commands framework.

    Note on the name
    ----------------
    The name `IrenesBot` is used mainly for display purposes here:
        * the bot's twitch account user name (just so it's clear that it's Irene's bot);
        * the bot's Steam account's display name;

    Name `IreBot` is pretty much used elsewhere:
        * the GitHub repository name and `README.md` file.
        * class name;
        * folder name;
        * systemd service name;
        * discord notifications webhook names;
        * category name in my own ToDo list;
        * etc.

    Maybe I will change this in future to be less confusing, but I think current situation is fine.

    """

    if TYPE_CHECKING:
        # it's "str | None" in twitchio, but we do supply it directly
        owner_id: str  # pyright: ignore[reportIncompatibleMethodOverride]
        user: twitchio.User  # pyright: ignore[reportIncompatibleMethodOverride]

    def __init__(
        self,
        *,
        session: ClientSession,
        pool: PoolTypedWithAny,
        subscriptions: list[eventsub.SubscriptionPayload],
        scopes_only: bool,
        force_subscribe: bool,
        adapter_enum: AdapterEnum,
        subset_mode: bool,
        test_account: bool,
    ) -> None:
        """Initiate IreBot."""
        if adapter_enum is AdapterEnum.local:
            self.domain = "http://localhost:4343"
            adapter: StarletteAdapter[Any] | None = None
        else:
            # AdapterEnum.remote
            self.domain = "https://parrot-thankful-trivially.ngrok-free.app"
            adapter = StarletteAdapter(
                host="0.0.0.0",  # noqa: S104
                domain=self.domain,
                eventsub_secret=env.EVENTSUB,
            )

        if test_account:
            # test account
            self.test = True
            client_id = env.TEST_TWITCH_CLIENT_ID
            client_secret = env.TEST_TWITCH_CLIENT_SECRET
            bot_id = const.UserID.Test
            self.prefixes = ("%",)
            self.error_ping = "<@&1337106675433340990>"
        else:
            # production account
            self.test = False
            client_id = env.TWITCH_CLIENT_ID
            client_secret = env.TWITCH_CLIENT_SECRET
            bot_id = const.UserID.Bot
            self.prefixes = ("!", "?", "$")
            self.error_ping = "<@&1116171071528374394>"

        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            owner_id=const.UserID.Irene,
            prefix=self.prefixes,
            adapter=adapter,  # pyright: ignore[reportArgumentType], it's hinted as `NotRequired` while I need to use `None`.
            subscriptions=subscriptions,
            force_subscribe=force_subscribe,  # Set to `True` if we need urgent manual refreshing eventsub subs.
        )
        self.session: ClientSession = session
        self.pool: PoolTypedWithAny = pool
        self.scopes_only: bool = scopes_only

        self.subset_mode: bool = subset_mode
        """A boolean flag indicating whether we launch the whole bot (on VPS machine)
        or just a subset of features (on my home Windows machine). We also use
        different credentials for certain things depending on home/vps choice.
        """

        self.modules_to_load: tuple[str, ...] = get_modules(is_subset_mode=self.subset_mode)
        self.error_manager = ErrorManager(self)

        self.streamers: dict[str, Streamer] = {}
        self.streamers_index_ready: asyncio.Event = asyncio.Event()
        self.friends_index_ready: asyncio.Event = asyncio.Event()

        self.stv: GraphQL7TVClient = GraphQL7TVClient(
            bearer_token=env.SEVEN_TV_BEARER,
            bot_7tv_user_id=const.SevenTV.BOT_ID,
            pool=pool,
        )

        # initialized later
        self.dota2: IreDota2Client = MISSING
        self.launch_time: datetime.datetime
        self.logs_via_webhook_handler: logging.Handler

    @override
    async def setup_hook(self) -> None:
        """
        Setup Hook. Method called after `.login` has been called but before the bot is ready.

        TwitchIO OAuth Tokens Magic
        ---------------------------
        In order to get the required oath tokens into the database when running the bot
        for the first time (or after adding extra scopes):
            1. Run the bot with `uv run main.py -s`;
            2. Click generated links using proper accounts:
                * bot - bot account (@IrenesBot)
                * personal - my own account
                * public - public accounts
            3. The bot will update the tokens in the database automatically;
            4. Run the bot normally (with `uv run main.py`).

        """
        if self.scopes_only:
            msg = (
                "Scopes Only Mode: print oauth urls and start the bot in adapter-only mode (no modules enabled).\n"
                f"{get_all_oauth_urls(self.domain)}"
            )
            log.warning(msg)
            return

        for module in self.modules_to_load:
            log.debug("Loading module: %s", module)
            try:
                await self.load_module(module)
            except commands.ModuleLoadFailure as error:
                embed = discord.Embed(title="Module Load Error", colour=0x12A28A)
                await self.error_manager.register(error, embed=embed)

    @override
    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        """Triggered when a (new) user authorizes the bot scopes using oauth link.

        Conduits require subscribing to new users or updated oauth scopes urls.
        Otherwise we need to use `force_subscribe` bot kwarg.

        Source
        ------
        Example `basic_conduits.py` by TwitchIO:
        * https://github.com/PythonistaGuild/TwitchIO/blob/main/examples/basic_conduits/main.py
        """
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            # We usually don't want subscribe to events on the bots channel...
            return

        subs: list[eventsub.SubscriptionPayload] = get_user_subscriptions(payload.user_id, self.bot_id)
        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            log.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

    @override
    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        """Add token to the twitchio client and into the bot's database.

        Source
        ------
        Quickstart guide by TwitchIO:
        * https://twitchio.dev/en/latest/getting-started/quickstart.html
        """
        # Make sure to call super() as it will add the tokens internally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        # Store our tokens in a simple SQLite Database when they are authorized...
        query = """
            INSERT INTO ttv_tokens
            (user_id, token, refresh)
            VALUES ($1, $2, $3)
            ON CONFLICT(user_id)
            DO UPDATE SET
                token = excluded.token,
                refresh = excluded.refresh
            RETURNING display_name;
        """
        display_name = await self.pool.fetchval(query, resp.user_id, token, refresh)
        if resp.user_id is not None and display_name is None:
            # Probably new user joined - let's give them a name
            user = await self.create_partialuser(resp.user_id).user()
            query = "UPDATE ttv_tokens SET display_name = $1 WHERE user_id = $2;"
            await self.pool.execute(query, user.display_name, user.id)
            log.info("Added a new streamer %s (@%s) to the database", user.id, user.display_name)

            # let's moderate the bot immediately
            await user.add_moderator(self.user.id)

            # TODO: maybe make a notification into irene's discord

        log.info("Added token to the database for user: %s", resp.user_id)
        return resp

    @override
    async def load_tokens(self, _: str | None = None) -> None:  # _ is `path`
        # We don't need to call this manually, it is called in .login() from .start() internally...
        query = "SELECT * FROM ttv_tokens"
        rows: list[LoadTokensQueryRow] = await self.pool.fetch(query)
        for row in rows:
            await self.add_token(row["token"], row["refresh"])

    @override
    async def start(
        self,
        token: str | None = None,
        *,
        with_adapter: bool = True,
        load_tokens: bool = True,
        save_tokens: bool = True,
    ) -> None:
        if PUBLIC_D9MMRBOT in self.modules_to_load:
            self.dota2 = IreDota2Client(self)
            try:
                await asyncio.gather(
                    super().start(token, with_adapter=with_adapter, load_tokens=load_tokens, save_tokens=save_tokens),
                    self.dota2.login(),
                )
            # A potential workaround for steam login issues
            # https://github.com/Gobot1234/steam.py/issues/446
            # My service / docker files are set to restart the bot on exits
            # So it will keep restarting the bot until Steam Issues are resolved.
            except steam.errors.NoCMsFound:
                log.warning("🔴 Encountered `steam.errors.NoCMsFound` - restarting. 🔴")
                sys.exit(1)
            except steam.errors.LoginError:
                log.warning("🔴 Encountered `steam.errors.LoginError` - restarting. 🔴")
                sys.exit(1)
        else:
            await super().start()

    @override
    async def close(self, **options: Any) -> None:
        if self.dota2:
            await self.dota2.close()
        await super().close(**options)

    @override
    def get_context(
        self,
        payload: twitchio.ChatMessage | twitchio.ChannelPointsRedemptionAdd | twitchio.ChannelPointsRedemptionUpdate,
        *,
        cls: Any = IreContext,
    ) -> IreContext:
        # they have channel points commands but I'm not using it (yet)
        return super().get_context(payload, cls=cls)

    # @override  # interesting that it's not an override
    async def event_ready(self) -> None:
        """Event that is dispatched when the `Client` is ready and has completed login."""
        log.info("%s is ready as @%s (id=%s)", self.__class__.__name__, self.user.display_name, self.bot_id)

        if not hasattr(self, "launch_time"):
            # who knows maybe it triggers many times like `discord.py`
            self.launch_time = datetime.datetime.now(datetime.UTC)
        if self.dota2:
            await self.dota2.wait_until_ready()

    SOMETHING_WENT_WRONG_MESSAGE = (
        f"Something went wrong {const.Global.FeelsDankMan} "
        f"but I've notified Irene about the error {const.Global.FeelsDankMan}"
    )

    async def handle_common_errors(
        self, error: BaseException | None, respond: Callable[..., Coroutine[Any, Any, twitchio.SentMessage]]
    ) -> bool:
        """Handle known common error types.

        Common in a sense that they can happen in commands, events, tasks, etc.
        So all error handlers can use this function as a helper.
        """
        match error:
            # MY CUSTOM ERRORS
            case errors.BotError():
                if error.silent:
                    return True
                if error.respond:
                    await respond(error.msg)
                if error.dev_message and not error.register:
                    await self.ping_developers(content=error.formatted_message_for_devs())
                if error.register:
                    return False
            # 7TV
            case stv_errors.UnauthorizedError():
                await respond(f"{error} {globs.Global7TV.FeelsDankMan}")
                await self.ping_developers(
                    content=f"The bot's 7TV Bearer Token is expired.\n{fmt.codeblock(repr(error.debug_data))}"
                )
            case stv_errors.InvokeQueryError():
                await respond(f"{error} {globs.Global7TV.FeelsDankMan}")
                await self.ping_developers(content=str(error))
            case stv_errors.SomethingWentWrongError():
                return False
            case stv_errors.SevenTVError():
                await respond(f"{error} {globs.Global7TV.FeelsDankMan}")

            # TWITCHIO ERRORS
            # I don't think we should be sending those in chat?
            # case twitchio.HTTPException():
            #     await respond(
            #         f"{error.__class__.__name__} - "
            #         f"{error.extra.get('error', 'Error')} "
            #         f"{error.extra.get('status', 'XXX')}: "
            #         f"{error.extra.get('message') or 'Unknown'} {const.STV.dankFix} "
            #         f"(Irene will surely fix it)"
            #     )
            case twitchio.MessageRejectedError():
                # This one is a annoying because it stops code execution
                # let's at least send the response back
                await respond(error.content + chr(32) + chr(917504))

            case _:
                return False
        return True

    @override
    async def event_command_error(self, payload: commands.CommandErrorPayload) -> None:
        """Called when error happens during command invoking."""
        command = payload.context.command
        ctx: IreContext = payload.context  # pyright: ignore[reportAssignmentType] we do not use Channel Point commands.
        error = payload.exception

        if command and command.has_error and ctx.error_dispatched:
            return

        # we aren't interested in the chain traceback from invoking:
        error = error.original if isinstance(error, commands.CommandInvokeError) and error.original else error

        # 1. Handle common error
        if await self.handle_common_errors(error, ctx.send):
            return

        match error:
            # 2. Handle command specific errors
            case commands.CommandNotFound():
                if self.test:
                    # if not `self.test` then we don't need to spam the logs with commands from other bots
                    # for streams that use several bots with the same prefix.
                    log.info("CommandNotFound: %s", error)
            case commands.CommandOnCooldown():
                command_name = f"{ctx.prefix}{command.name}" if command else "this command"
                await ctx.send(
                    f"Command {command_name} is on cooldown! Try again in {error.remaining:.0f} sec {const.STV.Timeloth}"
                )
            case commands.GuardFailure():
                if await self.handle_common_errors(error.__cause__, ctx.send):
                    # Guards raise `GuardFailure` errors while we're always interested in `__cause__`.
                    return
                # To make custom responses for default `twitchio` guards - need to cook a bit.
                # (or make our own guards with the same predicates, not like it's anything complex)
                guard_response = {
                    "is_moderator": "Only moderators are allowed to use this command",
                    "is_owner": "Only Irene_Adler__ is allowed to use this command",
                    "is_broadcaster": "Only broadcaster is allowed to use this command",
                }.get(
                    # an example of `.__qualname__`: "is_moderator.<locals>.predicate"
                    (
                        guard_name := "Unknown Guard"
                        if error.guard is None
                        else error.guard.__qualname__.removesuffix(".<locals>.predicate")
                    ),
                    f'For some reason ("{guard_name}") you are not allowed to use this command',
                )
                await ctx.send(f"{guard_response} {const.FFZ.peepoPolice}")
            case commands.MissingRequiredArgument():
                await ctx.send(f'You need to provide "{error.param.name}" argument for this command {const.FFZ.peepoPolice}')
            case commands.BadArgument():
                if await self.handle_common_errors(error.__cause__, ctx.send):
                    # Converters raise `BadArgument` Failed to convert "this" to <class 'typing._ProtocolMeta'>, which is not
                    # exactly telling much. We are more interested in the original `__cause__`.
                    return
                log.error("%s: %s | error.name=%s | error.value=%s", type(error), error, error.name, error.value)
                await ctx.send(
                    content=(
                        f"Couldn't convert value `{error.value}` for argument `{error.name}` "
                        f"to required type/format {const.STV.dankFix}"
                    )
                )
            case _:
                # 3. All other errors;
                # SomethingWentWrongError also goes here (unlike how it was long ago).
                await ctx.send(self.SOMETHING_WENT_WRONG_MESSAGE)
                # await ctx.send(f"{error.__class__.__name__}: {replace_secrets(str(error))}")
                command_name = getattr(ctx.command, "name", "unknown")
                embed = (
                    discord.Embed(
                        colour=ctx.chatter.colour.code if ctx.chatter.colour else 0x890620,
                        title=f"Command Error: `!{command_name}`",
                    )
                    .set_author(
                        name=f"Chatter {ctx.chatter.display_name}",
                        icon_url=(await ctx.chatter.user()).profile_image,
                    )
                    .set_footer(
                        text=f"Channel: {ctx.broadcaster.display_name}",
                        icon_url=(await ctx.broadcaster.user()).profile_image,
                    )
                    .add_field(name="Command Args", value=fmt.pformat_dict(ctx.kwargs), inline=False)
                )
                if isinstance(error, errors.BotError) and error.debug_data:
                    embed.add_field(name="Extra Debug Data", value=error.formatted_message_for_devs(), inline=False)
                await self.error_manager.register(error, embed=embed)

    @override
    async def event_error(self, payload: twitchio.EventErrorPayload) -> None:
        """Event Error."""
        error = payload.error
        original = payload.original

        if isinstance(original, twitchio.ChannelPointsRedemptionAdd):
            # let's be nice and refund channel points for failed redeems
            with contextlib.suppress(twitchio.HTTPException):
                await original.refund(token_for=original.broadcaster.id)

        if hasattr(original, "respond") and await self.handle_common_errors(error, original.respond):
            # 1. Handle common error
            return

        # 2. All other errors;
        # SomethingWentWrongError also goes here (unlike long ago).

        embed = discord.Embed(
            title=f"Event Error: `{payload.listener.__qualname__}`",
        ).add_field(
            name="Exception",
            value=f"`{payload.error.__class__.__name__}`",
        )
        if broadcaster := getattr(original, "broadcaster", None):
            embed.set_footer(
                text=f"Channel: {broadcaster.display_name}",
                icon_url=(await broadcaster.user()).profile_image,
            )
        if chatter := getattr(original, "user", None):
            embed.set_author(
                name=f"Chatter {chatter.display_name}",
                icon_url=(await chatter.user()).profile_image,
            )
        if isinstance(error, errors.BotError) and error.debug_data:
            embed.add_field(name="Extra Debug Data", value=error.formatted_message_for_devs(), inline=False)
        await self.error_manager.register(error, embed=embed)

    # SHORTCUTS AND UTILITIES

    def webhook_from_url(self, url: str) -> discord.Webhook:
        """A shortcut function with filled in discord.Webhook.from_url args."""
        return discord.Webhook.from_url(url=url, session=self.session)

    @discord.utils.cached_property
    def logger_webhook(self) -> discord.Webhook:
        """A webhook in hideout's #logger channel."""
        return self.webhook_from_url(env.WEBHOOK_LOGGER)

    @discord.utils.cached_property
    def error_webhook(self) -> discord.Webhook:
        """A webhook in hideout server to send errors/notifications to the developer(-s)."""
        return self.webhook_from_url(env.WEBHOOK_ERROR)

    async def ping_developers(self, **send_kwargs: Any) -> None:
        """Ping developers.

        Parameters
        ----------
        send_kwargs
            Kwargs for `webhook.send` method.
        """
        content = f"{self.error_ping}\n{send_kwargs.get('content') or ''}"
        await self.error_webhook.send(content, **send_kwargs)

    @discord.utils.cached_property
    def heartbeat_webhook(self) -> discord.Webhook:
        """A webhook in hideout server to send small heartbeat reports."""
        return self.webhook_from_url(env.WEBHOOK_HEARTBEAT)

    def is_online(self, user_id: str) -> bool:
        """Whether the user is online.

        This relies on `self.streamers` index.
        For proper request - we need to use twitchio's `.fetch_streams` method.
        """
        return self.get_streamer(user_id).online

    def get_streamer(self, user_id: str) -> Streamer:
        """Get streamer from the bot's streamer index."""
        try:
            return self.streamers[user_id]
        except KeyError:
            msg = f"Somehow {user_id} is not in the bots' streamer index."
            raise errors.SomethingWentWrongError(msg) from None

    def irene(self) -> PartialUser:
        """Create partial user for @Irene_Adler__ (the bot's owner)."""
        return self.create_partialuser(self.owner_id)
