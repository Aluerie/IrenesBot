from __future__ import annotations

import logging
import pprint
from typing import Any

import aiohttp
import orjson
import yarl

_log: logging.Logger = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)


class SevenTVWebSocket:
    DEFAULT_GATEWAY = yarl.URL("wss://events.7tv.io/v3/")  # ending "/" is important

    DISPATCH = 0
    HELLO = 1
    HEARTBEAT = 2
    RECONNECT = 4
    ACK = 5
    ERROR = 6
    END_OF_STREAM = 7
    IDENTIFY = 33
    RESUME = 34
    SUBSCRIBE = 35
    UNSUBSCRIBE = 36
    SIGNAL = 37

    def __init__(self, socket: aiohttp.ClientWebSocketResponse) -> None:
        self.socket = socket

    @classmethod
    async def from_client(
        cls,
        *,
        gateway: yarl.URL | None = None,
    ) -> None:
        gateway = gateway or cls.DEFAULT_GATEWAY

        async with aiohttp.ClientSession() as session:
            socket = await session.ws_connect(gateway)
            session.detach()

        ws = cls(socket)

        # poll event for OP Hello
        while True:
            await ws.poll_event()

    async def received_message(self, msg: Any, /):

        msg = orjson.loads(msg)

        _log.debug("7TV WebSocket Event: %s", msg)

        pprint.pprint(msg)

        op = msg.get("op")  # message operation code
        data = msg.get("d")  # 	generic data payload
        seq = msg.get("s")  # sequence ?
        t = msg.get("t")  # timestamp of the message's formation in unix millis

        if op == self.HELLO:
            interval = data["heartbeat_interval"] / 1000.0
            # self._keep_alive = KeepAliveHandler(ws=self, interval=interval, shard_id=self.shard_id)
            # # send a heartbeat immediately
            # await self.send_as_json(self._keep_alive.get_payload())
            # self._keep_alive.start()
            return

    async def poll_event(self) -> None:
        msg = await self.socket.receive()

        await self.received_message(msg.data)


if __name__ == "__main__":
    import asyncio
    asyncio.run(SevenTVWebSocket.from_client())
