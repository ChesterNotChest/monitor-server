"""Shared lightweight data types for vision modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Track:
    """ByteTrack tracking result."""

    bbox: list[float]
    track_id: int
    score: float
