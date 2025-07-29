#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Value Objects (VO)

不変で検証付きの値オブジェクト。
ビジネスルールに基づく制約を持つ値を表現。
"""

from .timecode import Timecode
from .color_space import ColorSpace, ColorPrimaries, TransferCharacteristics, MatrixCoefficients
from .resolution import Resolution, AspectRatioType
from .frame_rate import FrameRate, FrameRateType

__all__ = [
    "Timecode",
    "ColorSpace",
    "ColorPrimaries",
    "TransferCharacteristics",
    "MatrixCoefficients",
    "Resolution",
    "AspectRatioType",
    "FrameRate",
    "FrameRateType",
]