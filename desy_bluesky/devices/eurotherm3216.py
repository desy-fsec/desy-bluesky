from __future__ import annotations

import asyncio

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import observe_value

from ophyd_async.core import (
    WatchableAsyncStatus,
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
    SignalRW,
    SignalX,
    wait_for_value,
)
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    CalculatableTimeout,
    CALCULATE_TIMEOUT,
    WatcherUpdate
)

from tango import DeviceProxy, DevState

from .fsec_readable_device import FSECReadableDevice


class Eurotherm3216(FSECReadableDevice, Movable):
    Temperature: SignalRW[float]
    Setpoint: SignalRW[float]
    SetpointMin: SignalRW[float]
    SetpointMax: SignalRW[float]
    PowerMin: SignalRW[float]
    PowerMax: SignalRW[float]
    WorkingSetpoint: SignalRW[float]
    SetpointRamp: SignalRW[float]
    SetpointDwell: SignalRW[float]
    CurrentPIDSet: SignalRW[float]

    # --------------------------------------------------------------------

    def __init__(self, trl: str | None = None, device_proxy: DeviceProxy | None = None, name: str = "") -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Temperature,
                            self.Setpoint,
                            self.WorkingSetpoint,
                            self.SetpointRamp,
                            self.SetpointDwell], HintedSignal)
        self.add_readables([self.SetpointMin,
                            self.SetpointMax,
                            self.PowerMin,
                            self.PowerMax,
                            self.CurrentPIDSet], ConfigSignal)

    @WatchableAsyncStatus.wrap
    async def set(self, value: float, timeout=None):
        self._set_success = True
        (old_temperature, ramp_rate) = await asyncio.gather(self.Temperature.get_value(), self.SetpointRamp.get_value())

        await self.Setpoint.set(value)

        move_status = AsyncStatus(wait_for_value(self.State, DevState.ON, timeout=timeout))

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