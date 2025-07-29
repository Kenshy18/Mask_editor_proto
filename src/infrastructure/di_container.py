#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依存性注入コンテナ

型安全な依存性注入を提供するコンテナ実装。
"""
from typing import Dict, Any, Callable, TypeVar, Type, Optional, Protocol, Union
from enum import Enum
import inspect
from threading import Lock


T = TypeVar('T')


class Lifetime(Enum):
    """オブジェクトのライフタイム"""
    SINGLETON = "singleton"  # アプリケーション全体で1つのインスタンス
    TRANSIENT = "transient"  # 要求ごとに新しいインスタンス
    SCOPED = "scoped"  # スコープごとに1つのインスタンス（将来実装）


class ServiceDescriptor:
    """サービス記述子"""
    
    def __init__(
        self,
        service_type: Type[T],
        factory: Callable[[], T],
        lifetime: Lifetime = Lifetime.TRANSIENT
    ):
        self.service_type = service_type
        self.factory = factory
        self.lifetime = lifetime


class DIContainer:
    """
    依存性注入コンテナ
    
    型安全なサービスの登録と解決を提供。
    """
    
    def __init__(self):
        self._services: Dict[type, ServiceDescriptor] = {}
        self._singletons: Dict[type, Any] = {}
        self._config: Dict[str, Any] = {}
        self._lock = Lock()
    
    def register(
        self,
        interface: Type[T],
        factory: Union[Callable[[], T], Type[T]],
        lifetime: Lifetime = Lifetime.TRANSIENT
    ) -> None:
        """
        サービスを登録
        
        Args:
            interface: インターフェース型
            factory: ファクトリ関数またはクラス
            lifetime: オブジェクトのライフタイム
        """
        # クラスが渡された場合はファクトリ関数に変換
        if inspect.isclass(factory):
            factory_func = lambda: self._create_instance(factory)
        else:
            factory_func = factory
        
        descriptor = ServiceDescriptor(interface, factory_func, lifetime)
        self._services[interface] = descriptor
    
    def register_singleton(self, interface: Type[T], factory: Union[Callable[[], T], Type[T]]) -> None:
        """シングルトンとしてサービスを登録"""
        self.register(interface, factory, Lifetime.SINGLETON)
    
    def register_transient(self, interface: Type[T], factory: Union[Callable[[], T], Type[T]]) -> None:
        """トランジェントとしてサービスを登録"""
        self.register(interface, factory, Lifetime.TRANSIENT)
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """既存のインスタンスをシングルトンとして登録"""
        self._services[interface] = ServiceDescriptor(
            interface,
            lambda: instance,
            Lifetime.SINGLETON
        )
        self._singletons[interface] = instance
    
    def resolve(self, interface: Type[T]) -> T:
        """
        サービスを解決
        
        Args:
            interface: 解決するインターフェース型
            
        Returns:
            サービスのインスタンス
            
        Raises:
            ValueError: サービスが登録されていない場合
        """
        if interface not in self._services:
            raise ValueError(f"Service not registered: {interface.__name__}")
        
        descriptor = self._services[interface]
        
        if descriptor.lifetime == Lifetime.SINGLETON:
            return self._resolve_singleton(descriptor)
        elif descriptor.lifetime == Lifetime.TRANSIENT:
            return descriptor.factory()
        else:
            # SCOPED は将来実装
            raise NotImplementedError(f"Lifetime {descriptor.lifetime} not implemented")
    
    def _resolve_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """シングルトンを解決"""
        with self._lock:
            if descriptor.service_type not in self._singletons:
                self._singletons[descriptor.service_type] = descriptor.factory()
            return self._singletons[descriptor.service_type]
    
    def _create_instance(self, cls: Type[T]) -> T:
        """
        クラスのインスタンスを作成（依存性を自動注入）
        
        Args:
            cls: インスタンス化するクラス
            
        Returns:
            作成されたインスタンス
        """
        # コンストラクタのパラメータを取得
        sig = inspect.signature(cls.__init__)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # 型ヒントから依存性を解決
            if param.annotation != param.empty:
                param_type = param.annotation
                
                # Optionalの場合は内部の型を取得
                if hasattr(param_type, '__origin__') and param_type.__origin__ is Union:
                    args = param_type.__args__
                    if len(args) == 2 and type(None) in args:
                        param_type = args[0] if args[1] is type(None) else args[1]
                
                # サービスが登録されている場合は解決
                if param_type in self._services:
                    kwargs[param_name] = self.resolve(param_type)
                elif param.default != param.empty:
                    # デフォルト値がある場合はそれを使用
                    kwargs[param_name] = param.default
                else:
                    raise ValueError(
                        f"Cannot resolve dependency '{param_name}' of type {param_type} "
                        f"for {cls.__name__}"
                    )
        
        return cls(**kwargs)
    
    def set_config(self, key: str, value: Any) -> None:
        """設定値を登録"""
        self._config[key] = value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self._config.get(key, default)
    
    def clear(self) -> None:
        """コンテナをクリア"""
        with self._lock:
            self._services.clear()
            self._singletons.clear()
            self._config.clear()
    
    def has_service(self, interface: Type[T]) -> bool:
        """サービスが登録されているか確認"""
        return interface in self._services
    
    def get_all_services(self) -> Dict[type, ServiceDescriptor]:
        """登録されている全サービスを取得"""
        return self._services.copy()


# グローバルコンテナインスタンス
_global_container: Optional[DIContainer] = None
_container_lock = Lock()


def get_container() -> DIContainer:
    """グローバルコンテナを取得"""
    global _global_container
    
    with _container_lock:
        if _global_container is None:
            _global_container = DIContainer()
        return _global_container


def set_container(container: DIContainer) -> None:
    """グローバルコンテナを設定"""
    global _global_container
    
    with _container_lock:
        _global_container = container