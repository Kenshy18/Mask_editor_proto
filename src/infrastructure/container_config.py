#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIコンテナ設定

アプリケーションの依存性を設定ファイルに基づいて構成。
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import os
import logging

# YAMLはオプショナル
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)

from .di_container import DIContainer, Lifetime
from domain.ports.secondary.video_ports import IVideoReader, IVideoWriter
from domain.ports.secondary.mask_ports import IMaskProcessor
from domain.ports.secondary.project_ports import IProjectRepository
from domain.ports.secondary.input_data_ports import IInputDataSource
from domain.ports.secondary.project_ports import IProjectAutoSaver, IProjectSerializer
from domain.ports.secondary.effect_ports import (
    IEffect, IEffectEngine, IEffectRenderer, IEffectPreview, IEffectPresetManager
)
from domain.ports.secondary.brush_ports import (
    IBrushEngine, IBrushPreview, IBrushHistory, IBrushOptimizer
)
from domain.ports.secondary.cache_ports import IMaskCache
from domain.ports.secondary.performance_ports import IFrameThrottleService, IUIUpdateOptimizer
from adapters.secondary.pyav_video_reader import PyAVVideoReaderAdapter
from adapters.secondary.pyav_video_writer import PyAVVideoWriterAdapter
from adapters.secondary.opencv_mask_processor import OpenCVMaskProcessorAdapter
from adapters.secondary.json_project_repository import JsonProjectRepositoryAdapter
from adapters.secondary.local_file_input_adapter import LocalFileInputAdapter
from adapters.secondary.input_data_source_decorator import CachedInputDataSourceDecorator
from adapters.secondary.json_project_repository import JsonProjectSerializer
from adapters.secondary.project_auto_saver import ProjectAutoSaverAdapter
from adapters.secondary.effect_engine import EffectEngine
from adapters.secondary.effect_renderer import EffectRenderer
from adapters.secondary.effect_preview import EffectPreview
from adapters.secondary.effect_preset_manager import EffectPresetManager
from adapters.secondary.opencv_brush_engine import OpenCVBrushEngine, OpenCVBrushOptimizer
from adapters.secondary.brush_preview import BrushPreviewAdapter
from adapters.secondary.brush_history import BrushHistoryAdapter
from infrastructure.services.mask_cache_service import MaskCacheService
from infrastructure.services.frame_update_throttle_service import FrameUpdateThrottleService, UIUpdateOptimizer


