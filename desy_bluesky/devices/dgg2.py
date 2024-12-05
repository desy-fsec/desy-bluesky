from __future__ import annotations

from typing import Annotated as A

from bluesky.protocols import Triggerable, Stoppable, SyncOrAsync

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    SignalX,
    SignalRW,
    SignalR,
    wait_for_value,
    StandardReadableFormat as Format,
)
from ophyd_async.tango.core import (
    TangoPolling
)
from tango import DevState

from .fsec_readable_device import FSECReadableDevice


class DGG2Timer(FSECReadableDevice, Triggerable, Stoppable):
    SampleTime: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    Stop: SignalX
    Start: SignalX
    State: A[SignalR[DevState], TangoPolling(0.01)]

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        sample_time = await self.SampleTime.get_value()
        timeout = sample_time + DEFAULT_TIMEOUT
        await self.Start.trigger(wait=False, timeout=timeout)
        await AsyncStatus(wait_for_value(self.State, DevState.ON, timeout=timeout))

    def stop(self) -> SyncOrAsync:
        return self.Stop.trigger(wait=False)