from __future__ import annotations

from typing import Dict

from bluesky.protocols import Reading, Triggerable, Preparable

from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
    StandardReadable,
    SignalR,
    SignalRW,
    SignalX,
)
from ophyd_async.tango import tango_signal_rw, tango_signal_x, tango_signal_r
from tango.asyncio import DeviceProxy


# --------------------------------------------------------------------
class SIS3820Counter(StandardReadable):
    counts: SignalR
    offset: SignalRW
    reset: SignalX

    def __init__(self, trl: str, name: str = "", sources: dict = None) -> None:
        if sources is None:
            sources = {}
        self.proxy = None
        self.trl = trl
        self.src_dict = {
            "counts": sources.get("counts", "/Counts"),
            "offset": sources.get("offset", "/Offset"),
            "reset": sources.get("reset", "/Reset"),
        }

        for key in self.src_dict:
            if not self.src_dict[key].startswith("/"):
                self.src_dict[key] = "/" + self.src_dict[key]

        with self.add_children_as_readables(HintedSignal):
            self.counts = tango_signal_r(
                float, trl + self.src_dict["counts"], device_proxy=self.proxy
            )
        with self.add_children_as_readables(ConfigSignal):
            self.offset = tango_signal_rw(
                float, trl + self.src_dict["offset"], device_proxy=self.proxy
            )

        self.reset = tango_signal_x(
            trl + self.src_dict["reset"], device_proxy=self.proxy
        )

        StandardReadable.__init__(self, name=name)
        self._set_success = True

    async def _reset(self):
        await self.reset.trigger()
