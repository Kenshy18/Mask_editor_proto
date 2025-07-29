#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapters (アダプター層)

Hexagonal ArchitectureのAdapter実装。
ポートの具象実装を提供し、外部ライブラリとの接続を行う。
"""

# Secondary Adapters
from .secondary import (
    PyAVVideoReaderAdapter,
    PyAVVideoWriterAdapter,
    OpenCVMaskProcessorAdapter,
    JsonProjectRepositoryAdapter,
)

__all__ = [
    # Secondary Adapters
    "PyAVVideoReaderAdapter",
    "PyAVVideoWriterAdapter",
    "OpenCVMaskProcessorAdapter",
    "JsonProjectRepositoryAdapter",
]