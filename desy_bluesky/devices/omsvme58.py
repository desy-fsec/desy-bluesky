from __future__ import annotations

import asyncio
from asyncio import Event
import time
from typing import Optional, List, Callable
from dataclasses import dataclass

from bluesky.protocols import Movable, Stoppable, Preparable

from ophyd_async.core.signal import observe_value

from ophyd_async.core import (
    WatchableAsyncStatus,
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
    SignalRW,
    SignalX
)
from ophyd_async.core.utils import (
    DEFAULT_TIMEOUT,
    CalculatableTimeout,
    CalculateTimeout,
    WatcherUpdate
)
from ophyd_async.tango import (
    TangoReadableDevice,
    tango_signal_r,
    tango_signal_rw,
    tango_signal_x,
)
from tango import DevState

@dataclass
class OmsVME58MotorConfig:
    baserate: Optional[int] = None
    slewrate: Optional[int] = None
    conversion: Optional[float] = None
    acceleration: Optional[int] = None

# --------------------------------------------------------------------
class OmsVME58Motor(TangoReadableDevice, Movable, Stoppable, Preparable):
    """
    0ms VME58 motor device class
    
    Parameters
    ----------
    trl : str
        The Tango device server address
    name : str
        The name of the motor
    sources : dict
        A dictionary of the sources for the motor signals
    
    Attributes
    ----------
    position : SignalRW[float]
        The current position of the motor
    baserate : SignalRW[int]
        The base rate of the motor
    slewrate : SignalRW[int]
        The slew rate of the motor
    conversion : SignalRW[float]
        The step to egu conversion factor
    acceleration : SignalRW[int]
        The acceleration of the motor
    _stop : SignalX
        The signal to stop the motor
    _state : SignalRW[DevState]
    
    Methods
    -------
    set(value: float, timeout: CalculatableTimeout = CalculateTimeout, watchers: Optional[List[Callable]] = None) -> AsyncStatus
        Move the motor to a new position
    stop(success: bool = False) -> AsyncStatus
        Stop the motor
    
    
    
    """
    position: SignalRW[float]
    baserate: SignalRW[int]
    slewrate: SignalRW[int]
    conversion: SignalRW[float]
    acceleration: SignalRW[int]
    _stop: SignalX
    _state: SignalRW[DevState]
    
    # --------------------------------------------------------------------
    def __init__(self, trl: str, name: str = "", sources: dict = None) -> None:
        if sources is None:
            sources = {}
        self.src_dict["position"] = sources.get("position", "/Position")
        self.src_dict["baserate"] = sources.get("baserate", "/BaseRate")
        self.src_dict["slewrate"] = sources.get("slewrate", "/SlewRate")
        self.src_dict["conversion"] = sources.get("conversion", "/Conversion")
        self.src_dict["acceleration"] = sources.get("acceleration", "/Acceleration")
        self.src_dict["stop"] = sources.get("stop", "/StopMove")
        self.src_dict["state"] = sources.get("state", "/State")
        
        for key, value in self.src_dict.items():
            if not value.startswith("/"):
                self.src_dict[key] = "/" + value

        with self.add_children_as_readables(HintedSignal):
            self.position = tango_signal_rw(
                float, trl + self.src_dict["position"], device_proxy=self.proxy
            )
        with self.add_children_as_readables(ConfigSignal):
            self.baserate = tango_signal_rw(
                int, trl + self.src_dict["baserate"], device_proxy=self.proxy
            )
            self.slewrate = tango_signal_rw(
                int, trl + self.src_dict["slewrate"], device_proxy=self.proxy
            )
            self.conversion = tango_signal_rw(
                float, trl + self.src_dict["conversion"], device_proxy=self.proxy
            )
            self.acceleration = tango_signal_rw(
                int, trl + self.src_dict["acceleration"], device_proxy=self.proxy
            )

        self._stop = tango_signal_x(trl + self.src_dict["stop"], self.proxy)
        self._state = tango_signal_r(DevState, trl + self.src_dict["state"], self.proxy)

        TangoReadableDevice.__init__(self, trl, name)
        self._set_success = True

    # --------------------------------------------------------------------
    def set(
        self,
        value: float,
        timeout: CalculatableTimeout = CalculateTimeout,
    ):
        return WatchableAsyncStatus(self._set(value, timeout))
    
    # --------------------------------------------------------------------
    async def _set(
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
            self.position.get_value(),
            self.conversion.get_value(),
            self.slewrate.get_value(),
            self.acceleration.get_value(),
        )
        if timeout is CalculateTimeout:
            assert velocity > 0, "Motor has zero velocity"
            timeout = (
                (abs(value - old_position) * conversion / velocity)
                + (2 * velocity / acceleration)
                + DEFAULT_TIMEOUT
            )

        await self.position.set(value, wait=False, timeout=timeout)

        move_status = AsyncStatus(self._wait())
        
        try:
           async for current_position in observe_value(
               self.position, done_status=move_status
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
        return self._stop.trigger()

    # --------------------------------------------------------------------
    async def _wait(self, event: Optional[Event] = None) -> None:

        await asyncio.sleep(0.5)
        state = await self._state.get_value()
        try:
            while state == DevState.MOVING:
                await asyncio.sleep(0.1)
                state = await self._state.get_value()
        except Exception as e:
            raise RuntimeError(f"Error waiting for motor to stop: {e}") from e
        finally:
            if event:
                event.set()
            if state != DevState.ON:
                raise RuntimeError(f"Motor did not stop correctly. State {state}")
            
    # --------------------------------------------------------------------
    def prepare(self, value: OmsVME58MotorConfig) -> AsyncStatus:
        return AsyncStatus(self._prepare(value))
    
    # --------------------------------------------------------------------
    async def _prepare(self, value: OmsVME58MotorConfig) -> None:
        config = value.__dataclass_fields__
        for key, v in config.items():
            if v is not None:
                if hasattr(self, key):
                    await getattr(self, key).set(v)
    
    # --------------------------------------------------------------------
    async def get_dataclass(self) -> OmsVME58MotorConfig:
        return OmsVME58MotorConfig()
