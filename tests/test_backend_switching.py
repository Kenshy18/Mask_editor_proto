#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バックエンド切り替えテスト

DIコンテナのバックエンド切り替え機能とC++統合の準備状況を検証。
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json
import os

from infrastructure.di_container import DIContainer
from infrastructure.container_config import ContainerConfigurator
from domain.ports.secondary import IVideoReader, IVideoWriter, IMaskProcessor
from adapters.secondary import PyAVVideoReaderAdapter, PyAVVideoWriterAdapter


class TestBackendSwitching(unittest.TestCase):
    """バックエンド切り替え機能のテスト"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.json"
    
    def tearDown(self):
        """テスト環境のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_backend_registration(self):
        """デフォルトバックエンドの登録テスト"""
        container = DIContainer()
        configurator = ContainerConfigurator()
        configurator.configure_container(container)
        
        # PyAVバックエンドがデフォルトで登録されているか確認
        self.assertTrue(container.has_service(IVideoReader))
        self.assertTrue(container.has_service(IVideoWriter))
        
        # 実際のインスタンスを解決
        reader = container.resolve(IVideoReader)
        writer = container.resolve(IVideoWriter)
        
        self.assertIsInstance(reader, PyAVVideoReaderAdapter)
        self.assertIsInstance(writer, PyAVVideoWriterAdapter)
    
    def test_cpp_backend_fallback(self):
        """C++バックエンドのフォールバックテスト"""
        # C++バックエンドを指定する設定
        config = {
            "components": {
                "video_reader": {"backend": "cpp"},
                "video_writer": {"backend": "cpp"}
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        
        container = DIContainer()
        configurator = ContainerConfigurator(self.config_file)
        
        # C++モジュールが存在しない場合の警告をキャプチャ
        with patch('builtins.print') as mock_print:
            configurator.configure_container(container)
            
            # 警告メッセージが出力されたか確認
            mock_print.assert_called_with(
                "Warning: C++ video backend not available, falling back to PyAV"
            )
        
        # PyAVにフォールバックされているか確認
        reader = container.resolve(IVideoReader)
        self.assertIsInstance(reader, PyAVVideoReaderAdapter)
    
    def test_cpp_backend_with_mock(self):
        """C++バックエンドのモック実装テスト"""
        # C++実装をモック
        mock_cpp_reader = Mock()
        mock_cpp_writer = Mock()
        
        # モックモジュールを作成
        with patch.dict('sys.modules', {
            'adapters.secondary.cpp_video_reader': MagicMock(
                CppVideoReaderAdapter=mock_cpp_reader
            ),
            'adapters.secondary.cpp_video_writer': MagicMock(
                CppVideoWriterAdapter=mock_cpp_writer
            )
        }):
            config = {
                "components": {
                    "video_reader": {"backend": "cpp"},
                    "video_writer": {"backend": "cpp"}
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            
            container = DIContainer()
            configurator = ContainerConfigurator(self.config_file)
            configurator.configure_container(container)
            
            # C++実装が登録されているか確認
            self.assertTrue(container.has_service(IVideoReader))
            self.assertTrue(container.has_service(IVideoWriter))
    
    def test_environment_variable_override(self):
        """環境変数によるバックエンド切り替えテスト"""
        # 環境変数でバックエンドを指定
        os.environ['MASK_EDITOR_VIDEO_BACKEND'] = 'cpp'
        os.environ['MASK_EDITOR_GPU_ENABLED'] = 'false'
        
        try:
            container = DIContainer()
            configurator = ContainerConfigurator()
            
            with patch('builtins.print'):  # 警告を抑制
                configurator.configure_container(container)
            
            # 設定が環境変数で上書きされているか確認
            config = container.get_config('components')
            self.assertEqual(config['video_reader']['backend'], 'cpp')
            self.assertEqual(config['video_writer']['backend'], 'cpp')
            
            performance_config = container.get_config('performance')
            self.assertFalse(performance_config['gpu_enabled'])
            
        finally:
            # 環境変数をクリーンアップ
            del os.environ['MASK_EDITOR_VIDEO_BACKEND']
            del os.environ['MASK_EDITOR_GPU_ENABLED']
    
    def test_runtime_backend_switching(self):
        """実行時のバックエンド切り替えテスト"""
        container = DIContainer()
        
        # 初期状態でPyAVを登録
        container.register_transient(IVideoReader, PyAVVideoReaderAdapter)
        reader1 = container.resolve(IVideoReader)
        self.assertIsInstance(reader1, PyAVVideoReaderAdapter)
        
        # モックのC++実装に切り替え
        mock_cpp_reader = Mock(spec=IVideoReader)
        container.register_transient(IVideoReader, lambda: mock_cpp_reader)
        
        reader2 = container.resolve(IVideoReader)
        self.assertEqual(reader2, mock_cpp_reader)
        self.assertNotIsInstance(reader2, PyAVVideoReaderAdapter)
    
    def test_mixed_backend_configuration(self):
        """異なるコンポーネントで異なるバックエンドを使用するテスト"""
        config = {
            "components": {
                "video_reader": {"backend": "pyav"},
                "video_writer": {"backend": "pyav"},
                "mask_processor": {"backend": "cpp"}
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        
        container = DIContainer()
        configurator = ContainerConfigurator(self.config_file)
        
        with patch('builtins.print'):  # 警告を抑制
            configurator.configure_container(container)
        
        # ビデオ処理はPyAV、マスク処理はC++（フォールバック）を使用
        reader = container.resolve(IVideoReader)
        self.assertIsInstance(reader, PyAVVideoReaderAdapter)
        
        # マスクプロセッサも確認
        self.assertTrue(container.has_service(IMaskProcessor))


class TestDIContainerFlexibility(unittest.TestCase):
    """DIコンテナの柔軟性テスト"""
    
    def test_custom_factory_registration(self):
        """カスタムファクトリ関数の登録テスト"""
        container = DIContainer()
        
        # カスタムファクトリでインスタンスを作成
        def create_custom_reader():
            reader = PyAVVideoReaderAdapter()
            # カスタム設定を適用
            reader._custom_config = {"buffer_size": 1024}
            return reader
        
        container.register_singleton(IVideoReader, create_custom_reader)
        
        reader1 = container.resolve(IVideoReader)
        reader2 = container.resolve(IVideoReader)
        
        # シングルトンなので同じインスタンス
        self.assertIs(reader1, reader2)
        self.assertEqual(reader1._custom_config["buffer_size"], 1024)
    
    def test_dependency_chain_resolution(self):
        """依存関係チェーンの解決テスト"""
        container = DIContainer()
        
        # 依存関係を持つクラスを定義
        class ServiceA:
            pass
        
        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a
        
        class ServiceC:
            def __init__(self, service_b: ServiceB):
                self.service_b = service_b
        
        # 登録
        container.register_singleton(ServiceA, ServiceA)
        container.register_singleton(ServiceB, ServiceB)
        container.register_singleton(ServiceC, ServiceC)
        
        # 解決
        service_c = container.resolve(ServiceC)
        
        # 依存関係が正しく解決されているか確認
        self.assertIsInstance(service_c, ServiceC)
        self.assertIsInstance(service_c.service_b, ServiceB)
        self.assertIsInstance(service_c.service_b.service_a, ServiceA)
    
    def test_configuration_injection(self):
        """設定値の注入テスト"""
        container = DIContainer()
        
        # 設定値を登録
        container.set_config("video", {
            "max_buffer_size": 100,
            "codec": "h264"
        })
        
        # 設定を使用するサービス
        class ConfigurableService:
            def __init__(self):
                self.config = None
            
            def configure(self, container: DIContainer):
                self.config = container.get_config("video")
        
        # ファクトリ関数で設定を注入
        def create_service():
            service = ConfigurableService()
            service.configure(container)
            return service
        
        container.register_singleton(ConfigurableService, create_service)
        
        service = container.resolve(ConfigurableService)
        self.assertEqual(service.config["max_buffer_size"], 100)
        self.assertEqual(service.config["codec"], "h264")


if __name__ == '__main__':
    unittest.main()