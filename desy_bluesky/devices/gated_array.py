import asyncio
from typing import Optional, Dict, Any, Union

from ophyd_async.core import (
    AsyncStatus,
    Device,
    StandardReadable,
    soft_signal_rw,
    ConfigSignal,
    HintedSignal,
    SignalRW,
    SignalR,
    SignalX,
)
from ophyd_async.core.utils import merge_gathered_dicts
from bluesky.protocols import (
    Readable,
    Reading,
    Triggerable,
    Preparable,
)
from tango import DevState


class GatedArray(StandardReadable, Triggerable, Preparable):
    sampletime: SignalRW
    reset_on_trigger: SignalRW
    state: SignalR
    _gate: Union[Device, Triggerable, Preparable]
    _counters: list[Device, Readable]

    def __init__(self,
                 gate: Union[Device, Triggerable, Preparable],
                 counters: list[Device, Readable],
                 name: str = "") -> None:
        self._gate = gate
        self._counters = counters

        with self.add_children_as_readables(ConfigSignal):
            self.sampletime = self._gate.sampletime
            self.reset_on_trigger = soft_signal_rw(bool, initial_value=True)

        self.add_readables([self.sampletime], HintedSignal)
        self.add_readables([counter for counter in self._counters])
        self.add_readables([self._gate])
        self.state = self._gate._state

        super().__init__(name=name)

    def prepare(self, **kwargs) -> AsyncStatus:
        return AsyncStatus(self._prepare(kwargs))

    async def _prepare(self, kwargs: Dict[str, Any]) -> None:
        tasks = []

        sampletime = kwargs.get("sampletime", None)
        if sampletime is not None:
            tasks.append(self.sampletime.set(float(sampletime)))

        reset_on_trigger = kwargs.get("reset_on_trigger", None)
        if isinstance(reset_on_trigger, bool):
            tasks.append(self.reset_on_trigger.set(reset_on_trigger))

        await asyncio.gather(*tasks)

    def trigger(self) -> AsyncStatus:
        return AsyncStatus(self._trigger())

    async def _trigger(self) -> None:
        tasks = []
        for counter in self._counters:
            tasks.append(counter.reset.trigger())
        await asyncio.gather(*tasks)

        trigger_status = self._gate.trigger()
        await trigger_status

