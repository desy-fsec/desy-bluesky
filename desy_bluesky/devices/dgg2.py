from __future__ import annotations

from typing import Optional, Union

from bluesky.protocols import Triggerable, Preparable

from ophyd_async.core import (
    AsyncStatus,
)
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    SignalX,
    SignalR,
    SignalRW,
    HintedSignal,
    ConfigSignal
)
from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy

from .fsec_readable_device import FSECReadableDevice


class DGG2Timer(FSECReadableDevice, Triggerable, Preparable):
    SampleTime: SignalRW[float]
    RemainingTime: SignalR[float]
    StartAndWaitForTimer: SignalX
    Start: SignalX

    # --------------------------------------------------------------------
    def __init__(
            self,
            trl: Optional[str] = None,
            device_proxy: Optional[Union[AsyncDeviceProxy, SyncDeviceProxy]] = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self._set_success = True
        self.add_readables([self.SampleTime], HintedSignal)
        self.add_readables([self.SampleTime], ConfigSignal)

    # --------------------------------------------------------------------

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        sample_time = await self.SampleTime.get_value()
        timeout = sample_time + DEFAULT_TIMEOUT
        await self.Start.trigger(wait=False, timeout=timeout)
        await self.wait_for_idle()

    # --------------------------------------------------------------------
    @AsyncStatus.wrap
    async def prepare(self, value: float) -> None:
        await self.SampleTime.set(value)
