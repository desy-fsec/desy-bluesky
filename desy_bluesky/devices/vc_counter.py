from __future__ import annotations

from typing import Optional, Union

from ophyd_async.core import (
    HintedSignal,
    soft_signal_rw,
    SignalR,
    SignalX
)

from .fsec_readable_device import FSECReadableDevice
from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy


class VcCounter(FSECReadableDevice):
    Counts: SignalR
    Reset: SignalX

    def __init__(
            self,
            trl: Optional[str] = None,
            device_proxy: Optional[Union[AsyncDeviceProxy, SyncDeviceProxy]] = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Counts], HintedSignal)

        # Not used, I added it here because SIS3820 has it
        self.offset = soft_signal_rw(float, initial_value=0.0)

    async def _reset(self) -> None:
        await self.Reset.trigger()
