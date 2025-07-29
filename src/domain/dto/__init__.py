#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Transfer Objects (DTO)

レイヤー間のデータ転送に使用する純粋なデータクラス。
外部ライブラリの型を含まず、プリミティブ型とnumpyのみを使用。
"""

from .frame_dto import FrameDTO
from .mask_dto import MaskDTO
from .video_metadata_dto import VideoMetadataDTO
from .bounding_box_dto import BoundingBoxDTO
from .alert_dto import AlertDTO, AlertLevel, AlertType

__all__ = [
    "FrameDTO",
    "MaskDTO",
    "VideoMetadataDTO",
    "BoundingBoxDTO",
    "AlertDTO",
    "AlertLevel",
    "AlertType",
]