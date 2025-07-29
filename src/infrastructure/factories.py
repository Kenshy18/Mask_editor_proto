#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ファクトリークラス

各コンポーネントのファクトリー実装。
設定に基づいて適切な実装を生成。
"""
from typing import Dict, Type, Optional, Any, Protocol
from pathlib import Path

from domain.ports.secondary import (
    IVideoReader, IVideoWriter, IMaskReader, IMaskWriter,
    IMaskProcessor, IProjectRepository, IInputDataSource
)
from adapters.secondary import (
    PyAVVideoReaderAdapter, PyAVVideoWriterAdapter,
    OpenCVMaskProcessorAdapter, JsonProjectRepositoryAdapter,
    LocalFileInputAdapter
)


class VideoReaderFactory:
    """ビデオリーダーファクトリー"""
    
    _implementations: Dict[str, Type[IVideoReader]] = {
        "pyav": PyAVVideoReaderAdapter,
    }
    
    @classmethod
    def register(cls, name: str, implementation: Type[IVideoReader]) -> None:
        """実装を登録"""
        cls._implementations[name] = implementation
    
    @classmethod
    def create(cls, backend: str = "pyav", **options) -> IVideoReader:
        """
        ビデオリーダーを作成
        
        Args:
            backend: バックエンド名
            **options: 追加オプション
            
        Returns:
            IVideoReader実装
        """
        if backend not in cls._implementations:
            available = ", ".join(cls._implementations.keys())
            raise ValueError(f"Unknown backend: {backend}. Available: {available}")
        
        implementation = cls._implementations[backend]
        return implementation()
    
    @classmethod
    def get_available_backends(cls) -> list[str]:
        """利用可能なバックエンドのリストを取得"""
        return list(cls._implementations.keys())


class VideoWriterFactory:
    """ビデオライターファクトリー"""
    
    _implementations: Dict[str, Type[IVideoWriter]] = {
        "pyav": PyAVVideoWriterAdapter,
    }
    
    @classmethod
    def register(cls, name: str, implementation: Type[IVideoWriter]) -> None:
        """実装を登録"""
        cls._implementations[name] = implementation
    
    @classmethod
    def create(cls, backend: str = "pyav", **options) -> IVideoWriter:
        """
        ビデオライターを作成
        
        Args:
            backend: バックエンド名
            **options: 追加オプション
            
        Returns:
            IVideoWriter実装
        """
        if backend not in cls._implementations:
            available = ", ".join(cls._implementations.keys())
            raise ValueError(f"Unknown backend: {backend}. Available: {available}")
        
        implementation = cls._implementations[backend]
        return implementation()
    
    @classmethod
    def get_available_backends(cls) -> list[str]:
        """利用可能なバックエンドのリストを取得"""
        return list(cls._implementations.keys())


class MaskProcessorFactory:
    """マスクプロセッサファクトリー"""
    
    _implementations: Dict[str, Type[IMaskProcessor]] = {
        "opencv": OpenCVMaskProcessorAdapter,
    }
    
    @classmethod
    def register(cls, name: str, implementation: Type[IMaskProcessor]) -> None:
        """実装を登録"""
        cls._implementations[name] = implementation
    
    @classmethod
    def create(cls, backend: str = "opencv", **options) -> IMaskProcessor:
        """
        マスクプロセッサを作成
        
        Args:
            backend: バックエンド名
            **options: 追加オプション
            
        Returns:
            IMaskProcessor実装
        """
        if backend not in cls._implementations:
            available = ", ".join(cls._implementations.keys())
            raise ValueError(f"Unknown backend: {backend}. Available: {available}")
        
        implementation = cls._implementations[backend]
        return implementation()
    
    @classmethod
    def get_available_backends(cls) -> list[str]:
        """利用可能なバックエンドのリストを取得"""
        return list(cls._implementations.keys())


class ProjectRepositoryFactory:
    """プロジェクトリポジトリファクトリー"""
    
    _implementations: Dict[str, Type[IProjectRepository]] = {
        "json": JsonProjectRepositoryAdapter,
    }
    
    @classmethod
    def register(cls, name: str, implementation: Type[IProjectRepository]) -> None:
        """実装を登録"""
        cls._implementations[name] = implementation
    
    @classmethod
    def create(
        cls,
        backend: str = "json",
        config_dir: Optional[Path] = None,
        **options
    ) -> IProjectRepository:
        """
        プロジェクトリポジトリを作成
        
        Args:
            backend: バックエンド名
            config_dir: 設定ディレクトリ
            **options: 追加オプション
            
        Returns:
            IProjectRepository実装
        """
        if backend not in cls._implementations:
            available = ", ".join(cls._implementations.keys())
            raise ValueError(f"Unknown backend: {backend}. Available: {available}")
        
        implementation = cls._implementations[backend]
        
        if backend == "json":
            return implementation(config_dir)
        else:
            return implementation()
    
    @classmethod
    def get_available_backends(cls) -> list[str]:
        """利用可能なバックエンドのリストを取得"""
        return list(cls._implementations.keys())


class InputDataSourceFactory:
    """入力データソースファクトリー"""
    
    _implementations: Dict[str, Type[IInputDataSource]] = {
        "local_file": LocalFileInputAdapter,
    }
    
    @classmethod
    def register(cls, name: str, implementation: Type[IInputDataSource]) -> None:
        """実装を登録"""
        cls._implementations[name] = implementation
    
    @classmethod
    def create(cls, backend: str = "local_file", **options) -> IInputDataSource:
        """
        入力データソースを作成
        
        Args:
            backend: バックエンド名
            **options: 追加オプション
            
        Returns:
            IInputDataSource実装
        """
        if backend not in cls._implementations:
            available = ", ".join(cls._implementations.keys())
            raise ValueError(f"Unknown backend: {backend}. Available: {available}")
        
        implementation = cls._implementations[backend]
        instance = implementation()
        
        # 設定がある場合は初期化
        if options:
            instance.initialize(options)
        
        return instance
    
    @classmethod
    def get_available_backends(cls) -> list[str]:
        """利用可能なバックエンドのリストを取得"""
        return list(cls._implementations.keys())


# C++実装の自動登録（利用可能な場合）
def register_cpp_implementations() -> None:
    """C++実装を登録（利用可能な場合）"""
    try:
        # ビデオ
        from adapters.secondary.cpp_video_reader import CppVideoReaderAdapter
        from adapters.secondary.cpp_video_writer import CppVideoWriterAdapter
        VideoReaderFactory.register("cpp", CppVideoReaderAdapter)
        VideoWriterFactory.register("cpp", CppVideoWriterAdapter)
    except ImportError:
        pass
    
    try:
        # マスク処理
        from adapters.secondary.cpp_mask_processor import CppMaskProcessorAdapter
        MaskProcessorFactory.register("cpp", CppMaskProcessorAdapter)
    except ImportError:
        pass


# モジュール読み込み時にC++実装を登録
register_cpp_implementations()