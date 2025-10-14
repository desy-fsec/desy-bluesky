from __future__ import annotations

from typing import Annotated as A

from ophyd_async.core import (
    SignalRW,
    SignalX,
    SignalR,
    StandardReadableFormat as Format,
)

from ophyd_async.tango.core import TangoPolling

from .fsec_readable_device import FSECReadableDevice, FSECSubscribable


class SIS3820Counter(FSECReadableDevice):
    Counts: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    Offset: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Reset: SignalR[int]

    async def reset(self):
        await self.Reset.get_value()

class SIS3820Subscribable(FSECSubscribable, SIS3820Counter):
    Counts: A[SignalRW[float], Format.HINTED_SIGNAL, TangoPolling(0.5)]
    Offset: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Reset: SignalR[int]
