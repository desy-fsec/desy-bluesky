from __future__ import annotations

from ophyd_async.core import (
    HintedSignal,
    soft_signal_rw,
    SignalR,
    SignalX
)

from .fsec_readable_device import FSECReadableDevice
from tango import DeviceProxy


class VcCounter(FSECReadableDevice):
    Counts: SignalR[int]
    Reset: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Counts], HintedSignal)

        # Not used, I added it here because SIS3820 has it
        self.offset = soft_signal_rw(float, initial_value=0.0)

    async def _reset(self) -> None:
        await self.Reset.trigger()
