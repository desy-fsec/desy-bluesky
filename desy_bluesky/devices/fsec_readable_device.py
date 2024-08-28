from __future__ import annotations

import asyncio
from typing import Optional, Union, TypeVar
from dataclasses import field, make_dataclass

from bluesky.protocols import Reading

from ophyd_async.core import (
    AsyncStatus,
)
from ophyd_async.core import (
    SignalR,
    HintedSignal,
    ConfigSignal
)
from ophyd_async.tango import (
    TangoReadable,
    tango_polling
)
from tango import DevState

FSECDeviceConfig = TypeVar("FSECDeviceConfig")


@tango_polling(0.1, 0.1, 0.1)
class FSECReadableDevice(TangoReadable):
    State: SignalR

    def wait_for_idle(self):
        return AsyncStatus(self._wait_for_idle())

    async def _wait_for_idle(self):
        event = asyncio.Event()

        def _wait(value: dict[str, Reading]):
            if value[self.State.name]["value"] == DevState.ON:
                event.set()

        self.State.subscribe(_wait)
        await event.wait()

    @AsyncStatus.wrap
    async def prepare(self, value: FSECDeviceConfig) -> None:
        config = value.__dataclass_fields__
        tasks = []
        for key in config:
            v = getattr(value, key)
            if v is not None:
                if hasattr(self, key):
                    tasks.append(getattr(self, key).set(v))
        await asyncio.gather(*tasks)

    def get_config(self):
        attrs = []
        for sig in self._configurables:
            if isinstance(sig, Union[HintedSignal, ConfigSignal]):
                sig = sig.signal
            attrs.append((sig.name.split("-")[-1],
                          Optional[sig._backend.datatype],
                          field(default=None)))
        config_dataclass = make_dataclass("FSECDeviceConfig", attrs)
        return config_dataclass()
