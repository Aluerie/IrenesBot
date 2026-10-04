"""The bot's launcher, so called "main.py" file.

You can launch this bot with:
* `make run` - preferred for local testing;
* `uv run --no-dev src/main.py` preferred for production.

CLI supported flags can be viewed with `--help` flag (or looked up in this file).

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import sys

import aiohttp
import click

from config import env
from core import AdapterEnum, IreBot, get_eventsub_subscriptions
from shared.concepts import db, logs
from shared.other import run

# generated at https://patorjk.com/software/taag/ using "Standard" font
ASCII_STARTING_UP_ART = r"""
  ___ ____  _____ ____   ___ _____   ____ _____  _    ____ _____ ___ _   _  ____
 |_ _|  _ \| ____| __ ) / _ \_   _| / ___|_   _|/ \  |  _ \_   _|_ _| \ | |/ ___|
  | || |_) |  _| |  _ \| | | || |   \___ \ | | / _ \ | |_) || |  | ||  \| | |  _
  | ||  _ <| |___| |_) | |_| || |    ___) || |/ ___ \|  _ < | |  | || |\  | |_| |
 |___|_| \_\_____|____/ \___/ |_|   |____/ |_/_/   \_\_| \_\|_| |___|_| \_|\____
                    [ IREBOT IS STARTING NOW ]
"""


async def start_the_bot(
    *,
    scopes_only: bool,
    force_subscribe: bool,
    adapter_enum: AdapterEnum,
    subset_mode: bool,
    test_account: bool,
) -> None:
    """Start the bot."""
    log = logging.getLogger()
    postgres_url = env.POSTGRES_VPS if platform.system() == "Linux" else env.POSTGRES_HOME
    try:
        pool = await db.create_pool(postgres_url)
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
            adapter_enum=adapter_enum,
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
    "--adapter",
    "-a",
    type=click.Choice(AdapterEnum, case_sensitive=False),
    default=AdapterEnum.remote,  # usual default: AdapterType.local ✅
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
    adapter: AdapterEnum,
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
                run(
                    start_the_bot(
                        scopes_only=scopes_only,
                        force_subscribe=force_subscribe,
                        adapter_enum=adapter,
                        subset_mode=subset_mode,
                        test_account=test_account,
                    ),
                )
            except KeyboardInterrupt:
                print("Aborted! The bot was interrupted with `KeyboardInterrupt`!")  # ruff: ignore[print]
            except asyncio.CancelledError:
                print("Aborted! The bot was interrupted with `asyncio.CancelledError`!")  # ruff: ignore[print]


if __name__ == "__main__":
    launch()
