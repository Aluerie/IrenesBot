# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Notifications to systemd for a `Type=notify` unit with a watchdog."""

from __future__ import annotations

import asyncio
import os
import socket
import sys

from loguru import logger

__all__ = ("sd_notify", "watchdog_loop")


def sd_notify(state: str) -> None:
    """Send a state message such as ``READY=1`` or ``WATCHDOG=1`` to systemd.

    Does nothing when the process is not started by a systemd unit with ``Type=notify`` (e.g. local development).
    """
    if sys.platform == "win32":
        return
    address = os.environ.get("NOTIFY_SOCKET", "")
    if not address:
        return
    if address.startswith("@"):  # abstract namespace socket
        address = "\0" + address[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:  # ty: ignore[unresolved-attribute, unused-ignore-comment]
            sock.connect(address)
            sock.sendall(state.encode())
    except OSError:
        logger.exception("Failed to notify systemd with {}", state)


async def watchdog_loop() -> None:
    """Keep pinging the systemd watchdog so systemd restarts the process if its event loop gets stuck.

    Pings at half of the unit's ``WatchdogSec=``; returns immediately when the unit has no watchdog configured.
    """
    watchdog_usec = os.environ.get("WATCHDOG_USEC", "")
    if not watchdog_usec:
        return
    interval = int(watchdog_usec) / 1_000_000 / 2
    while True:
        sd_notify("WATCHDOG=1")
        await asyncio.sleep(interval)
