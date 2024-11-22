from __future__ import annotations

from typing import Annotated as A

from ophyd_async.core import (
    soft_signal_rw,
    SignalR,
    SignalX,
    StandardReadableFormat as Format,
)

from .fsec_readable_device import FSECReadableDevice
from tango import DeviceProxy


class VcCounter(FSECReadableDevice):
    Counts: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    Reset: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        # Not used, I added it here because SIS3820 has it
        self.offset = soft_signal_rw(float, initial_value=0.0)

    async def _reset(self) -> None:
        await self.Reset.trigger()
