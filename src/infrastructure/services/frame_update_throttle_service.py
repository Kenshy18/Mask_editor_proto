#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フレーム更新スロットリングサービス

UIのフレーム更新頻度を制御する独立したサービス
"""
import time
from typing import Optional, Dict, Any, List
from collections import deque

import logging
logger = logging.getLogger(__name__)


class FrameUpdateThrottleService:
    """フレーム更新のスロットリングサービス
    
    設計原則に従い、UIロジックとは独立したサービスとして実装。
    Single Responsibility Principle (SRP) を遵守。
    """
    
    def __init__(self, fps_limit: int = 30):
        """初期化
        
        Args:
            fps_limit: 最大FPS（フレーム/秒）
        """
        self._fps_limit = fps_limit
        self._min_interval_ms = 1000.0 / fps_limit
        self._last_update_time = 0
        self._pending_frame: Optional[int] = None
        
        # パフォーマンス統計
        self._frame_times = deque(maxlen=100)
        self._dropped_frames = 0
        self._total_frames = 0
    
    def should_update(self, frame_index: int, is_playing: bool = False) -> bool:
        """フレーム更新を行うべきかを判定
        
        Args:
            frame_index: フレーム番号
            is_playing: 再生中かどうか
            
        Returns:
            更新すべきならTrue
        """
        current_time = time.time() * 1000  # ms
        self._total_frames += 1
        
        # 再生中でない場合は常に更新
        if not is_playing:
            self._last_update_time = current_time
            return True
        
        # 前回の更新からの経過時間
        elapsed = current_time - self._last_update_time
        
        if elapsed >= self._min_interval_ms:
            # 更新可能
            self._last_update_time = current_time
            self._frame_times.append(elapsed)
            return True
        else:
            # スロットリング
            self._pending_frame = frame_index
            self._dropped_frames += 1
            return False
    
    def get_pending_frame(self) -> Optional[int]:
        """保留中のフレームを取得
        
        Returns:
            保留中のフレーム番号（なければNone）
        """
        frame = self._pending_frame
        self._pending_frame = None
        return frame
    
    def set_fps_limit(self, fps_limit: int) -> None:
        """FPS制限を設定
        
        Args:
            fps_limit: 最大FPS
        """
        self._fps_limit = fps_limit
        self._min_interval_ms = 1000.0 / fps_limit
        logger.info(f"FPS limit set to {fps_limit} ({self._min_interval_ms:.1f}ms interval)")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得
        
        Returns:
            統計情報の辞書
        """
        if not self._frame_times:
            return {
                "fps_limit": self._fps_limit,
                "avg_interval_ms": 0,
                "max_interval_ms": 0,
                "min_interval_ms": 0,
                "dropped_frames": self._dropped_frames,
                "total_frames": self._total_frames,
                "drop_rate": 0
            }
        
        avg_interval = sum(self._frame_times) / len(self._frame_times)
        drop_rate = self._dropped_frames / self._total_frames if self._total_frames > 0 else 0
        
        return {
            "fps_limit": self._fps_limit,
            "avg_interval_ms": avg_interval,
            "max_interval_ms": max(self._frame_times),
            "min_interval_ms": min(self._frame_times),
            "dropped_frames": self._dropped_frames,
            "total_frames": self._total_frames,
            "drop_rate": drop_rate,
            "effective_fps": 1000.0 / avg_interval if avg_interval > 0 else 0
        }
    
    def reset_stats(self) -> None:
        """統計をリセット"""
        self._frame_times.clear()
        self._dropped_frames = 0
        self._total_frames = 0


class UIUpdateOptimizer:
    """UI更新最適化サービス
    
    再生中のUI更新を最適化する独立したサービス。
    """
    
    def __init__(self):
        """初期化"""
        self._is_playing = False
        self._update_intervals = {
            "timeline": 10,  # タイムラインは10フレームごと
            "mask_display": 1,  # マスク表示は毎フレーム
            "id_management": 30,  # ID管理は30フレームごと
            "effect_panel": 30,  # エフェクトパネルは30フレームごと
        }
        self._frame_counters = {}
    
    def set_playing_state(self, is_playing: bool) -> None:
        """再生状態を設定
        
        Args:
            is_playing: 再生中かどうか
        """
        self._is_playing = is_playing
        if not is_playing:
            # 再生停止時はカウンターをリセット
            self._frame_counters.clear()
    
    def should_update_component(self, component_name: str, frame_index: int) -> bool:
        """特定のコンポーネントを更新すべきかを判定
        
        Args:
            component_name: コンポーネント名
            frame_index: フレーム番号
            
        Returns:
            更新すべきならTrue
        """
        # 再生中でない場合は常に更新
        if not self._is_playing:
            return True
        
        # コンポーネントの更新間隔を取得
        interval = self._update_intervals.get(component_name, 1)
        
        # 最後の更新フレームを取得
        last_update = self._frame_counters.get(component_name, -interval)
        
        # 更新判定
        if frame_index - last_update >= interval:
            self._frame_counters[component_name] = frame_index
            return True
        
        return False
    
    def set_update_interval(self, component_name: str, interval: int) -> None:
        """コンポーネントの更新間隔を設定
        
        Args:
            component_name: コンポーネント名
            interval: 更新間隔（フレーム数）
        """
        self._update_intervals[component_name] = interval
        logger.debug(f"Update interval for {component_name} set to {interval} frames")