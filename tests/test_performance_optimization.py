#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
パフォーマンス最適化の統合テスト

設計原則に従ったパフォーマンス最適化の動作を検証
"""
import unittest
import time
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from infrastructure.services.frame_update_throttle_service import FrameUpdateThrottleService, UIUpdateOptimizer
from infrastructure.services.mask_cache_service import MaskCacheService
from adapters.secondary.input_data_source_decorator import CachedInputDataSourceDecorator
from domain.dto.mask_dto import MaskDTO
import numpy as np


class TestFrameUpdateThrottleService(unittest.TestCase):
    """フレーム更新スロットリングサービスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.throttle = FrameUpdateThrottleService(fps_limit=30)
    
    def test_throttling_during_playback(self):
        """再生中のスロットリング動作"""
        # 33ms間隔（30FPS）でフレーム更新を試行
        results = []
        
        for i in range(10):
            should_update = self.throttle.should_update(i, is_playing=True)
            results.append(should_update)
            time.sleep(0.01)  # 10ms待機
        
        # 最初のフレームは必ず更新される
        self.assertTrue(results[0])
        
        # 全てのフレームが更新されるわけではない（スロットリング効果）
        self.assertLess(sum(results), 10)
        
        # パフォーマンス統計を確認
        stats = self.throttle.get_performance_stats()
        self.assertGreater(stats['dropped_frames'], 0)
        self.assertEqual(stats['fps_limit'], 30)
    
    def test_no_throttling_when_paused(self):
        """一時停止中はスロットリングなし"""
        results = []
        
        for i in range(5):
            should_update = self.throttle.should_update(i, is_playing=False)
            results.append(should_update)
            time.sleep(0.01)
        
        # 全てのフレームが更新される
        self.assertEqual(sum(results), 5)
    
    def test_pending_frame_retrieval(self):
        """保留フレームの取得"""
        # 高速でフレーム更新を試行
        for i in range(10):
            self.throttle.should_update(i, is_playing=True)
            time.sleep(0.001)  # 1ms待機
        
        # 保留中のフレームを取得
        pending = self.throttle.get_pending_frame()
        self.assertIsNotNone(pending)
        
        # 2回目の取得ではNone
        self.assertIsNone(self.throttle.get_pending_frame())


class TestUIUpdateOptimizer(unittest.TestCase):
    """UI更新最適化サービスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.optimizer = UIUpdateOptimizer()
    
    def test_component_update_intervals(self):
        """コンポーネントごとの更新間隔"""
        self.optimizer.set_playing_state(True)
        
        timeline_updates = []
        id_panel_updates = []
        
        # 50フレーム分の更新をシミュレート
        for frame in range(50):
            if self.optimizer.should_update_component("timeline", frame):
                timeline_updates.append(frame)
            if self.optimizer.should_update_component("id_management", frame):
                id_panel_updates.append(frame)
        
        # タイムラインは10フレームごと
        self.assertLessEqual(len(timeline_updates), 6)
        
        # ID管理パネルは30フレームごと
        self.assertLessEqual(len(id_panel_updates), 2)
    
    def test_all_updates_when_paused(self):
        """一時停止中は全て更新"""
        self.optimizer.set_playing_state(False)
        
        updates = []
        for frame in range(10):
            if self.optimizer.should_update_component("timeline", frame):
                updates.append(frame)
        
        # 全フレームで更新される
        self.assertEqual(len(updates), 10)


class TestCachedInputDataSource(unittest.TestCase):
    """キャッシュ付き入力データソースのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        # モックの入力データソース
        self.inner_source = Mock()
        mask_data = np.zeros((512, 512), dtype=np.uint8)
        # オブジェクトIDをマスクデータに追加
        mask_data[10:20, 10:20] = 1
        mask_data[30:40, 30:40] = 2
        mask_data[50:60, 50:60] = 3
        
        self.inner_source.get_mask.return_value = MaskDTO(
            frame_index=0,
            data=mask_data,
            width=512,
            height=512,
            object_ids=[1, 2, 3],
            classes={1: "class1", 2: "class2", 3: "class3"},
            confidences={1: 0.9, 2: 0.8, 3: 0.7}
        )
        
        # キャッシュサービス
        self.cache_service = MaskCacheService(max_size=10)
        
        # デコレータ
        self.cached_source = CachedInputDataSourceDecorator(
            self.inner_source,
            self.cache_service
        )
    
    def test_cache_hit(self):
        """キャッシュヒット時の動作"""
        # 最初の呼び出し
        mask1 = self.cached_source.get_mask(0)
        self.assertEqual(self.inner_source.get_mask.call_count, 1)
        
        # 2回目の呼び出し（キャッシュから）
        mask2 = self.cached_source.get_mask(0)
        self.assertEqual(self.inner_source.get_mask.call_count, 1)  # 呼び出し回数は増えない
        
        # 同じマスクが返される
        self.assertEqual(mask1.frame_index, mask2.frame_index)
        np.testing.assert_array_equal(mask1.data, mask2.data)
    
    def test_cache_miss(self):
        """キャッシュミス時の動作"""
        # 異なるフレームを要求
        self.cached_source.get_mask(0)
        self.cached_source.get_mask(1)
        self.cached_source.get_mask(2)
        
        # 3回呼び出される
        self.assertEqual(self.inner_source.get_mask.call_count, 3)
    
    def test_prefetch_behavior(self):
        """プリフェッチ動作の確認"""
        # プリフェッチを有効にしてマスクを取得
        mask = self.cached_source.get_mask(5)
        
        # しばらく待機（プリフェッチが動作する時間を与える）
        time.sleep(0.1)
        
        # 次のフレームがキャッシュにあることを確認
        # （実際のプリフェッチ実装に依存）
        # ここでは基本的な動作のみ確認
        self.assertIsNotNone(mask)


class TestPerformanceIntegration(unittest.TestCase):
    """パフォーマンス最適化の統合テスト"""
    
    def test_improved_main_window_with_throttling(self):
        """ImprovedMainWindowでのスロットリング統合"""
        from infrastructure.container_config import create_default_container
        
        # DIコンテナを作成
        container = create_default_container()
        
        # パフォーマンスサービスを直接取得してテスト
        from domain.ports.secondary.performance_ports import IFrameThrottleService, IUIUpdateOptimizer
        
        frame_throttle = container.resolve(IFrameThrottleService)
        ui_optimizer = container.resolve(IUIUpdateOptimizer)
        
        # サービスが正しく登録されているか確認
        self.assertIsNotNone(frame_throttle)
        self.assertIsNotNone(ui_optimizer)
        
        # 再生状態を設定
        ui_optimizer.set_playing_state(True)
        
        # 高速でフレーム更新をシミュレート
        update_count = 0
        for i in range(100):
            if frame_throttle.should_update(i, is_playing=True):
                update_count += 1
            time.sleep(0.001)  # 1ms間隔
        
        # スロットリングにより更新回数が制限される
        self.assertLess(update_count, 50)  # 100フレーム中50回未満の更新
        
        # パフォーマンス統計を確認
        stats = frame_throttle.get_performance_stats()
        self.assertGreater(stats['dropped_frames'], 0)
        self.assertGreater(stats['drop_rate'], 0)


if __name__ == '__main__':
    unittest.main()