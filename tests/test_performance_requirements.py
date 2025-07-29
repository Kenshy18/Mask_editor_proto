#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
パフォーマンス要件テスト

NFR-1: 1080p@30fps動画をリアルタイムで処理（≤50ms/frame）
を満たしているか検証。
"""
import unittest
import time
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import psutil
import os

from infrastructure.di_container import DIContainer
from infrastructure.container_config import create_default_container
from domain.ports.secondary import IVideoReader, IVideoWriter, IMaskProcessor
from domain.ports.secondary.effect_ports import IEffectEngine, IEffect
from adapters.secondary.effects import MosaicEffect, BlurEffect
from adapters.secondary.effect_engine import EffectEngine


class TestPerformanceRequirements(unittest.TestCase):
    """パフォーマンス要件のテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスのセットアップ"""
        # 1080pのテストフレームを作成
        cls.frame_1080p = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        cls.mask_1080p = np.random.randint(0, 255, (1080, 1920), dtype=np.uint8)
        
        # 720pのテストフレームも用意
        cls.frame_720p = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        cls.mask_720p = np.random.randint(0, 255, (720, 1280), dtype=np.uint8)
    
    def setUp(self):
        """各テストのセットアップ"""
        self.container = create_default_container()
    
    def test_single_effect_performance_1080p(self):
        """単一エフェクトの1080p処理性能テスト"""
        # エフェクトエンジンを取得
        engine = self.container.resolve(IEffectEngine)
        
        # モザイクエフェクトを登録
        mosaic = MosaicEffect()
        engine.add_effect("mosaic", mosaic, {"block_size": 16})
        
        # ウォームアップ（JITコンパイラ等の初期化のため）
        for _ in range(5):
            engine.apply_effects(self.frame_1080p, self.mask_1080p)
        
        # パフォーマンス測定
        num_frames = 30
        start_time = time.perf_counter()
        
        for _ in range(num_frames):
            result = engine.apply_effects(self.frame_1080p, self.mask_1080p)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_frame = total_time / num_frames * 1000  # ミリ秒
        
        print(f"\n1080p Single Effect Performance:")
        print(f"  Average time per frame: {avg_time_per_frame:.2f}ms")
        print(f"  FPS: {1000/avg_time_per_frame:.2f}")
        
        # NFR-1: 50ms以下であることを確認
        self.assertLess(avg_time_per_frame, 50.0,
                       f"Frame processing took {avg_time_per_frame:.2f}ms, "
                       f"exceeding 50ms requirement")
    
    def test_multiple_effects_performance_1080p(self):
        """複数エフェクトの1080p処理性能テスト"""
        engine = self.container.resolve(IEffectEngine)
        
        # 複数のエフェクトを登録
        engine.add_effect("mosaic", MosaicEffect(), {"block_size": 16})
        engine.add_effect("blur", BlurEffect(), {"blur_radius": 15})
        
        # ウォームアップ
        for _ in range(5):
            engine.apply_effects(self.frame_1080p, self.mask_1080p)
        
        # パフォーマンス測定
        num_frames = 30
        start_time = time.perf_counter()
        
        for _ in range(num_frames):
            result = engine.apply_effects(self.frame_1080p, self.mask_1080p)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time_per_frame = total_time / num_frames * 1000
        
        print(f"\n1080p Multiple Effects Performance:")
        print(f"  Average time per frame: {avg_time_per_frame:.2f}ms")
        print(f"  FPS: {1000/avg_time_per_frame:.2f}")
        
        # 複数エフェクトでも100ms以下を目標
        self.assertLess(avg_time_per_frame, 100.0,
                       f"Multiple effects processing took {avg_time_per_frame:.2f}ms")
    
    def test_mask_processing_performance(self):
        """マスク処理の性能テスト"""
        mask_processor = self.container.resolve(IMaskProcessor)
        
        # ウォームアップ
        for _ in range(5):
            mask_processor.apply_morphology(self.mask_1080p, "dilate", 3)
        
        # 各モルフォロジー操作の性能を測定
        operations = ["dilate", "erode", "open", "close"]
        
        print("\n1080p Mask Processing Performance:")
        
        for op in operations:
            start_time = time.perf_counter()
            
            for _ in range(30):
                result = mask_processor.apply_morphology(self.mask_1080p, op, 3)
            
            end_time = time.perf_counter()
            avg_time = (end_time - start_time) / 30 * 1000
            
            print(f"  {op}: {avg_time:.2f}ms per frame")
            
            # マスク処理は10ms以下を目標
            self.assertLess(avg_time, 10.0,
                           f"Mask {op} took {avg_time:.2f}ms")
    
    def test_memory_usage(self):
        """メモリ使用量のテスト"""
        process = psutil.Process(os.getpid())
        
        # 初期メモリ使用量
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        engine = self.container.resolve(IEffectEngine)
        engine.add_effect("mosaic", MosaicEffect(), {"block_size": 16})
        
        # 100フレーム処理
        frames = []
        for i in range(100):
            result = engine.apply_effects(self.frame_1080p, self.mask_1080p)
            frames.append(result)
            
            # 10フレームごとにメモリ使用量をチェック
            if (i + 1) % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                print(f"\nMemory after {i+1} frames: {current_memory:.1f}MB "
                      f"(+{memory_increase:.1f}MB)")
        
        # 最終メモリ使用量
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"\nTotal memory increase: {memory_increase:.1f}MB")
        
        # メモリリークがないことを確認（増加が妥当な範囲内）
        # 100フレーム分のバッファを考慮しても1GB以下
        self.assertLess(memory_increase, 1024,
                       f"Memory increased by {memory_increase:.1f}MB")
    
    def test_concurrent_processing(self):
        """並行処理の性能テスト"""
        engine = EffectEngine(max_workers=4)
        engine.add_effect("mosaic", MosaicEffect(), {"block_size": 16})
        
        # 複数フレームの並行処理をシミュレート
        frames = [self.frame_1080p.copy() for _ in range(4)]
        masks = [self.mask_1080p.copy() for _ in range(4)]
        
        start_time = time.perf_counter()
        
        # 並行処理（実際の実装では別スレッドで実行される想定）
        results = []
        for frame, mask in zip(frames, masks):
            result = engine.apply_effects(frame, mask)
            results.append(result)
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        avg_time_per_frame = total_time / len(frames)
        
        print(f"\nConcurrent Processing Performance (4 frames):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average per frame: {avg_time_per_frame:.2f}ms")
        
        # 並行処理でも妥当な時間内に完了
        self.assertLess(total_time, 200.0,
                       f"Concurrent processing took {total_time:.2f}ms")
    
    def test_different_resolutions(self):
        """異なる解像度での性能テスト"""
        engine = self.container.resolve(IEffectEngine)
        engine.add_effect("mosaic", MosaicEffect(), {"block_size": 16})
        
        resolutions = [
            ("480p", (480, 854, 3)),
            ("720p", (720, 1280, 3)),
            ("1080p", (1080, 1920, 3)),
            ("4K", (2160, 3840, 3))
        ]
        
        print("\nPerformance at Different Resolutions:")
        
        for name, shape in resolutions:
            frame = np.random.randint(0, 255, shape, dtype=np.uint8)
            mask = np.random.randint(0, 255, shape[:2], dtype=np.uint8)
            
            # ウォームアップ
            for _ in range(3):
                engine.apply_effects(frame, mask)
            
            # 測定
            start_time = time.perf_counter()
            for _ in range(10):
                result = engine.apply_effects(frame, mask)
            end_time = time.perf_counter()
            
            avg_time = (end_time - start_time) / 10 * 1000
            pixels = shape[0] * shape[1]
            time_per_mpixel = avg_time / (pixels / 1_000_000)
            
            print(f"  {name} ({shape[1]}x{shape[0]}): "
                  f"{avg_time:.2f}ms per frame, "
                  f"{time_per_mpixel:.2f}ms per megapixel")
            
            # 解像度に応じた妥当な処理時間
            if name == "1080p":
                self.assertLess(avg_time, 50.0)  # NFR-1
            elif name == "4K":
                self.assertLess(avg_time, 200.0)  # 4Kは4倍の時間を許容
    
    def test_cpu_vs_gpu_performance(self):
        """CPU vs GPU性能比較テスト（GPUが利用可能な場合）"""
        engine = self.container.resolve(IEffectEngine)
        
        # CPU処理
        engine.set_gpu_enabled(False)
        engine.add_effect("blur", BlurEffect(), {"blur_radius": 21})
        
        start_time = time.perf_counter()
        for _ in range(10):
            result_cpu = engine.apply_effects(self.frame_1080p, self.mask_1080p)
        cpu_time = (time.perf_counter() - start_time) / 10 * 1000
        
        # GPU処理（利用可能な場合）
        engine.clear_effects()
        engine.set_gpu_enabled(True)
        engine.add_effect("blur", BlurEffect(), {"blur_radius": 21})
        
        start_time = time.perf_counter()
        for _ in range(10):
            result_gpu = engine.apply_effects(self.frame_1080p, self.mask_1080p)
        gpu_time = (time.perf_counter() - start_time) / 10 * 1000
        
        print(f"\nCPU vs GPU Performance (1080p):")
        print(f"  CPU: {cpu_time:.2f}ms per frame")
        print(f"  GPU: {gpu_time:.2f}ms per frame")
        
        if gpu_time < cpu_time:
            speedup = cpu_time / gpu_time
            print(f"  GPU speedup: {speedup:.2f}x")


if __name__ == '__main__':
    unittest.main()