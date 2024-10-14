from __future__ import annotations

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    soft_signal_rw,
    AsyncStatus,
    HintedSignal,
    ConfigSignal,
    SignalRW,
    WatchableAsyncStatus,
    SignalX,
    wait_for_value,
)

from tango import DeviceProxy, DevState

from .fsec_readable_device import FSECReadableDevice


class Undulator(FSECReadableDevice, Movable, Stoppable):
    Position: SignalRW[float]
    StopMove: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
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

        move_status = AsyncStatus(wait_for_value(self.State, DevState.ON, timeout=timeout))
        return move_status

    # --------------------------------------------------------------------

    def stop(self, success: bool = True) -> AsyncStatus:
        self._set_success = success
        return self.StopMove.trigger()
