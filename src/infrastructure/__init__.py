#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infrastructure (インフラストラクチャ層)

DIコンテナ、設定管理、共通ユーティリティなど、
アプリケーション全体を支える基盤機能を提供。
"""

from .di_container import (
    DIContainer, Lifetime, ServiceDescriptor,
    get_container, set_container
)
from .container_config import ContainerConfigurator, create_default_container
from .factories import (
    VideoReaderFactory, VideoWriterFactory,
    MaskProcessorFactory, ProjectRepositoryFactory,
    InputDataSourceFactory
)

__all__ = [
    # DI Container
    "DIContainer",
    "Lifetime",
    "ServiceDescriptor",
    "get_container",
    "set_container",
    # Configuration
    "ContainerConfigurator",
    "create_default_container",
    # Factories
    "VideoReaderFactory",
    "VideoWriterFactory",
    "MaskProcessorFactory",
    "ProjectRepositoryFactory",
    "InputDataSourceFactory",
]