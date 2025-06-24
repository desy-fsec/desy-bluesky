from __future__ import annotations

from ophyd_async.core import (
    SignalX,
    SignalRW,
    SignalR,
    Array1D
)

from .fsec_readable_device import FSECReadableDevice

class Dante(FSECReadableDevice):
    ConfigFilePath: SignalRW[str]
    Counts00: SignalR[Array1D[int]]
    Counts01: SignalR[Array1D[int]]
    Counts02: SignalR[Array1D[int]]
    Counts03: SignalR[Array1D[int]]
    Data00: SignalR[Array1D[int]]
    Data01: SignalR[Array1D[int]]
    Data02: SignalR[Array1D[int]]
    Data03: SignalR[Array1D[int]]
    FileDir: SignalRW[str]
    FilePrefix: SignalRW[str]
    FileStartNum: SignalRW[int]
    FrameCounter: SignalR[int]
    FramesPerFile: SignalRW[int]
    GatingMode: SignalRW[int]
    ICR00: SignalR[int]
    ICR01: SignalR[int]
    ICR02: SignalR[int]
    ICR03: SignalR[int]
    Init: SignalX
    NbFrames: SignalRW[int]
    OCR00: SignalR[int]
    OCR01: SignalR[int]
    OCR02: SignalR[int]
    OCR03: SignalR[int]
    ROIs00: SignalR[Array1D[int]]
    ROIs01: SignalR[Array1D[int]]
    ROIs02: SignalR[Array1D[int]]
    ROIs03: SignalR[Array1D[int]]
    SaveData: SignalRW[bool]
    StartAcq: SignalX
    Status: SignalR[str]
    StopAcq: SignalX
    TimePerPoint: SignalRW[int]