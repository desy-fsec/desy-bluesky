from __future__ import annotations

from typing import Annotated as A

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    soft_signal_rw,
    AsyncStatus,
    SignalRW,
    SignalR,
    WatchableAsyncStatus,
    SignalX,
    wait_for_value,
    StandardReadableFormat as Format,
)

from ophyd_async.tango.core import (
    TangoPolling
)

from tango import DeviceProxy, DevState

from .fsec_readable_device import FSECReadableDevice


class Undulator(FSECReadableDevice, Movable, Stoppable):
    Position: A[SignalRW[float], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1, 0.1)]
    PositionSim: A[SignalRW[float], Format.UNCACHED_SIGNAL]
    Velocity: A[SignalRW[float], Format.UNCACHED_SIGNAL]
    HarmonicSim: A[SignalRW[int], Format.UNCACHED_SIGNAL]
    ResultSim: A[SignalR[str], Format.UNCACHED_SIGNAL]
    Gap: A[SignalRW[float], Format.UNCACHED_SIGNAL]
    StopMove: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
            offset: float = 0.0,
    ) -> None:
        super().__init__(trl, device_proxy, name)
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.Offset = soft_signal_rw(float, initial_value=offset)
        self._set_success = True
        
    @AsyncStatus.wrap
    async def set(
        self,
        new_position: float,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._set_success = True

        await self.Position.set(new_position, timeout=timeout)
        await wait_for_value(self.State, DevState.ON, timeout=timeout)
    

    def stop(self, success: bool = True) -> AsyncStatus:
        self._set_success = success
        return self.StopMove.trigger()
