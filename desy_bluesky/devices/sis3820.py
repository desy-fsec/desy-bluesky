from __future__ import annotations
from typing import Optional, Union

from ophyd_async.core import (
    ConfigSignal,
    HintedSignal,
    SignalR,
    SignalRW,
    SignalX,
)

from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy

from .fsec_readable_device import FSECReadableDevice


# --------------------------------------------------------------------
class SIS3820Counter(FSECReadableDevice):
    Counts: SignalR[float]
    Offset: SignalRW[float]
    Reset: SignalX

    def __init__(
            self,
            trl: Optional[str] = None,
            device_proxy: Optional[Union[AsyncDeviceProxy, SyncDeviceProxy]] = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Counts], HintedSignal)
        self.add_readables([self.Offset], ConfigSignal)

    async def reset(self):
        await self.Reset.trigger()
