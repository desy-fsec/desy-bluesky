from __future__ import annotations

from typing import Annotated as A

from bluesky.protocols import Stoppable, SyncOrAsync

from ophyd_async.core import (
    AsyncStatus,
    StandardReadableFormat as Format,
    SignalX,
    SignalRW,
    DEFAULT_TIMEOUT,
)

from .fsec_readable_device import FSECReadableDevice


class VmMotor(FSECReadableDevice, Stoppable):
    Position: A[SignalRW[float], Format.HINTED_UNCACHED_SIGNAL]
    StopMove: SignalX
    

    @AsyncStatus.wrap
    async def set(self, new_position: float, timeout: float = DEFAULT_TIMEOUT):
        await self.Position.set(new_position, wait=True, timeout=timeout)

    def stop(self, success=True) -> SyncOrAsync:
        self._set_success = success
        return self.StopMove.trigger(wait=True)
