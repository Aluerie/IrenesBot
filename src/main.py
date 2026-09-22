"""
Python file to launch the bot with, so called "main".

You can launch this bot with:
* `make run` (preferred for local testing)
* `uv run src/main.py`
* `python src/main.py`

CLI supported flags can be viewed with `--help` flag.

License
-------
* License: MPL-2.0, see LICENSE for more details.
* Copyright: (C) 2020-present @Aluerie.
"""

# uvloop existing only for Linux makes that reportMissingImports to be invalid for Linux, but valid for Windows
# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import asyncio
import logging
import platform
import sys
from typing import TYPE_CHECKING

import aiohttp
import asyncpg
import click

from config import env
from core import IreBot, get_eventsub_subscriptions
from shared.concepts import logs

if TYPE_CHECKING:
    from shared.types_.database import PoolTypedWithAny

try:
    import uvloop  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]
except ModuleNotFoundError:
    # WINDOWS - uvloop does not support Windows
    RUNTIME = asyncio.run  # pyright: ignore[reportConstantRedefinition]
else:
    # LINUX
    RUNTIME = uvloop.run  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

# generated at https://patorjk.com/software/taag/ using "Standard" font
ASCII_STARTING_UP_ART = r"""
  ___ ____  _____ ____   ___ _____   ____ _____  _    ____ _____ ___ _   _  ____
 |_ _|  _ \| ____| __ ) / _ \_   _| / ___|_   _|/ \  |  _ \_   _|_ _| \ | |/ ___|
  | || |_) |  _| |  _ \| | | || |   \___ \ | | / _ \ | |_) || |  | ||  \| | |  _
  | ||  _ <| |___| |_) | |_| || |    ___) || |/ ___ \|  _ < | |  | || |\  | |_| |
 |___|_| \_\_____|____/ \___/ |_|   |____/ |_/_/   \_\_| \_\|_| |___|_| \_|\____
                    [ IREBOT IS STARTING NOW ]
"""


async def create_pool() -> asyncpg.Pool[asyncpg.Record]:
    """Create AsyncPG Pool."""
    postgres_url = env.POSTGRES_VPS if platform.system() == "Linux" else env.POSTGRES_HOME
    return await asyncpg.create_pool(postgres_url, command_timeout=60, min_size=10, max_size=10, statement_cache_size=0)


async def start_the_bot(
    *,
    scopes_only: bool,
    force_subscribe: bool,
    local_adapter: bool,
    subset_mode: bool,
    test_account: bool,
) -> None:
    """Start the bot."""
    log = logging.getLogger()
    try:
        # Unfortunate `asyncpg` typing crutch. Read `types_.database` for more
        pool: PoolTypedWithAny = await create_pool()  # pyright: ignore[reportAssignmentType]  # ty:ignore[invalid-assignment]
    except Exception:
        msg = "Could not set up PostgreSQL. Exiting."
        click.echo(msg, file=sys.stderr)
        log.exception(msg)
        return

    subscriptions = await get_eventsub_subscriptions(pool, test_account=test_account)

    async with (
        aiohttp.ClientSession() as session,
        pool as pool,
        IreBot(
            session=session,
            pool=pool,
            subscriptions=subscriptions,
            scopes_only=scopes_only,
            force_subscribe=force_subscribe,
            local=local_adapter,
            subset_mode=subset_mode,
            test_account=test_account,
        ) as irebot,
    ):
        await irebot.start()


@click.group(invoke_without_command=True, options_metavar="[options]")
@click.pass_context
@click.option(
    "--scopes-only",
    "-s",
    is_flag=True,
    default=False,  # usual default: False ✅
    help=(
        "Launches the bot without any functionality except for Auth Token management."
        "This also show OATH urls with scopes for a bot account, the bot owner and broadcasters to authorize with."
        "The bot will add their tokens to the database upon authorization thanks to Auth Token management being on."
    ),
)
@click.option(
    "--force-subscribe",
    "-f",
    is_flag=True,
    default=False,  # usual default: False ✅
    help=("Whether to force subscribing to Conduits.You have to do this every time you add new subscriptions"),
)
@click.option(
    "--local-adapter",
    "-l",
    is_flag=True,
    default=False,  # usual default: True ✅
    help="Whether to use adapter with localhost (default) or remote host (currently ngrok-free for testing purposes).",
)
@click.option(
    "--subset-mode",
    "-u",
    is_flag=True,
    default=False,  # usual default: False ✅
    help=(
        "Whether to launch the bot in subset-mode. "
        "In this mode the bot only loads modules that are listed in `modules_subset.py` file."
        "Useful for debugging as it makes launch times much faster."
    ),
)
@click.option(
    "--test-account",
    "-t",
    is_flag=True,
    default=False,  # usual default: False ✅
    help=(
        "Whether to launch the bot using test dummy account (@IrenesTest). "
        "It's useful when we want to test some features without interrupting the main account."
    ),
)
def launch(
    click_ctx: click.Context,
    *,
    scopes_only: bool,
    force_subscribe: bool,
    local_adapter: bool,
    subset_mode: bool,
    test_account: bool,
) -> None:
    """Launch the bot."""
    if click_ctx.invoked_subcommand is None:
        with logs.setup_logging(
            starting_up_art=ASCII_STARTING_UP_ART,
            filename="irebot.log",
        ):
            try:
                RUNTIME(
                    start_the_bot(
                        scopes_only=scopes_only,
                        force_subscribe=force_subscribe,
                        local_adapter=local_adapter,
                        subset_mode=subset_mode,
                        test_account=test_account,
                    )
                )
            except KeyboardInterrupt:
                print("Aborted! The bot was interrupted with `KeyboardInterrupt`!")  # noqa: T201
            except asyncio.CancelledError:
                print("Aborted! The bot was interrupted with `asyncio.CancelledError`!")  # noqa: T201


if __name__ == "__main__":
    launch()
