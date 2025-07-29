#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ports (ポート定義)

Hexagonal Architectureのポート定義。
Primary（入力）とSecondary（出力）のポートを管理。
"""

# Primary Ports
from .primary import (
    PlaybackState, ViewMode, IApplicationController, IVideoViewer,
    EditMode, BrushMode, MorphologyOperation, IMaskEditor
)

# Secondary Ports
from .secondary import (
    IVideoMetadata, IFrame, IVideoReader, IVideoWriter,
    IMaskMetadata, IMaskReader, IMaskWriter, IMaskProcessor,
    IEffect, IEffectEngine, IEffectRenderer, IEffectPreview, IEffectPresetManager,
    IProjectMetadata, IProjectRepository, IProjectSerializer
)

__all__ = [
    # Primary Ports - Application
    "PlaybackState",
    "ViewMode",
    "IApplicationController",
    "IVideoViewer",
    # Primary Ports - Editor
    "EditMode",
    "BrushMode", 
    "MorphologyOperation",
    "IMaskEditor",
    # Secondary Ports - Video
    "IVideoMetadata",
    "IFrame",
    "IVideoReader",
    "IVideoWriter",
    # Secondary Ports - Mask
    "IMaskMetadata",
    "IMaskReader",
    "IMaskWriter",
    "IMaskProcessor",
    # Secondary Ports - Effect
    "IEffect",
    "IEffectEngine",
    "IEffectRenderer",
    "IEffectPreview",
    "IEffectPresetManager",
    # Secondary Ports - Project
    "IProjectMetadata",
    "IProjectRepository",
    "IProjectSerializer",
]