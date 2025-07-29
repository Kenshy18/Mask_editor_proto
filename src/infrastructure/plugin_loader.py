#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プラグインローダー

カスタムエフェクトやアダプターを動的に読み込むプラグインシステム。
"""
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Type, Any, Optional, Protocol
import inspect
import json
import logging

from domain.ports.secondary.effect_ports import IEffect
from infrastructure.di_container import DIContainer

logger = logging.getLogger(__name__)


class IPlugin(Protocol):
    """プラグインインターフェース"""
    
    @property
    def name(self) -> str:
        """プラグイン名"""
        ...
    
    @property
    def version(self) -> str:
        """プラグインバージョン"""
        ...
    
    @property
    def description(self) -> str:
        """プラグインの説明"""
        ...
    
    def register(self, container: DIContainer) -> None:
        """
        DIコンテナにサービスを登録
        
        Args:
            container: 登録先のDIコンテナ
        """
        ...


class PluginMetadata:
    """プラグインメタデータ"""
    
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.config_file = path / "plugin.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """メタデータを読み込む"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "name": self.name,
            "version": "0.0.0",
            "description": "No description",
            "entry_point": "__init__",
            "dependencies": []
        }
    
    @property
    def entry_point(self) -> str:
        """エントリーポイントモジュール名"""
        return self.metadata.get("entry_point", "__init__")
    
    @property
    def dependencies(self) -> List[str]:
        """依存プラグインのリスト"""
        return self.metadata.get("dependencies", [])


class PluginLoader:
    """
    プラグインローダー
    
    指定ディレクトリからプラグインを動的に読み込み、
    DIコンテナに登録する。
    """
    
    def __init__(self, plugin_dir: Path):
        """
        Args:
            plugin_dir: プラグインディレクトリ
        """
        self.plugin_dir = plugin_dir
        self.loaded_plugins: Dict[str, IPlugin] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """
        プラグインを探索
        
        Returns:
            発見されたプラグインのメタデータリスト
        """
        plugins = []
        
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {self.plugin_dir}")
            return plugins
        
        # プラグインディレクトリをスキャン
        for path in self.plugin_dir.iterdir():
            if path.is_dir() and not path.name.startswith('_'):
                # __init__.pyまたはplugin.jsonがあるディレクトリをプラグインとして認識
                if (path / "__init__.py").exists() or (path / "plugin.json").exists():
                    metadata = PluginMetadata(path)
                    plugins.append(metadata)
                    self.plugin_metadata[metadata.name] = metadata
        
        return plugins
    
    def load_plugin(self, name: str) -> Optional[IPlugin]:
        """
        プラグインを読み込む
        
        Args:
            name: プラグイン名
            
        Returns:
            読み込まれたプラグイン（失敗時はNone）
        """
        if name in self.loaded_plugins:
            return self.loaded_plugins[name]
        
        if name not in self.plugin_metadata:
            logger.error(f"Plugin not found: {name}")
            return None
        
        metadata = self.plugin_metadata[name]
        
        try:
            # 依存関係を先に読み込む
            for dep in metadata.dependencies:
                if not self.load_plugin(dep):
                    logger.error(f"Failed to load dependency: {dep}")
                    return None
            
            # プラグインモジュールを動的にインポート
            module_path = metadata.path / f"{metadata.entry_point}.py"
            spec = importlib.util.spec_from_file_location(
                f"plugins.{name}",
                module_path
            )
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # IPluginを実装するクラスを探す
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (inspect.isclass(attr) and 
                        attr is not IPlugin and
                        issubclass(attr, IPlugin)):
                        # プラグインインスタンスを作成
                        plugin = attr()
                        self.loaded_plugins[name] = plugin
                        logger.info(f"Loaded plugin: {name} v{plugin.version}")
                        return plugin
                
                logger.error(f"No IPlugin implementation found in {name}")
                
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
        
        return None
    
    def load_all_plugins(self) -> List[IPlugin]:
        """
        すべてのプラグインを読み込む
        
        Returns:
            読み込まれたプラグインのリスト
        """
        self.discover_plugins()
        loaded = []
        
        for name in self.plugin_metadata:
            plugin = self.load_plugin(name)
            if plugin:
                loaded.append(plugin)
        
        return loaded
    
    def register_plugins(self, container: DIContainer) -> None:
        """
        読み込まれたプラグインをDIコンテナに登録
        
        Args:
            container: 登録先のDIコンテナ
        """
        for plugin in self.loaded_plugins.values():
            try:
                plugin.register(container)
                logger.info(f"Registered plugin: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to register plugin {plugin.name}: {e}")


class EffectPluginBase(IPlugin):
    """
    エフェクトプラグインの基底クラス
    
    カスタムエフェクトを作成する際の基底クラス。
    """
    
    def __init__(self, effect_class: Type[IEffect]):
        """
        Args:
            effect_class: 登録するエフェクトクラス
        """
        self.effect_class = effect_class
        self._effect_instance = effect_class()
    
    @property
    def name(self) -> str:
        return self._effect_instance.get_metadata().effect_type.value
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return self._effect_instance.get_metadata().display_name
    
    def register(self, container: DIContainer) -> None:
        """DIコンテナにエフェクトを登録"""
        # エフェクトエンジンを取得
        from domain.ports.secondary.effect_ports import IEffectEngine
        
        if container.has_service(IEffectEngine):
            engine = container.resolve(IEffectEngine)
            # エフェクトを登録
            engine.register_effect(
                self._effect_instance.get_metadata().effect_type,
                self.effect_class
            )
            logger.info(f"Registered effect: {self.name}")
        else:
            logger.warning("IEffectEngine not found in container")


def create_plugin_loader(plugin_dir: Optional[Path] = None) -> PluginLoader:
    """
    デフォルト設定でプラグインローダーを作成
    
    Args:
        plugin_dir: プラグインディレクトリ（省略時はデフォルト）
        
    Returns:
        プラグインローダー
    """
    if plugin_dir is None:
        # デフォルトのプラグインディレクトリ
        plugin_dir = Path.home() / ".config" / "mask_editor_god" / "plugins"
    
    return PluginLoader(plugin_dir)