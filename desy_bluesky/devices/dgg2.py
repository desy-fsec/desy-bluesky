from __future__ import annotations

from typing import Annotated as A

from bluesky.protocols import Triggerable, Stoppable

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    SignalX,
    SignalRW,
    SignalR,
    StandardReadableFormat as Format,
)
from ophyd_async.tango.core import TangoPolling, DevStateEnum

from .fsec_readable_device import FSECReadableDevice

# TODO: SAWFT only works for SampleTime < 3.0 seconds. Solve this.


class DGG2Timer(FSECReadableDevice, Triggerable, Stoppable):
    SampleTime: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    Stop: SignalR[int]
    State: A[SignalR[DevStateEnum], TangoPolling(0.01)]
    StartAndWaitForTimer: SignalR[int]

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        sample_time = await self.SampleTime.get_value()
        await self.StartAndWaitForTimer.get_value()

    @AsyncStatus.wrap
    async def stop(self, success: bool = True):
        await self.Stop.get_value()
