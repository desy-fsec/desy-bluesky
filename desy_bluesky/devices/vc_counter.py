from __future__ import annotations

from typing import Dict

from bluesky.protocols import Triggerable, Reading, Preparable

from ophyd_async.core import (
    AsyncStatus,
    HintedSignal,
)

from ophyd_async.tango import (
    TangoReadableDevice,
    tango_signal_rw,
    tango_signal_x,
)


class VcCounter(TangoReadableDevice, Preparable):
    # --------------------------------------------------------------------
    def __init__(self, trl: str, name="", sources: dict = None) -> None:
        if sources is None:
            sources = {}
        self.trl = trl
        self.src_dict["counts"] = sources.get("counts", "/Counts")
        self.src_dict["reset"] = sources.get("reset", "/Reset")

        for key in self.src_dict:
            if not self.src_dict[key].startswith("/"):
                self.src_dict[key] = "/" + self.src_dict[key]

        with self.add_children_as_readables(HintedSignal):
            self.counts = tango_signal_rw(
                float, trl + self.src_dict["counts"], device_proxy=self.proxy
            )
        self.reset = tango_signal_x(
            self.trl + self.src_dict["reset"], device_proxy=self.proxy
        )

        TangoReadableDevice.__init__(self, trl, name)
        self._set_success = True

    # --------------------------------------------------------------------
    async def read(self) -> Dict[str, Reading]:
        ret = await super().read()
        return ret

    # --------------------------------------------------------------------
    def prepare(self, **kwargs) -> AsyncStatus:
        return AsyncStatus(self._reset())

    # --------------------------------------------------------------------

    async def _reset(self) -> None:
        await self.reset.trigger()
