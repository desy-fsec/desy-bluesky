from __future__ import annotations

from ophyd_async.core import (
    ConfigSignal,
    HintedSignal,
    SignalR,
    SignalRW,
    SignalX,
)

from tango import DeviceProxy

from .fsec_readable_device import FSECReadableDevice


# --------------------------------------------------------------------
class SIS3820Counter(FSECReadableDevice):
    Counts: SignalR[float]
    Offset: SignalRW[float]
    Reset: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Counts], HintedSignal)
        self.add_readables([self.Offset], ConfigSignal)

    async def reset(self):
        await self.Reset.trigger()
