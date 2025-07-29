#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ドメイン層

ビジネスロジックとドメインモデルを定義する層。
外部ライブラリへの依存を持たず、純粋なビジネスルールを表現する。
"""

# DTO
from .dto import (
    FrameDTO, MaskDTO, VideoMetadataDTO, BoundingBoxDTO,
    AlertDTO, AlertLevel, AlertType
)

# Value Objects
from .vo import (
    Timecode, ColorSpace, ColorPrimaries, TransferCharacteristics,
    MatrixCoefficients, Resolution, AspectRatioType, FrameRate, FrameRateType
)

# Ports
from .ports import (
    # Primary Ports
    PlaybackState, ViewMode, IApplicationController, IVideoViewer,
    EditMode, BrushMode, MorphologyOperation, IMaskEditor,
    # Secondary Ports
    IVideoMetadata, IFrame, IVideoReader, IVideoWriter,
    IMaskMetadata, IMaskReader, IMaskWriter, IMaskProcessor,
    IEffect, IEffectEngine, IEffectRenderer, IEffectPreview, IEffectPresetManager,
    IProjectMetadata, IProjectRepository, IProjectSerializer
)

__all__ = [
    # DTO
    "FrameDTO",
    "MaskDTO",
    "VideoMetadataDTO",
    "BoundingBoxDTO",
    "AlertDTO",
    "AlertLevel",
    "AlertType",
    # Value Objects
    "Timecode",
    "ColorSpace",
    "ColorPrimaries",
    "TransferCharacteristics",
    "MatrixCoefficients",
    "Resolution",
    "AspectRatioType",
    "FrameRate",
    "FrameRateType",
    # Primary Ports
    "PlaybackState",
    "ViewMode",
    "IApplicationController",
    "IVideoViewer",
    "EditMode",
    "BrushMode",
    "MorphologyOperation",
    "IMaskEditor",
    # Secondary Ports
    "IVideoMetadata",
    "IFrame",
    "IVideoReader",
    "IVideoWriter",
    "IMaskMetadata",
    "IMaskReader",
    "IMaskWriter",
    "IMaskProcessor",
    "IEffect",
    "IEffectEngine",
    "IEffectRenderer",
    "IEffectPreview",
    "IEffectPresetManager",
    "IProjectMetadata",
    "IProjectRepository",
    "IProjectSerializer",
]