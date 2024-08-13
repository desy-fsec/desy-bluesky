import asyncio
from typing import Union

from ophyd_async.core import (
    Device,
    AsyncStatus,
    StandardReadable,
    soft_signal_rw,
    ConfigSignal,
    HintedSignal,
    SignalRW,
    SignalR,
    SignalX,
)
from bluesky.protocols import (
    Readable,
    Triggerable,
    Preparable,
)


class GatedCounter(StandardReadable, Preparable, Triggerable):
    gate: Union[Device, Triggerable, Preparable]
    counter: Union[Device, Readable]

    counts: SignalR
    reset: SignalX
    sampletime: SignalRW
    remainingtime: SignalRW
    state: SignalR
    reset_on_trigger: SignalRW

    def __init__(
        self,
        gate: Union[Triggerable, Preparable],
        counter: Readable,
        name: str = "",
    ) -> None:
        self.gate = gate
        self.counter = counter

        with self.add_children_as_readables(HintedSignal):
            self.counts = self.counter.counts

        with self.add_children_as_readables(ConfigSignal):
            self.sampletime = self.gate.sampletime
            self.reset_on_trigger = soft_signal_rw(bool, initial_value=True)

        self.add_readables([self.sampletime], HintedSignal)
        self.add_readables(self.gate, self.counter)

        self.state = self.gate._state

        super().__init__(name=name)

    def prepare(self, **kwargs) -> AsyncStatus:
        return AsyncStatus(self._prepare(kwargs))

    async def _prepare(self, kwargs) -> None:
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

    async def _trigger(self):
        reset_on_trigger = await self.reset_on_trigger.get_value()
        if reset_on_trigger:
            status = self.counter.trigger()
            await status
