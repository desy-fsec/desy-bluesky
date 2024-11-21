from __future__ import annotations

from ophyd_async.core import (
    ConfigSignal,
    HintedSignal,
    SignalRW,
    SignalX,
    StandardReadableFormat as Format,
)

from tango import DeviceProxy

from .fsec_readable_device import FSECReadableDevice


# --------------------------------------------------------------------
class SIS3820Counter(FSECReadableDevice):
    Counts: SignalRW[float]
    Offset: SignalRW[float]
    Reset: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Counts], Format.HINTED_SIGNAL)
        self.add_readables([self.Offset], Format.CONFIG_SIGNAL)

    async def reset(self):
        await self.Reset.trigger()
