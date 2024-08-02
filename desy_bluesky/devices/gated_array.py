import asyncio
from typing import Optional, Union
from dataclasses import dataclass

from ophyd_async.core import (
    AsyncStatus,
    Device,
    StandardReadable,
    soft_signal_rw,
    ConfigSignal,
    HintedSignal,
    SignalRW,
    SignalR,
)

from bluesky.protocols import (
    Readable,
    Triggerable,
    Preparable,
)

@dataclass
class GatedArrayConfig:
    sampletime: Optional[float] = None
    reset_on_trigger: Optional[bool] = None

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

    # --------------------------------------------------------------------
    def prepare(self, value: GatedArrayConfig) -> AsyncStatus:
        return AsyncStatus(self._prepare(value))
    
    # --------------------------------------------------------------------
    async def _prepare(self, value: GatedArrayConfig) -> None:
        config = value.__dataclass_fields__
        for key, v in config.items():
            if v is not None:
                if hasattr(self, key):
                    await getattr(self, key).set(v)
    
    # --------------------------------------------------------------------
    def trigger(self) -> AsyncStatus:
        return AsyncStatus(self._trigger())
    
    # --------------------------------------------------------------------
    async def _trigger(self) -> None:
        tasks = []
        for counter in self._counters:
            tasks.append(counter.reset.trigger())
        await asyncio.gather(*tasks)

        trigger_status = self._gate.trigger()
        await trigger_status
    
    def get_dataclass() -> GatedArrayConfig:
        return GatedArrayConfig()
