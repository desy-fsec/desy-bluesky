from __future__ import annotations

from typing import Annotated as A

from ophyd_async.core import (
    soft_signal_rw,
    SignalRW,
    SignalX,
    StandardReadableFormat as Format,
)

from .fsec_readable_device import FSECReadableDevice


class VcCounter(FSECReadableDevice):
    Counts: A[SignalRW[int], Format.HINTED_UNCACHED_SIGNAL]
    Reset: SignalX

    def __init__(
        self,
        trl: str,
        name: str = "",
    ) -> None:
        # Not used, I added it here because SIS3820 has it
        self.offset = soft_signal_rw(float, initial_value=0.0)
        super().__init__(trl, name)
        

    async def _reset(self) -> None:
        await self.Reset.trigger()
