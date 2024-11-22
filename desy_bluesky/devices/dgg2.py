from __future__ import annotations

from typing import Annotated as A

from bluesky.protocols import Triggerable

from ophyd_async.tango.core import (
    TangoPolling
)
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    SignalX,
    SignalRW,
    wait_for_value,
    StandardReadableFormat as Format,
)
from tango import DevState

from .fsec_readable_device import FSECReadableDevice


class DGG2Timer(FSECReadableDevice, Triggerable):
    SampleTime: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    Start: SignalX

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        sample_time = await self.SampleTime.get_value()
        timeout = sample_time + DEFAULT_TIMEOUT
        await self.Start.trigger(wait=False, timeout=timeout)
        await AsyncStatus(wait_for_value(self.State, DevState.ON, timeout=timeout))
