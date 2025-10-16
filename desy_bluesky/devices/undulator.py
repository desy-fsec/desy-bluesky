from __future__ import annotations

from typing import Annotated as A, Sequence

import numpy as np

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import (
    soft_signal_rw,
    AsyncStatus,
    SignalRW,
    SignalR,
    SignalX,
    wait_for_value,
    StandardReadableFormat as Format,
    Array1D,
)

from .fsec_readable_device import FSECReadableDevice


class Undulator(FSECReadableDevice, Movable, Stoppable):
    Position: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    PositionSim: SignalRW[float]
    Velocity: SignalRW[float]
    HarmonicSim: SignalRW[int]
    ResultSim: SignalR[Sequence[str]]
    Gap: A[SignalRW[float], Format.UNCACHED_SIGNAL]
    StopMove: SignalX

    def __init__(
        self,
        trl: str,
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
        value: float,
        timeout: float | None = None,
    ):
        self._set_success = True

        await self.Position.set(value, timeout=timeout)
        await wait_for_value(self.State, "ON", timeout=timeout)

    def stop(self, success: bool = True) -> AsyncStatus:
        self._set_success = success
        return self.StopMove.trigger()
