from __future__ import annotations

from typing import Optional, Union

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    soft_signal_rw,
    AsyncStatus,
    HintedSignal,
    ConfigSignal,
    SignalRW,
    WatchableAsyncStatus,
    SignalX
)

from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy

from .fsec_readable_device import FSECReadableDevice


class Undulator(FSECReadableDevice, Movable, Stoppable):
    Position: SignalRW[float]
    StopMove: SignalX

    def __init__(
            self,
            trl: Optional[str] = None,
            device_proxy: Optional[Union[AsyncDeviceProxy, SyncDeviceProxy]] = None,
            name: str = "",
            offset: float = 0.0,
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Position], HintedSignal)
        with self.add_children_as_readables(ConfigSignal):
            self.Offset = soft_signal_rw(float, initial_value=offset)
        self._set_success = True

    # --------------------------------------------------------------------

    @WatchableAsyncStatus.wrap
    async def set(
        self,
        new_position: float,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._set_success = True

        await self.Position.set(new_position, timeout=timeout)

        move_status = self.wait_for_idle()
        return move_status

    # --------------------------------------------------------------------

    def stop(self, success: bool = True) -> AsyncStatus:
        self._set_success = success
        return self.StopMove.trigger()
