import asyncio
from typing import Optional, Dict, Any

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
    gate: Triggerable and Preparable
    counter: Readable

    def __init__(
        self,
        gate: Triggerable and Preparable,
        counter: Readable,
        delay: Optional[float] = 0,
        name: str = "",
    ) -> None:
        self.gate = gate
        self.counter = counter

        with self.add_children_as_readables(ConfigSignal):
            self.delay = soft_signal_rw(float, delay)
            self.reset = soft_signal_rw(bool, False)

        super().__init__(name=name)


    def prepare(self, value: dict) -> AsyncStatus:
        return AsyncStatus(self._prepare(value))

    async def _prepare(self, value: dict) -> None:
        tasks = []
        configs = self._configurables
        for sig in configs:
            name = sig.signal.name
            name = name.split('-')[-1]
            if name in value:
                tasks.append(sig.signal.set(value[name]))
        try:
            await asyncio.gather(*tasks)
        except Exception as ex:
            print(f"Error in preparing {self.name}: {ex}")
            raise ex

        await self.gate.prepare(await self.delay.get_value())

        is_reset = await self.reset.get_value()
        if is_reset:
            await self.counter.prepare({"reset": True})
            await self.reset.set(False)


    def trigger(self) -> AsyncStatus:
        return AsyncStatus(self._trigger())

    async def _trigger(self):
        gate_status = await self.gate._state.get_value()
        if gate_status == DevState.MOVING:
            return
        await self.gate.trigger()

    async def read(self) -> Dict[str, Reading]:
        counter_reading = await self.counter.read()
        gate_reading = await self.gate.read()
        return counter_reading | gate_reading

    async def describe(self) -> Dict[str, Any]:
        counter_desc = await self.counter.describe()
        return counter_desc
