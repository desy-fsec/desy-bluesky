import asyncio
from typing import Optional, Dict, Any, Union

from ophyd_async.core import AsyncStatus, StandardReadable, soft_signal_rw, ConfigSignal, HintedSignal
from bluesky.protocols import (
    Readable,
    Reading,
    Triggerable,
    Preparable,
)
from tango import DevState


class GatedCounter(StandardReadable, Preparable, Triggerable):
    # gate must be triggerable and preparable
    gate: Union[Triggerable, Preparable]
    counter: Readable

    def __init__(
        self,
        gate: Union[Triggerable, Preparable],
        counter: Readable,
        name: str = "",
    ) -> None:
        self.gate = gate
        self.counter = counter

        with self.add_children_as_readables(ConfigSignal):
            self.sampletime = self.gate.sampletime
        
        with self.add_children_as_readables(HintedSignal):
            self.counts = self.counter.counts
            
        self.add_readables([self.sampletime], HintedSignal)
        
        self.reset = self.counter.reset

        super().__init__(name=name)

    def prepare(self, **kwargs) -> AsyncStatus:
        return AsyncStatus(self._prepare(kwargs))

    async def _prepare(self, kwargs) -> None:
        tasks = []
        tasks.append(self.gate.prepare(**kwargs))
        tasks.append(self.counter.prepare(**kwargs))
        await asyncio.gather(*tasks)

    def trigger(self) -> AsyncStatus:
        return AsyncStatus(self._trigger())

    async def _trigger(self):
        gate_status = await self.gate._state.get_value()
        if gate_status == DevState.MOVING:
            return
        await self.gate.trigger()
