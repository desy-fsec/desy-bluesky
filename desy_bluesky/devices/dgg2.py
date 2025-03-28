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
from ophyd_async.tango.core import TangoPolling
from tango import DevState

from .fsec_readable_device import FSECReadableDevice

# TODO: SAWFT only works for SampleTime < 3.0 seconds. Solve this.


class DGG2Timer(FSECReadableDevice, Triggerable, Stoppable):
    SampleTime: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    Stop: SignalX
    Start: SignalX
    State: A[SignalR[DevState], Format.UNCACHED_SIGNAL, TangoPolling(0.01)]
    StartAndWaitForTimer: SignalX

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        sample_time = await self.SampleTime.get_value()
        timeout = sample_time + DEFAULT_TIMEOUT
        await self.StartAndWaitForTimer.trigger(wait=True, timeout=timeout)

    def stop(self, success: bool = True) -> AsyncStatus:
        return self.Stop.trigger(wait=False)
