from typing import Dict
import numpy.typing as npt

from ophyd_async.core import AsyncStatus, HintedSignal, ConfigSignal
from bluesky.protocols import (
    Reading,
    Triggerable,
    Configurable,
)
from ophyd_async.tango import (
    TangoReadableDevice,
    tango_signal_r,
    tango_signal_rw,
    tango_signal_x,
)
from tango import DevState


class MCA8715(TangoReadableDevice, Triggerable, Configurable):
    """
    A device that controls a MCA8715 Multi-Channel Analyzer.
    """

    src_dict: dict = {}
    name: str
    trl: str

    def __init__(self, trl: str, name: str = "", sources: dict = None) -> None:
        if sources is None:
            sources = {}
        self.trl = trl
        self.src_dict["datalength"] = sources.get("DataLength", "/DataLength")
        self.src_dict["data"] = sources.get("Data", "/Data")
        self.src_dict["state"] = sources.get("State", "/State")
        self.src_dict["counts"] = sources.get("Start", "/Counts")
        self.src_dict["countsdiff"] = sources.get("CountsDiff", "/CountsDiff")
        self.src_dict["clear"] = sources.get("Clear", "/Clear")

        for key in self.src_dict:
            if not self.src_dict[key].startswith("/"):
                self.src_dict[key] = "/" + self.src_dict[key]

        with self.add_children_as_readables(HintedSignal):
            self.data = tango_signal_r(
                npt.NDArray[int], trl + self.src_dict["data"], device_proxy=self.proxy
            )
            self.counts = tango_signal_r(
                npt.NDArray[float],
                trl + self.src_dict["counts"],
                device_proxy=self.proxy,
            )
            self.countsdiff = tango_signal_r(
                npt.NDArray[float],
                trl + self.src_dict["countsdiff"],
                device_proxy=self.proxy,
            )

        with self.add_children_as_readables(ConfigSignal):
            self.datalength = tango_signal_rw(
                int, trl + self.src_dict["datalength"], device_proxy=self.proxy
            )

        self._state = tango_signal_r(
            DevState, trl + self.src_dict["state"], device_proxy=self.proxy
        )

        self.clear = tango_signal_x(
            trl + self.src_dict["clear"], device_proxy=self.proxy
        )

        TangoReadableDevice.__init__(self, trl, name)
        self._set_success = True

    async def read(self) -> Dict[str, Reading]:
        ret = await super().read()
        return ret

    def configure(self, value: float) -> AsyncStatus:
        return AsyncStatus(self._configure(value))

    async def _configure(self, value: float) -> None:
        value = int(value)
        try:
            await self.datalength.set(value)
        except Exception as e:
            raise RuntimeError(f"Error configuring {self.name}: {e}")

    def trigger(self) -> AsyncStatus:
        return AsyncStatus(self._clear())

    async def _clear(self) -> None:
        try:
            await self.clear.trigger()
        except Exception as e:
            raise RuntimeError(f"Error triggering {self.name}: {e}")
