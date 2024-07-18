from __future__ import annotations

import asyncio
from asyncio import Event
from typing import Optional

from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import (
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
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


class VmMotor(TangoReadableDevice, Stoppable, Movable):
    # --------------------------------------------------------------------
    def __init__(self, trl: str, name: str = "", sources: dict = None,
                 md: dict = None) -> None:
        if md is None:
            me = {}
        self.md = md
        if sources is None:
            sources = {}
        self.trl = trl
        self.src_dict["position"] = sources.get("position", "/Position")
        self.src_dict["cwlimit"] = sources.get("cwlimit", "/CWLimit")
        self.src_dict["ccwlimit"] = sources.get("ccwlimit", "/CCWLimit")
        self.src_dict["unitlimitmin"] = sources.get("unitlimitmin", "/UnitLimitMin")
        self.src_dict["unitlimitmax"] = sources.get("unitlimitmax", "/UnitLimitMax")
        self.src_dict["stop"] = sources.get("stop", "/StopMove")
        self.src_dict["state"] = sources.get("state", "/State")

        for key in self.src_dict:
            if not self.src_dict[key].startswith("/"):
                self.src_dict[key] = "/" + self.src_dict[key]

        with self.add_children_as_readables(HintedSignal):
            self.position = tango_signal_rw(
                float, trl + self.src_dict["position"], device_proxy=self.proxy
            )
        with self.add_children_as_readables(ConfigSignal):
            self.cwlimit = tango_signal_rw(
                int, trl + self.src_dict["cwlimit"], device_proxy=self.proxy
            )
            self.ccwlimit = tango_signal_rw(
                int, trl + self.src_dict["ccwlimit"], device_proxy=self.proxy
            )
            self.unitlimitmin = tango_signal_rw(
                float, trl + self.src_dict["unitlimitmin"], device_proxy=self.proxy
            )
            self.unitlimitmax = tango_signal_rw(
                float, trl + self.src_dict["unitlimitmax"], device_proxy=self.proxy
            )
        self._stop = tango_signal_x(trl + self.src_dict["stop"], self.proxy)
        self._state = tango_signal_r(DevState, trl + self.src_dict["state"], self.proxy)

        TangoReadableDevice.__init__(self, trl, name)
        self._set_success = True

    # --------------------------------------------------------------------

    @WatchableAsyncStatus.wrap
    async def set(self, new_position: float, timeout: float = DEFAULT_TIMEOUT):
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
    async def stop(self, success: bool = False) -> None:
        self._set_success = success
        # Put with completion will never complete as we are waiting for completion on
        # the move above, so need to pass wait=False
        await self._stop.trigger()

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

    async def _update_md(self):
        async def update_signal_values(d):
            for k, v in list(d.items()):
                if isinstance(v, dict):
                    await update_signal_values(v)
                elif k == 'signal' and 'value' in d:
                    signal_name = d['signal']
                    signal = getattr(self, signal_name)
                    # If the signal is cached, use the last cached value
                    if signal._get_cache() and signal._get_cache()._value is not None:
                        d['value'] = signal._get_cache()._value
                    else:
                        d['value'] = await signal.get_value()

        await update_signal_values(self.md)

    # overwrite the read method to update the metadata after normal read
    async def read(self):
        ret = await super().read()
        await self._update_md()
        return ret


