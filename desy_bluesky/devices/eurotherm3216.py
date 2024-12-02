from __future__ import annotations

from typing import Annotated as A

import numpy as np

from bluesky.protocols import Movable, Stoppable, SyncOrAsync, Subscribable

from ophyd_async.core import (
    WatchableAsyncStatus,
    AsyncStatus,
    SignalRW,
    set_and_wait_for_other_value,
    StandardReadableFormat as Format,
    WatcherUpdate,
    soft_signal_rw,
    observe_value
)
from ophyd_async.tango.core import (
    TangoPolling,
)

from tango import DeviceProxy

from .fsec_readable_device import FSECReadableDevice

class Eurotherm3216(FSECReadableDevice, Movable, Stoppable, Subscribable):
    """
    Eurotherm 3216 temperature controller

    Attributes
    ----------
    Temperature : SignalRW[float]
        The current temperature (deg C)
    Setpoint : SignalRW[float]
        The setpoint temperature (deg C)
    SetpointRamp : SignalRW[float]
        The setpoint ramp rate (deg C/min)
    SetpointDwell : SignalRW[float]
        The setpoint dwell time (min)
    SetpointMin : SignalRW[float]
        The minimum setpoint temperature (deg C)
    SetpointMax : SignalRW[float]
        The maximum setpoint temperature (deg C)
    PowerMin : SignalRW[float]
        The minimum power
    PowerMax : SignalRW[float]
        The maximum power
    CurrentPIDSet : SignalRW[float]
        The current PID setting
    setpoint_tolerance : SignalRW[float]
        The tolerance for setting the setpoint (deg C). Default is 2.0 deg C
        Setpoint is considered set when the temperature is within this tolerance.
    """
    Temperature: A[SignalRW[float], Format.HINTED_SIGNAL, TangoPolling(0.1, 0.1)]
    Setpoint: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    SetpointRamp: A[SignalRW[float], Format.CONFIG_SIGNAL]
    SetpointDwell: A[SignalRW[float], Format.CONFIG_SIGNAL]
    SetpointMin: A[SignalRW[float], Format.CONFIG_SIGNAL]
    SetpointMax: A[SignalRW[float], Format.CONFIG_SIGNAL]
    PowerMin: A[SignalRW[float], Format.CONFIG_SIGNAL]
    PowerMax: A[SignalRW[float], Format.CONFIG_SIGNAL]
    CurrentPIDSet: A[SignalRW[float], Format.CONFIG_SIGNAL]

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl=trl, device_proxy=device_proxy, name=name)
        self._set_success = False
        self.setpoint_tolerance = soft_signal_rw(float, 2.0, "setpoint_tolerance", "C")
        self.add_readables([self.setpoint_tolerance], Format.CONFIG_SIGNAL)

    @WatchableAsyncStatus.wrap
    async def set(self, value: float, timeout=None):
        self._set_success = True
        old_temperature = await self.Temperature.get_value()
        tol = await self.setpoint_tolerance.get_value()
        move_status = AsyncStatus(set_and_wait_for_other_value(self.Setpoint, value, self.Temperature,
                                                               lambda v: np.isclose(v, value, atol=tol),
                                                               timeout=timeout))

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

    def stop(self, success: bool = False) -> SyncOrAsync:
        self._set_success = success
        async def _stop():
            setp = await self.Setpoint.get_value()
            tol = await self.setpoint_tolerance.get_value()
            await set_and_wait_for_other_value(self.Setpoint, setp, self.Temperature,
                                               lambda v: np.isclose(v, setp, atol=tol))
        return _stop()

    def subscribe(self, cb):
        return self.Temperature.subscribe(cb)

    def clear_sub(self, sub):
        self.Temperature.clear_sub(sub)