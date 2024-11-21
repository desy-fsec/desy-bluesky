from __future__ import annotations

from bluesky.protocols import Triggerable, Preparable

from ophyd_async.core import (
    AsyncStatus,
)
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    SignalX,
    SignalR,
    SignalRW,
    HintedSignal,
    ConfigSignal,
    wait_for_value,
    StandardReadableFormat as Format,
)
from tango import DeviceProxy, DevState

from .fsec_readable_device import FSECReadableDevice


class DGG2Timer(FSECReadableDevice, Triggerable):
    SampleTime: SignalRW[float]
    Start: SignalX

    # --------------------------------------------------------------------
    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self._set_success = True
        self.add_readables([self.SampleTime], Format.HINTED_SIGNAL)

    # --------------------------------------------------------------------

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        sample_time = await self.SampleTime.get_value()
        timeout = sample_time + DEFAULT_TIMEOUT
        await self.Start.trigger(wait=False, timeout=timeout)
        await AsyncStatus(wait_for_value(self.State, DevState.ON, timeout=timeout))
