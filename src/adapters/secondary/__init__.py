#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secondary Adapters (出力アダプター)

外部リソースへのアクセスを実装するアダプター。
Secondary Portの実装を提供。
"""

from .pyav_video_reader import PyAVVideoReaderAdapter
from .pyav_video_writer import PyAVVideoWriterAdapter
from .opencv_mask_processor import OpenCVMaskProcessorAdapter
from .json_project_repository import JsonProjectRepositoryAdapter
from .local_file_input_adapter import LocalFileInputAdapter

__all__ = [
    "PyAVVideoReaderAdapter",
    "PyAVVideoWriterAdapter",
    "OpenCVMaskProcessorAdapter",
    "JsonProjectRepositoryAdapter",
    "LocalFileInputAdapter",
]