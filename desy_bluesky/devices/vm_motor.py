from __future__ import annotations

from typing import Optional, Union

from bluesky.protocols import Stoppable

from ophyd_async.core import (
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
)

from ophyd_async.core import (
    SignalR,
    SignalX,
    SignalRW,
    DEFAULT_TIMEOUT,
)

from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy

from .fsec_readable_device import FSECReadableDevice


class VmMotor(FSECReadableDevice, Stoppable):
    Position: SignalRW
    CwLimit: SignalR
    CcwLimit: SignalR
    UnitLimitMin: SignalR
    UnitLimitMax: SignalR
    StopMove: SignalX
    State: SignalR

    # --------------------------------------------------------------------
    def __init__(
            self,
            trl: Optional[str] = None,
            device_proxy: Optional[Union[AsyncDeviceProxy, SyncDeviceProxy]] = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Position], HintedSignal)
        self.add_readables([self.CwLimit,
                            self.CcwLimit,
                            self.UnitLimitMin,
                            self.UnitLimitMax], ConfigSignal)
        self._set_success = True

    # --------------------------------------------------------------------

    @AsyncStatus.wrap
    async def set(self, new_position: float, timeout: float = DEFAULT_TIMEOUT):
        await self.Position.set(new_position, wait=True, timeout=timeout)
        self._set_success = True

    # --------------------------------------------------------------------
    @AsyncStatus.wrap
    async def stop(self, success=True) -> None:
        self._set_success = success
        await self.StopMove.trigger(wait=True)
