from __future__ import annotations

import asyncio
from asyncio import Event
from typing import Union, Optional

from bluesky.protocols import Movable, Stoppable, Preparable

from ophyd_async.core import observe_value

from ophyd_async.core import (
    WatchableAsyncStatus,
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
    SignalRW,
    SignalX,
    SignalR,
)
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    CalculatableTimeout,
    CalculateTimeout,
    WatcherUpdate
)

from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy

from .fsec_readable_device import FSECReadableDevice


class OmsVME58Motor(FSECReadableDevice, Movable, Stoppable):
    Position: SignalRW
    BaseRate: SignalRW
    SlewRate: SignalRW
    Conversion: SignalRW
    Acceleration: SignalRW
    StopMove: SignalX
    State: SignalR
    
    # --------------------------------------------------------------------
    def __init__(
            self,
            trl: Optional[str] = None,
            device_proxy: Optional[Union[AsyncDeviceProxy, SyncDeviceProxy]] = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self._set_success = True
        self.add_readables([self.Position], HintedSignal)
        self.add_readables([self.BaseRate,
                            self.SlewRate,
                            self.Conversion,
                            self.Acceleration],
                           ConfigSignal)

    @WatchableAsyncStatus.wrap
    async def set(
        self,
        value: float,
        timeout: CalculatableTimeout = CalculateTimeout,
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
        if timeout is CalculateTimeout:
            assert velocity > 0, "Motor has zero velocity"
            timeout = (
                (abs(value - old_position) * conversion / velocity)
                + (2 * velocity / acceleration)
                + DEFAULT_TIMEOUT
            )

        await self.Position.set(value, wait=False, timeout=timeout)

        move_status = self.wait_for_idle()

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

    # --------------------------------------------------------------------
    def stop(self, success: bool = False) -> AsyncStatus:
        self._set_success = success
        return self.StopMove.trigger()
