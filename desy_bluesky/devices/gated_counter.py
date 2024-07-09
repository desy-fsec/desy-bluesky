import asyncio
import time
from typing import Callable, List, Optional, Dict, Any

from ophyd_async.core import AsyncStatus, StandardReadable
from bluesky.protocols import (
    Readable,
    Reading,
    Triggerable,
    Preparable,
)
from tango import DevState


class GatedCounter(StandardReadable, Preparable, Triggerable):
    # gate must be triggerable and preparable
    gate: Triggerable and Preparable
    counter: Readable

    def __init__(self,
                 gate: Triggerable and Preparable,
                 counter: Readable,
                 delay: Optional[float] = None,
                 name: str = "") -> None:
        super().__init__(name=name)
        self.gate = gate
        self.counter = counter
        self.delay = delay

    def prepare(self, value: float) -> AsyncStatus:
        self.delay = value
        return AsyncStatus(self._prepare(value))

    async def _prepare(self, value: float) -> None:
        await self.gate.prepare(value)

    def trigger(self) -> AsyncStatus:
        self.prepare(self.delay)
        if self.counter is Triggerable:
            self.counter.trigger()
        gate_state = self.gate.state.get_value()
        if gate_state == DevState.MOVING:
            return AsyncStatus(asyncio.sleep(0))
        status = self.gate.trigger()
        return status

    async def read(self) -> Dict[str, Reading]:
        return await self.counter.read()

    async def describe(self) -> Dict[str, Any]:
        counter_desc = await self.counter.describe()
        return counter_desc