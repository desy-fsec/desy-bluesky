from typing import Union

from ophyd_async.core import (
    StandardReadable,
    AsyncStatus,
    soft_signal_rw,
    ConfigSignal,
)

from bluesky.protocols import (
    Triggerable,
)

from .dgg2 import DGG2Timer
from .sis3820 import SIS3820Counter


class GatedCounter(StandardReadable, Triggerable):
    gate: DGG2Timer
    counter: SIS3820Counter

    def __init__(self,
                 gate: Union[DGG2Timer, str],
                 counter: Union[SIS3820Counter, str],
                 name: str = "") -> None:

        with self.add_children_as_readables():
            if isinstance(counter, SIS3820Counter):
                self.counter = counter
            elif isinstance(counter, str):
                self.counter = SIS3820Counter(counter)
            else:
                raise ValueError("counter must be a SIS3820Counter or a string")

            if isinstance(gate, str):
                self.gate = DGG2Timer(gate)
            elif isinstance(gate, DGG2Timer):
                self.gate = gate
            else:
                raise ValueError("gate must be a DGG2Timer or a string")

        self.reset_on_trigger = soft_signal_rw(datatype=bool,
                                               name="reset_on_trigger",
                                               initial_value=True)
        self.add_readables([self.gate.SampleTime, self.reset_on_trigger], ConfigSignal)

        super().__init__(name=name)

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        if await self.reset_on_trigger.get_value():
            await self.counter.Reset.trigger()

        trigger_status = self.gate.trigger()
        await trigger_status
