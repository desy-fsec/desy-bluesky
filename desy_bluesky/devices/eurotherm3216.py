from __future__ import annotations

import asyncio

from dataclasses import dataclass

from bluesky.protocols import Movable, Flyable, Preparable, Stoppable

from ophyd_async.core import observe_value

from ophyd_async.core import (
    WatchableAsyncStatus,
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
    SignalRW,
    wait_for_value,
    soft_signal_rw,
    StandardReadableFormat as Format,
)
from ophyd_async.core import (
    WatcherUpdate
)

from tango import DeviceProxy, DevState

from .fsec_readable_device import FSECReadableDevice

@dataclass
class Eurotherm3216Config:
    Setpoint: float | None = None
    SetpointRamp: float | None = None

class Eurotherm3216(FSECReadableDevice, Movable, Flyable, Preparable, Stoppable):
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
                            self.SetpointDwell], Format.HINTED_SIGNAL)
        self.add_readables([self.SetpointMin,
                            self.SetpointMax,
                            self.PowerMin,
                            self.PowerMax,
                            self.CurrentPIDSet], Format.CONFIG_SIGNAL)
        self._fly_setpoint = soft_signal_rw(float, None, name="_fly_setpoint")
        self._fly_setpoint_ramp = soft_signal_rw(float, None, name="_fly_setpoint_ramp")
        self._set_success = True

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

    def get_config(self) -> Eurotherm3216Config:
        return Eurotherm3216Config()

    @AsyncStatus.wrap
    async def prepare(self, value: Eurotherm3216Config):
        if value.Setpoint is not None:
            await self._fly_setpoint.set(value.Setpoint)
        if value.SetpointRamp is not None:
            await self._fly_setpoint_ramp.set(value.SetpointRamp)

    @AsyncStatus.wrap
    async def kickoff(self):
        new_setpoint = await self._fly_setpoint.get_value()
        self.set(new_setpoint)

    @AsyncStatus.wrap
    async def complete(self):
        await wait_for_value(self.State, DevState.ON, None)

    @AsyncStatus.wrap
    async def stop(self, success: bool = False):
        self._set_success = success
        await self.Setpoint.set(await self.Temperature.get_value())
        await wait_for_value(self.State, DevState.ON, None)
