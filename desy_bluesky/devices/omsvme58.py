from __future__ import annotations

from typing import Annotated as A

import asyncio

from bluesky.protocols import Movable, Stoppable, SyncOrAsync

from ophyd_async.core import (
    AsyncStatus,
    SignalRW,
    SignalR,
    SignalX,
    wait_for_value,
    DEFAULT_TIMEOUT,
    CalculatableTimeout,
    CALCULATE_TIMEOUT,
    StandardReadableFormat as Format,
    Ignore,
)
from ophyd_async.tango.core import TangoPolling


from .fsec_readable_device import FSECReadableDevice, FSECSubscribable


class OmsVME58Motor(FSECReadableDevice, Movable, Stoppable):
    Position: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    SlewRate: A[SignalRW[int], Format.CONFIG_SIGNAL]
    SlewRateMax: A[SignalRW[int], Format.CONFIG_SIGNAL]
    Conversion: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Acceleration: A[SignalRW[int], Format.CONFIG_SIGNAL]
    StopMove: SignalR[int]
    # Signals with different input/output types are not supported and must be ignored
    Calibrate: Ignore
    Move: Ignore
    MoveLoop: Ignore
    SetupUnitMove: Ignore
    UserCalibrate: Ignore
    movevvc: Ignore

    @AsyncStatus.wrap
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
        await self.Position.set(value, timeout=timeout)
        await wait_for_value(self.State, "ON", timeout=float(timeout))

    @AsyncStatus.wrap
    async def stop(self, success: bool = False):
        self._set_success = success
        await self.StopMove.get_value()


class OmsVME58MotorNoEncoder(OmsVME58Motor):
    Position: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    SlewRate: A[SignalRW[int], Format.CONFIG_SIGNAL]
    SlewRateMax: A[SignalRW[int], Format.CONFIG_SIGNAL]
    Conversion: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Acceleration: A[SignalRW[int], Format.CONFIG_SIGNAL]
    StopMove: SignalR[int]
    PositionEncoder: Ignore
    PositionEncoderRaw: Ignore
    StepPositionController: A[SignalRW[int], Format.UNCACHED_SIGNAL]


class OmsVME58MotorEncoder(OmsVME58Motor):
    Position: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    SlewRate: A[SignalRW[int], Format.CONFIG_SIGNAL]
    SlewRateMax: A[SignalRW[int], Format.CONFIG_SIGNAL]
    Conversion: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Acceleration: A[SignalRW[int], Format.CONFIG_SIGNAL]
    StopMove: SignalR[int]
    PositionEncoder: A[SignalR[float], Format.UNCACHED_SIGNAL]
    PositionEncoderRaw: A[SignalR[float], Format.UNCACHED_SIGNAL]


class PolledOmsVME58MotorEncoder(FSECSubscribable, OmsVME58Motor):
    Position: A[SignalRW[float], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1)]
    SlewRate: A[SignalRW[int], Format.CONFIG_SIGNAL]
    SlewRateMax: A[SignalRW[int], Format.CONFIG_SIGNAL]
    Conversion: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Acceleration: A[SignalRW[int], Format.CONFIG_SIGNAL]
    StopMove: SignalR[int]
    PositionEncoder: A[SignalR[float], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1)]
    PositionEncoderRaw: A[SignalR[float], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1)]


class PolledOmsVME58MotorNoEncoder(FSECSubscribable, OmsVME58Motor):
    Position: A[SignalRW[float], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1)]
    StepPositionController: A[
        SignalRW[int], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1)
    ]
    SlewRate: A[SignalRW[int], Format.CONFIG_SIGNAL]
    SlewRateMax: A[SignalRW[int], Format.CONFIG_SIGNAL]
    Conversion: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Acceleration: A[SignalRW[int], Format.CONFIG_SIGNAL]
    StopMove: SignalR[int]
    PositionEncoder: Ignore
    PositionEncoderRaw: Ignore
