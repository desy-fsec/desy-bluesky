from __future__ import annotations
from enum import Enum

import asyncio
from typing import TypeVar

from bluesky.protocols import Reading

from ophyd_async.core import (
    AsyncStatus,
)
from ophyd_async.core import (
    SignalR,
)
from ophyd_async.tango import (
    TangoReadable,
    tango_polling
)
from tango import DevState

FSECDeviceConfig = TypeVar("FSECDeviceConfig")


@tango_polling((0.1, 0.1, 0.1))
class FSECReadableDevice(TangoReadable):
    State: SignalR[Enum]

    @AsyncStatus.wrap
    async def wait_for_idle(self):
        event = asyncio.Event()

        def _wait(value: dict[str, Reading]):
            if value[self.State.name]["value"] == DevState.ON:
                event.set()

        self.State.subscribe(_wait)
        await event.wait()
        self.State.clear_sub(_wait)
