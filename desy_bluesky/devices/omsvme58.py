from __future__ import annotations

from typing import Annotated as A

import asyncio

from bluesky.protocols import Movable, Stoppable, SyncOrAsync, Subscribable

from ophyd_async.core import (
    WatchableAsyncStatus,
    AsyncStatus,
    SignalRW,
    SignalX,
    SignalR,
    wait_for_value,
    observe_value,
    DEFAULT_TIMEOUT,
    CalculatableTimeout,
    CALCULATE_TIMEOUT,
    WatcherUpdate,
    StandardReadableFormat as Format,
)
from ophyd_async.tango.core import (
    TangoPolling
)

from tango import DevState

from .fsec_readable_device import FSECReadableDevice

class OmsVME58Motor(FSECReadableDevice, Movable, Stoppable):
    Position: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    # PositionEncoder: A[SignalR[float], Format.UNCACHED_SIGNAL]
    SlewRate: A[SignalRW[float], Format.CONFIG_SIGNAL]
    SlewRateMax: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Conversion: A[SignalRW[float], Format.CONFIG_SIGNAL]
    Acceleration: A[SignalRW[float], Format.CONFIG_SIGNAL]
    StopMove: SignalX
    
    # @WatchableAsyncStatus.wrap
    # async def set(
    #     self,
    #     value: float,
    #     timeout: CalculatableTimeout = CALCULATE_TIMEOUT,
    # ):
    #     self._set_success = True
    #     (
    #         old_position,
    #         conversion,
    #         velocity,
    #         acceleration,
    #     ) = await asyncio.gather(
    #         self.Position.get_value(),
    #         self.Conversion.get_value(),
    #         self.SlewRate.get_value(),
    #         self.Acceleration.get_value(),
    #     )
    #     if timeout is CALCULATE_TIMEOUT:
    #         assert velocity > 0, "Motor has zero velocity"
    #         timeout = (
    #             (abs(value - old_position) * conversion / velocity)
    #             + (2 * velocity / acceleration)
    #             + DEFAULT_TIMEOUT
    #         )
    #     await self.Position.set(value, wait=False, timeout=timeout)
    #     move_status = AsyncStatus(wait_for_value(self.State, DevState.ON, timeout=timeout))
    #     try:
    #         async for current_position in observe_value(
    #                 self.Position, done_status=move_status
    #         ):
    #             yield WatcherUpdate(
    #                 current=current_position,
    #                 initial=old_position,
    #                 target=value,
    #                 name=self.name,
    #             )
    #     except RuntimeError as exc:
    #         print(f"RuntimeError: {exc}")
    #         raise
    #     if not self._set_success:
    #         raise RuntimeError("Motor was stopped")

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

        await self.Position.set(value, wait=False, timeout=timeout)

        await wait_for_value(self.State, DevState.ON, timeout=timeout)

    def stop(self, success: bool = False) -> SyncOrAsync:
        self._set_success = success
        return self.StopMove.trigger()
