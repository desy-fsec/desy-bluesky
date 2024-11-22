from __future__ import annotations

from typing import Annotated as A

from ophyd_async.core import (
    SignalRW,
    SignalX,
    StandardReadableFormat as Format,
)

from .fsec_readable_device import FSECReadableDevice


# --------------------------------------------------------------------
class SIS3820Counter(FSECReadableDevice):
    Counts: A[SignalRW[int], Format.HINTED_UNCACHED_SIGNAL]
    Offset: A[SignalRW[int], Format.CONFIG_SIGNAL]
    Reset: SignalX

    async def reset(self):
        await self.Reset.trigger()
