#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secondary Ports (出力ポート)

外部リソースへのアクセスを定義するインターフェース。
データベース、ファイルシステム、外部APIなどへのアクセスポート。
"""

from .video_ports import IVideoMetadata, IFrame, IVideoReader, IVideoWriter
from .mask_ports import IMaskMetadata, IMaskReader, IMaskWriter, IMaskProcessor
from .effect_ports import IEffect, IEffectEngine, IEffectRenderer, IEffectPreview, IEffectPresetManager
from .project_ports import IProjectMetadata, IProjectRepository, IProjectSerializer
from .input_data_ports import IInputDataSource

__all__ = [
    # Video
    "IVideoMetadata",
    "IFrame", 
    "IVideoReader",
    "IVideoWriter",
    # Mask
    "IMaskMetadata",
    "IMaskReader",
    "IMaskWriter",
    "IMaskProcessor",
    # Effect
    "IEffect",
    "IEffectEngine",
    "IEffectRenderer",
    "IEffectPreview",
    "IEffectPresetManager",
    # Project
    "IProjectMetadata",
    "IProjectRepository",
    "IProjectSerializer",
    # Input Data
    "IInputDataSource",
]