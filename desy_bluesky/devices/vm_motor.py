from __future__ import annotations

from bluesky.protocols import Stoppable

from ophyd_async.core import (
    AsyncStatus,
    HintedSignal,
)

from ophyd_async.core import (
    SignalX,
    SignalRW,
    DEFAULT_TIMEOUT,
)

from tango import DeviceProxy

from .fsec_readable_device import FSECReadableDevice


class VmMotor(FSECReadableDevice, Stoppable):
    Position: SignalRW[float]
    StopMove: SignalX

    # --------------------------------------------------------------------
    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Position], HintedSignal)
        self._set_success = True

    # --------------------------------------------------------------------

    @AsyncStatus.wrap
    async def set(self, new_position: float, timeout: float = DEFAULT_TIMEOUT):
        await self.Position.set(new_position, wait=True, timeout=timeout)
        self._set_success = True

    # --------------------------------------------------------------------
    @AsyncStatus.wrap
    async def stop(self, success=True) -> None:
        self._set_success = success
        await self.StopMove.trigger(wait=True)
