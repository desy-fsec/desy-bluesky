from __future__ import annotations

import asyncio

from bluesky.protocols import Movable, Stoppable, Preparable, Flyable

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
    WatcherUpdate,
    soft_signal_rw
)

from tango import DeviceProxy, DevState

from .fsec_readable_device import FSECReadableDevice

class OmsVME58Motor(FSECReadableDevice, Movable, Stoppable, Preparable, Flyable):
    Position: SignalRW[float]
    SlewRate: SignalRW[int]
    Conversion: SignalRW[float]
    Acceleration: SignalRW[int]
    StopMove: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self._set_success = True
        self.add_readables([self.Position], HintedSignal)
        self.add_readables([self.SlewRate,
                            self.Conversion,
                            self.Acceleration],
                           ConfigSignal)
        self._fly_setpoint = soft_signal_rw(float, None, name="_fly_setpoint")

    @WatchableAsyncStatus.wrap
    async def set(
        self,
        value: float,
        timeout: CalculatableTimeout = CALCULATE_TIMEOUT,
    ):
        self._set_success = True
        (
            old_position,
            conversion,
            velocity,
            acceleration,
        ) = await asyncio.gather(
            self.Position.get_value(),
            self.Conversion.get_value(),
            self.SlewRate.get_value(),
            self.Acceleration.get_value(),
        )
        if timeout is CALCULATE_TIMEOUT:
            assert velocity > 0, "Motor has zero velocity"
            timeout = (
                (abs(value - old_position) * conversion / velocity)
                + (2 * velocity / acceleration)
                + DEFAULT_TIMEOUT
            )

        await self.Position.set(value, wait=False, timeout=timeout)

        move_status = AsyncStatus(wait_for_value(self.State, DevState.ON, timeout=timeout))

        try:
            async for current_position in observe_value(
                    self.Position, done_status=move_status
            ):
                yield WatcherUpdate(
                    current=current_position,
                    initial=old_position,
                    target=value,
                    name=self.name,
                )
        except RuntimeError as exc:
            print(f"RuntimeError: {exc}")
            raise
        if not self._set_success:
            raise RuntimeError("Motor was stopped")

    def stop(self, success: bool = False) -> AsyncStatus:
        self._set_success = success
        return self.StopMove.trigger()

    @AsyncStatus.wrap
    async def prepare(self, value):
        try:
            fvalue = float(value)
            await self._fly_setpoint.set(fvalue)
        except ValueError:
            raise ValueError("Setpoint must be a float")

    @AsyncStatus.wrap
    async def kickoff(self):
        new_position = await self._fly_setpoint.get_value()
        self.set(new_position)

    @AsyncStatus.wrap
    async def complete(self):
        await wait_for_value(self.State, DevState.ON, None)