class ContainerConfigurator:
    """
    DIコンテナ設定クラス
    
    設定ファイルやデフォルト設定に基づいてDIコンテナを構成。
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """設定を読み込む"""
        # デフォルト設定
        self.config = self._get_default_config()
        
        # 設定ファイルがあれば読み込む
        if self.config_path and self.config_path.exists():
            if self.config_path.suffix == '.yaml' or self.config_path.suffix == '.yml':
                if HAS_YAML:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        file_config = yaml.safe_load(f)
                else:
                    # YAMLが利用できない場合はスキップ
                    logger.warning(f"YAML support not available. Skipping {self.config_path}")
                    return
            elif self.config_path.suffix == '.json':
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {self.config_path}")
            
            # デフォルト設定を上書き
            self._merge_config(self.config, file_config)
        
        # 環境変数で上書き
        self._apply_env_overrides()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            "components": {
                "video_reader": {
                    "backend": "pyav",
                    "options": {}
                },
                "video_writer": {
                    "backend": "pyav",
                    "options": {
                        "stream_copy": True
                    }
                },
                "mask_processor": {
                    "backend": "opencv",
                    "options": {}
                },
                "project_repository": {
                    "backend": "json",
                    "options": {}
                },
                "input_data_source": {
                    "backend": "local_file",
                    "options": {
                        "base_path": "test_input",
                        "video_file": "CHUC_TEST1.mp4",
                        "detections_file": "detections_genitile.json",
                        "mask_directory": "filtered"
                    }
                },
                "effect_engine": {
                    "max_workers": 4,
                    "gpu_enabled": True
                },
                "effect_presets": {
                    "preset_dir": "~/.config/mask_editor_god/presets"
                }
            },
            "performance": {
                "thread_count": 4,
                "gpu_enabled": True,
                "cache_size": 100
            },
            "paths": {
                "config_dir": "~/.config/mask_editor_god",
                "cache_dir": "~/.cache/mask_editor_god",
                "temp_dir": "/tmp/mask_editor_god"
            }
        }
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """設定をマージ（再帰的）"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _apply_env_overrides(self) -> None:
        """環境変数による設定の上書き"""
        # 例: MASK_EDITOR_VIDEO_BACKEND=cpp
        prefix = "MASK_EDITOR_"
        
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            
            # キーをパースして設定に適用
            config_key = key[len(prefix):].lower()
            
            # ビデオバックエンド
            if config_key == "video_backend":
                self.config["components"]["video_reader"]["backend"] = value
                self.config["components"]["video_writer"]["backend"] = value
            
            # マスクプロセッサバックエンド
            elif config_key == "mask_backend":
                self.config["components"]["mask_processor"]["backend"] = value
            
            # GPU有効/無効
            elif config_key == "gpu_enabled":
                self.config["performance"]["gpu_enabled"] = value.lower() in ["true", "1", "yes"]
    
    def configure_container(self, container: DIContainer) -> None:
        """
        DIコンテナを設定
        
        Args:
            container: 設定するDIコンテナ
        """
        # 設定値を登録
        for key, value in self.config.items():
            container.set_config(key, value)
        
        # コンポーネントを登録
        self._register_video_components(container)
        self._register_mask_components(container)
        self._register_project_components(container)
        self._register_input_data_components(container)
        self._register_effect_components(container)
        self._register_brush_components(container)
        self._register_id_management_components(container)
        self._register_performance_components(container)
        
        # TODO: Primary Adaptersとサービス層の登録
    
    def _register_video_components(self, container: DIContainer) -> None:
        """ビデオ関連コンポーネントを登録"""
        video_config = self.config["components"]["video_reader"]
        backend = video_config["backend"]
        
        if backend == "pyav":
            # PyAV実装を登録
            container.register_transient(IVideoReader, PyAVVideoReaderAdapter)
            container.register_transient(IVideoWriter, PyAVVideoWriterAdapter)
        
        elif backend == "cpp":
            # C++実装を登録（将来実装）
            try:
                from adapters.secondary.cpp_video_reader import CppVideoReaderAdapter
                from adapters.secondary.cpp_video_writer import CppVideoWriterAdapter
                container.register_transient(IVideoReader, CppVideoReaderAdapter)
                container.register_transient(IVideoWriter, CppVideoWriterAdapter)
            except ImportError:
                # C++実装が利用できない場合はPyAVにフォールバック
                print("Warning: C++ video backend not available, falling back to PyAV")
                container.register_transient(IVideoReader, PyAVVideoReaderAdapter)
                container.register_transient(IVideoWriter, PyAVVideoWriterAdapter)
        
        else:
            raise ValueError(f"Unknown video backend: {backend}")
    
    def _register_mask_components(self, container: DIContainer) -> None:
        """マスク関連コンポーネントを登録"""
        mask_config = self.config["components"]["mask_processor"]
        backend = mask_config["backend"]
        
        if backend == "opencv":
            container.register_transient(IMaskProcessor, OpenCVMaskProcessorAdapter)
        
        elif backend == "cpp":
            # C++実装を登録（将来実装）
            try:
                from adapters.secondary.cpp_mask_processor import CppMaskProcessorAdapter
                container.register_transient(IMaskProcessor, CppMaskProcessorAdapter)
            except ImportError:
                print("Warning: C++ mask backend not available, falling back to OpenCV")
                container.register_transient(IMaskProcessor, OpenCVMaskProcessorAdapter)
        
        else:
            raise ValueError(f"Unknown mask backend: {backend}")
    
    def _register_project_components(self, container: DIContainer) -> None:
        """プロジェクト関連コンポーネントを登録"""
        project_config = self.config["components"]["project_repository"]
        backend = project_config["backend"]
        
        if backend == "json":
            # 設定ディレクトリを展開
            config_dir = Path(self.config["paths"]["config_dir"]).expanduser()
            
            # TODO: デバッグのため一時的にシンプルな登録に変更
            # シリアライザを登録
            serializer = JsonProjectSerializer()
            container.register_instance(IProjectSerializer, serializer)
            
            # リポジトリを登録
            repository = JsonProjectRepositoryAdapter(
                serializer=serializer,
                config_dir=config_dir
            )
            container.register_instance(IProjectRepository, repository)
            
            # 自動保存を登録
            auto_saver = ProjectAutoSaverAdapter(repository=repository)
            container.register_instance(IProjectAutoSaver, auto_saver)
        
        else:
            raise ValueError(f"Unknown project backend: {backend}")
    
    def _register_input_data_components(self, container: DIContainer) -> None:
        """入力データソース関連コンポーネントを登録"""
        input_config = self.config["components"]["input_data_source"]
        backend = input_config["backend"]
        options = input_config.get("options", {})
        
        if backend == "local_file":
            # キャッシュサービスを登録
            cache_enabled = self.config.get("performance", {}).get("cache_enabled", True)
            cache_size = self.config.get("performance", {}).get("cache_size", 100)
            
            if cache_enabled:
                # キャッシュサービスを登録
                container.register_singleton(
                    IMaskCache,
                    lambda: MaskCacheService(max_size=cache_size)
                )
                
                # デコレータパターンで入力データソースをラップ
                container.register_singleton(
                    IInputDataSource,
                    lambda: self._create_cached_local_file_input(container, options)
                )
            else:
                # キャッシュなしの通常実装
                container.register_singleton(
                    IInputDataSource,
                    lambda: self._create_local_file_input(options)
                )
        
        elif backend == "network":
            # ネットワーク実装を登録（将来実装）
            raise NotImplementedError("Network input data source not yet implemented")
        
        else:
            raise ValueError(f"Unknown input data source backend: {backend}")
    
    def _create_local_file_input(self, options: Dict[str, Any]) -> LocalFileInputAdapter:
        """ローカルファイル入力アダプターを作成"""
        adapter = LocalFileInputAdapter()
        adapter.initialize(options)
        return adapter
    
    def _create_cached_local_file_input(self, container: DIContainer, options: Dict[str, Any]) -> CachedInputDataSourceDecorator:
        """キャッシュ付きローカルファイル入力アダプターを作成"""
        # 基本アダプターを作成
        base_adapter = LocalFileInputAdapter()
        base_adapter.initialize(options)
        
        # キャッシュサービスを取得
        cache_service = container.resolve(IMaskCache)
        
        # デコレータでラップ
        cached_adapter = CachedInputDataSourceDecorator(base_adapter, cache_service)
        
        # キャッシュサービスにコールバックを設定
        if hasattr(cache_service, 'set_load_callback'):
            cache_service.set_load_callback(base_adapter.get_mask)
        
        return cached_adapter
    
    def _register_effect_components(self, container: DIContainer) -> None:
        """エフェクト関連コンポーネントを登録"""
        effect_config = self.config["components"]["effect_engine"]
        preset_config = self.config["components"]["effect_presets"]
        
        # TODO: デバッグのため一時的にシンプルな登録に変更
        # エフェクトエンジンを登録
        effect_engine = EffectEngine(
            max_workers=effect_config.get("max_workers", 4)
        )
        container.register_instance(IEffectEngine, effect_engine)
        
        # エフェクトレンダラーを登録
        renderer = EffectRenderer()
        container.register_instance(IEffectRenderer, renderer)
        
        # プリセットマネージャーを登録
        preset_dir = Path(preset_config["preset_dir"]).expanduser()
        preset_manager = EffectPresetManager(str(preset_dir))
        container.register_instance(IEffectPresetManager, preset_manager)
        
        # エフェクトプレビューを登録
        effect_preview = EffectPreview(effect_engine=effect_engine)
        container.register_instance(IEffectPreview, effect_preview)
        
        # GPU設定を適用
        if effect_config.get("gpu_enabled", True):
            effect_engine.set_gpu_enabled(True)
    
    def _register_brush_components(self, container: DIContainer) -> None:
        """ブラシ関連コンポーネントを登録"""
        # ブラシエンジンを登録
        brush_engine = OpenCVBrushEngine()
        container.register_instance(IBrushEngine, brush_engine)
        
        # ブラシプレビューを登録
        brush_preview = BrushPreviewAdapter()
        container.register_instance(IBrushPreview, brush_preview)
        
        # ブラシ履歴を登録
        brush_history = BrushHistoryAdapter(max_history=100)
        container.register_instance(IBrushHistory, brush_history)
        
        # ブラシ最適化を登録
        brush_optimizer = OpenCVBrushOptimizer()
        container.register_instance(IBrushOptimizer, brush_optimizer)
        
        logger.debug("Brush components registered")
    
    def _register_id_management_components(self, container: DIContainer) -> None:
        """ID管理関連コンポーネントを登録"""
        from adapters.secondary.id_manager_adapter import IDManagerAdapter
        from adapters.secondary.threshold_manager_adapter import ThresholdManagerAdapter
        from adapters.secondary.id_preview_adapter import IDPreviewAdapter
        from domain.ports.secondary.id_management_ports import IIDManager, IThresholdManager, IIDPreview
        
        # ID管理を登録
        id_manager = IDManagerAdapter()
        container.register_instance(IIDManager, id_manager)
        
        # 閾値管理を登録
        threshold_manager = ThresholdManagerAdapter()
        container.register_instance(IThresholdManager, threshold_manager)
        
        # IDプレビューを登録
        id_preview = IDPreviewAdapter()
        container.register_instance(IIDPreview, id_preview)
        
        logger.debug("ID management components registered")
    
    def _register_performance_components(self, container: DIContainer) -> None:
        """パフォーマンス関連コンポーネントを登録"""
        performance_config = self.config.get("performance", {})
        
        # フレームスロットリングサービスを登録
        fps_limit = performance_config.get("fps_limit", 30)
        frame_throttle = FrameUpdateThrottleService(fps_limit=fps_limit)
        container.register_instance(IFrameThrottleService, frame_throttle)
        
        # UI更新最適化サービスを登録
        ui_optimizer = UIUpdateOptimizer()
        container.register_instance(IUIUpdateOptimizer, ui_optimizer)
        
        logger.debug("Performance components registered")


def create_default_container(config_path: Optional[Path] = None) -> DIContainer:
    """
    デフォルト設定でDIコンテナを作成
    
    Args:
        config_path: 設定ファイルのパス
        
    Returns:
        設定済みのDIコンテナ
    """
    container = DIContainer()
    configurator = ContainerConfigurator(config_path)
    configurator.configure_container(container)
    return container