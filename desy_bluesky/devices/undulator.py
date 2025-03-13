from __future__ import annotations

from typing import Annotated as A

import numpy as np

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    soft_signal_rw,
    AsyncStatus,
    SignalRW,
    SignalX,
    wait_for_value,
    StandardReadableFormat as Format,
    Array1D
)


from tango import DevState

from .fsec_readable_device import FSECReadableDevice


class Undulator(FSECReadableDevice, Movable, Stoppable):
    Position: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    PositionSim: A[SignalRW[float], Format.UNCACHED_SIGNAL]
    Velocity: A[SignalRW[float], Format.UNCACHED_SIGNAL]
    HarmonicSim: A[SignalRW[int], Format.UNCACHED_SIGNAL]
    ResultSim: A[Array1D[np.str_], Format.UNCACHED_SIGNAL]
    Gap: A[SignalRW[float], Format.UNCACHED_SIGNAL]
    StopMove: SignalX

    def __init__(
        self,
        trl: str | None = None,
        name: str = "",
        offset: float = 0.0,
    ) -> None:
        self._set_success = True
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.Offset = soft_signal_rw(float, initial_value=offset)
        super().__init__(trl, name)        

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
