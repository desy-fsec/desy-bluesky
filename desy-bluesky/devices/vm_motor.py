import asyncio
import time
from typing import Callable, List, Optional

from ophyd_async.core import AsyncStatus
from bluesky.protocols import (
    Locatable,
    Location,
    Stoppable,
    Movable,
)
from ophyd_async.tango import (
    TangoReadableDevice,
    tango_signal_r,
    tango_signal_rw,
    tango_signal_x
)
from tango import DevState


class VmMotor(TangoReadableDevice, Locatable, Stoppable, Movable):
    # --------------------------------------------------------------------
    def __init__(self, trl: str, name: str = "") -> None:
        TangoReadableDevice.__init__(self, trl, name)
        self._set_success = True

    # --------------------------------------------------------------------
    def register_signals(self) -> None:
        self.position = tango_signal_rw(
            float, self.trl + "/Position", device_proxy=self.proxy
        )
        self.cwlimit = tango_signal_rw(
            int, self.trl + "/CWLimit", device_proxy=self.proxy
        )
        self.ccwlimit = tango_signal_rw(
            int, self.trl + "/CCWLimit", device_proxy=self.proxy
        )
        self.unitlimitmin = tango_signal_rw(
            float, self.trl + "/UnitLimitMin", device_proxy=self.proxy
        )
        self.unitlimitmax = tango_signal_rw(
            float, self.trl + "/UnitLimitMax", device_proxy=self.proxy
        )

        self.set_readable_signals(
            read_uncached=[self.position],
            config=[self.cwlimit, self.ccwlimit, self.unitlimitmin, self.unitlimitmax],
        )

        self._stop = tango_signal_x(self.trl + "/StopMove", self.proxy)
        self._state = tango_signal_r(DevState, self.trl + "/State", self.proxy)

        self.set_name(self.name)

    # --------------------------------------------------------------------
    async def _move(self, new_position: float, watchers: List[Callable] or None = None)\
            -> None:
        if watchers is None:
            watchers = []
        self._set_success = True
        start = time.monotonic()
        start_position = await self.position.get_value()

        def update_watchers(current_position: float) -> None:
            for watcher in watchers:
                watcher(
                    name=self.name,
                    current=current_position,
                    initial=start_position,
                    target=new_position,
                    time_elapsed=time.monotonic() - start,
                )

        if self.position.is_cachable():
            self.position.subscribe_value(update_watchers)
        else:
            update_watchers(start_position)
        try:
            await self.position.set(new_position)
            await asyncio.sleep(0.1)
            counter = 0
            while await self._state.get_value() == DevState.MOVING:
                # Update the watchers with the current position every 0.5 seconds
                if counter % 5 == 0:
                    current_position = await self.position.get_value()
                    update_watchers(current_position)
                    counter = 0
                await asyncio.sleep(0.1)
                counter += 1
        finally:
            if self.position.is_cachable():
                self.position.clear_sub(update_watchers)
            else:
                update_watchers(await self.position.get_value())
        if not self._set_success:
            raise RuntimeError("Motor was stopped")

    # --------------------------------------------------------------------
    def set(self, new_position: float, timeout: Optional[float] = None) -> AsyncStatus:
        watchers: List[Callable] = []
        coro = asyncio.wait_for(self._move(new_position, watchers), timeout=timeout)
        return AsyncStatus(coro, watchers)

    # --------------------------------------------------------------------
    async def locate(self) -> Location:
        set_point = await self.position.get_setpoint()
        readback = await self.position.get_value()
        return Location(setpoint=set_point, readback=readback)

    # --------------------------------------------------------------------
    async def stop(self, success: bool = False) -> None:
        self._set_success = success
        # Put with completion will never complete as we are waiting for completion on
        # the move above, so need to pass wait=False
        await self._stop.trigger()