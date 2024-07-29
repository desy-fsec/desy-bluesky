from __future__ import annotations

from typing import Dict
from typing import Optional

from bluesky.protocols import Movable, Stoppable, Reading, Preparable, Status

import asyncio
from asyncio import Event

from ophyd_async.core import (
    soft_signal_rw,
    AsyncStatus,
    HintedSignal,
    ConfigSignal,
    WatchableAsyncStatus,
)
from ophyd_async.core.signal import observe_value
from ophyd_async.core.utils import (
    DEFAULT_TIMEOUT,
    WatcherUpdate,
)
from ophyd_async.tango import (
    TangoReadableDevice,
    tango_signal_r,
    tango_signal_rw,
    tango_signal_x,
)
from tango import DevState


class Undulator(TangoReadableDevice, Stoppable, Preparable, Movable):
    trl: str
    name: str
    src_dict: dict
    offset: float
    position: tango_signal_rw
    _state: tango_signal_r
    _stop: tango_signal_x

    def __init__(
        self, trl: str, name: str = "", sources: dict = None, offset: float = 0
    ) -> None:
        if sources is None:
            sources = {}
        self.trl = trl
        self.src_dict = sources
        self.src_dict["position"] = sources.get("position", "/Position")
        self.src_dict["state"] = sources.get("state", "/State")
        self.src_dict["stop"] = sources.get("stop", "/StopMove")
        

        for key in self.src_dict:
            if not self.src_dict[key].startswith("/"):
                self.src_dict[key] = "/" + self.src_dict[key]

        with self.add_children_as_readables(HintedSignal):
            self.position = tango_signal_rw(
                float, trl + self.src_dict["position"], device_proxy=self.proxy
            )
        self._state = tango_signal_r(DevState, trl + self.src_dict["state"], self.proxy)
        self._stop = tango_signal_x(
            trl + self.src_dict["stop"], device_proxy=self.proxy
        )
        
        with self.add_children_as_readables(ConfigSignal):
            self.offset = soft_signal_rw(float, initial_value=offset)

        TangoReadableDevice.__init__(self, trl, name)
        self._set_success = True

    # --------------------------------------------------------------------

    @WatchableAsyncStatus.wrap
    async def set(
        self,
        new_position: float,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._set_success = True
        old_position = await self.position.get_value()

        await self.position.set(new_position, wait=True, timeout=timeout)

        move_status = AsyncStatus(self._wait())

        try:
            async for current_position in observe_value(
                self.position, done_status=move_status
            ):
                yield WatcherUpdate(
                    current=current_position,
                    initial=old_position,
                    target=new_position,
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

    async def read(self) -> Dict[str, Reading]:
        ret = await super().read()
        return ret

    # --------------------------------------------------------------------

    def prepare(self, value: float) -> Status:
        self.offset.put(value)
        # Return a dummy status
        return Status()

    # --------------------------------------------------------------------

    async def _wait(self, event: Optional[Event] = None) -> None:
        await asyncio.sleep(0.5)
        state = await self._state.get_value()
        try:
            while state == DevState.MOVING:
                await asyncio.sleep(0.1)
                state = await self._state.get_value()
        except Exception as e:
            raise RuntimeError(f"Error waiting for motor to stop: {e}")
        finally:
            if event:
                event.set()
            if state != DevState.ON:
                raise RuntimeError(f"Motor did not stop correctly. State {state}")
