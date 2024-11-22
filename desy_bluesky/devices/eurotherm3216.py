from __future__ import annotations

from typing import Annotated as A

from dataclasses import dataclass

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import observe_value

from ophyd_async.core import (
    WatchableAsyncStatus,
    AsyncStatus,
    SignalRW,
    set_and_wait_for_other_value,
    StandardReadableFormat as Format,
    WatcherUpdate
)
from ophyd_async.tango.core import (
    TangoPolling,
)

from .fsec_readable_device import FSECReadableDevice

class Eurotherm3216(FSECReadableDevice, Movable, Stoppable):
    Temperature: A[SignalRW[float], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1)]
    Setpoint: SignalRW[float]
    WorkingSetpoint: SignalRW[float]
    SetpointRamp: A[SignalRW[float], Format.CONFIG_SIGNAL]
    SetpointDwell: A[SignalRW[float], Format.CONFIG_SIGNAL]
    SetpointMin: A[SignalRW[float], Format.CONFIG_SIGNAL]
    SetpointMax: A[SignalRW[float], Format.CONFIG_SIGNAL]
    PowerMin: A[SignalRW[float], Format.CONFIG_SIGNAL]
    PowerMax: A[SignalRW[float], Format.CONFIG_SIGNAL]
    CurrentPIDSet: A[SignalRW[float], Format.CONFIG_SIGNAL]

    @WatchableAsyncStatus.wrap
    async def set(self, value: float, timeout=None):
        self._set_success = True
        old_temperature = await self.Temperature.get_value()
        
        move_status = AsyncStatus(set_and_wait_for_other_value(self.Setpoint, value, self.Temperature, value, timeout=timeout))

        try:
            async for current_temperature in observe_value(
                self.Temperature, done_status=move_status
            ):
                yield WatcherUpdate(
                    current=current_temperature,
                    initial=old_temperature,
                    target=value,
                    name=self.name,
                )
        except RuntimeError as exc:
            raise RuntimeError(f"{exc}") from exc
        if not self._set_success:
            raise RuntimeError("Motor was stopped")

    @AsyncStatus.wrap
    async def stop(self, success: bool = False):
        self._set_success = success
        setp = await self.Setpoint.get_value()
        await set_and_wait_for_other_value(self.Setpoint, setp, self.Temperature, setp)
