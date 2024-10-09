import asyncio
from typing import List, Union

from ophyd_async.core import (
    StandardReadable,
    AsyncStatus,
    soft_signal_rw,
    ConfigSignal,
    DeviceVector
)

from bluesky.protocols import (
    Triggerable,
)

from .dgg2 import DGG2Timer
from .sis3820 import SIS3820Counter


class GatedArray(StandardReadable, Triggerable):

    def __init__(self,
                 gate: DGG2Timer | str,
                 counters: List[SIS3820Counter | str],
                 name: str = "") -> None:

        with self.add_children_as_readables():
            if all(isinstance(counter, SIS3820Counter) for counter in counters):
                self.counters = DeviceVector(
                    {i: counter for i, counter in enumerate(counters)}
                )
            elif all(isinstance(counter, str) for counter in counters):
                self.counters = DeviceVector(
                    {i: SIS3820Counter(trl) for i, trl in enumerate(counters)}
                )
            else:
                raise ValueError("counters must be a list of SIS3820Counter or"
                                 " a list of TRLs.")

            if isinstance(gate, str):
                self.gate = DGG2Timer(gate)
            elif isinstance(gate, DGG2Timer):
                self.gate = gate

        self.reset_on_trigger = soft_signal_rw(datatype=bool,
                                               name="reset_on_trigger",
                                               initial_value=True)
        self.add_readables([self.gate.SampleTime, self.reset_on_trigger], ConfigSignal)

        super().__init__(name=name)

    # --------------------------------------------------------------------
    
    @AsyncStatus.wrap
    async def trigger(self) -> None:
        tasks = []
        for counter in self.counters.values():
            if self.reset_on_trigger:
                tasks.append(counter.Reset.trigger())
        await asyncio.gather(*tasks)

        trigger_status = self.gate.trigger()
        await trigger_status
