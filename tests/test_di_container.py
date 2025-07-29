#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIコンテナのテスト
"""
import pytest
from typing import Protocol

from infrastructure import DIContainer, Lifetime


class ITestService(Protocol):
    """テスト用サービスインターフェース"""
    def get_value(self) -> str: ...


class TestServiceA:
    """テスト用サービス実装A"""
    def get_value(self) -> str:
        return "Service A"


class TestServiceB:
    """テスト用サービス実装B"""
    def get_value(self) -> str:
        return "Service B"


class DependentService:
    """依存性を持つサービス"""
    def __init__(self, service: ITestService):
        self.service = service
    
    def get_dependent_value(self) -> str:
        return f"Dependent on: {self.service.get_value()}"


class TestDIContainer:
    """DIコンテナのテスト"""
    
    def test_register_and_resolve_transient(self):
        """トランジェントサービスの登録と解決"""
        container = DIContainer()
        
        # サービスを登録
        container.register(ITestService, TestServiceA, Lifetime.TRANSIENT)
        
        # サービスを解決
        service1 = container.resolve(ITestService)
        service2 = container.resolve(ITestService)
        
        assert isinstance(service1, TestServiceA)
        assert isinstance(service2, TestServiceA)
        assert service1 is not service2  # トランジェントなので別インスタンス
    
    def test_register_and_resolve_singleton(self):
        """シングルトンサービスの登録と解決"""
        container = DIContainer()
        
        # サービスを登録
        container.register_singleton(ITestService, TestServiceA)
        
        # サービスを解決
        service1 = container.resolve(ITestService)
        service2 = container.resolve(ITestService)
        
        assert isinstance(service1, TestServiceA)
        assert isinstance(service2, TestServiceA)
        assert service1 is service2  # シングルトンなので同一インスタンス
    
    def test_register_instance(self):
        """既存インスタンスの登録"""
        container = DIContainer()
        
        # インスタンスを作成して登録
        instance = TestServiceA()
        container.register_instance(ITestService, instance)
        
        # サービスを解決
        resolved = container.resolve(ITestService)
        
        assert resolved is instance
    
    def test_auto_injection(self):
        """自動依存性注入"""
        container = DIContainer()
        
        # 依存サービスを登録
        container.register(ITestService, TestServiceA)
        
        # 依存性を持つサービスを登録
        container.register(DependentService, DependentService)
        
        # サービスを解決（依存性が自動注入される）
        dependent = container.resolve(DependentService)
        
        assert isinstance(dependent, DependentService)
        assert dependent.get_dependent_value() == "Dependent on: Service A"
    
    def test_service_not_registered(self):
        """未登録サービスの解決エラー"""
        container = DIContainer()
        
        with pytest.raises(ValueError, match="Service not registered"):
            container.resolve(ITestService)
    
    def test_has_service(self):
        """サービス登録確認"""
        container = DIContainer()
        
        assert not container.has_service(ITestService)
        
        container.register(ITestService, TestServiceA)
        
        assert container.has_service(ITestService)
    
    def test_config_management(self):
        """設定値の管理"""
        container = DIContainer()
        
        # 設定値を登録
        container.set_config("test.value", 123)
        container.set_config("test.string", "hello")
        
        # 設定値を取得
        assert container.get_config("test.value") == 123
        assert container.get_config("test.string") == "hello"
        assert container.get_config("test.missing", "default") == "default"
    
    def test_clear(self):
        """コンテナのクリア"""
        container = DIContainer()
        
        # サービスと設定を登録
        container.register(ITestService, TestServiceA)
        container.set_config("test.value", 123)
        
        # クリア
        container.clear()
        
        # 確認
        assert not container.has_service(ITestService)
        assert container.get_config("test.value") is None
    
    def test_factory_function(self):
        """ファクトリ関数の使用"""
        container = DIContainer()
        
        # カウンターを使用したファクトリ
        counter = 0
        def create_service():
            nonlocal counter
            counter += 1
            service = TestServiceA()
            service.counter = counter
            return service
        
        container.register(ITestService, create_service, Lifetime.TRANSIENT)
        
        # 解決するたびに新しいインスタンス
        service1 = container.resolve(ITestService)
        service2 = container.resolve(ITestService)
        
        assert service1.counter == 1
        assert service2.counter == 2