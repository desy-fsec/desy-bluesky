from __future__ import annotations

from typing import Annotated as A

from ophyd_async.core import (
    SignalRW,
    SignalX,
    StandardReadableFormat as Format,
)

from .fsec_readable_device import FSECReadableDevice, FSECSubscribable


class SIS3820Counter(FSECReadableDevice):
    Counts: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    Offset: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Reset: SignalX

    async def reset(self):
        await self.Reset.trigger()

class SIS3820Subscribable(FSECSubscribable):
    Counts: A[SignalRW[float], Format.HINTED_SIGNAL]
    Offset: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Reset: SignalX
