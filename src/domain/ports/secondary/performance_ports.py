#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
パフォーマンス最適化ポート

UIやデータ処理のパフォーマンス最適化に関するインターフェースを定義。
Hexagonal Architectureに従い、実装の詳細から独立したプロトコルを提供。
"""
from typing import Protocol, Optional, Dict, Any, Callable


class IFrameThrottleService(Protocol):
    """フレーム更新スロットリングサービスのインターフェース
    
    UIのフレーム更新頻度を制御し、パフォーマンスを最適化。
    """
    
    def should_update(self, frame_index: int, is_playing: bool = False) -> bool:
        """フレーム更新を行うべきかを判定
        
        Args:
            frame_index: フレーム番号
            is_playing: 再生中かどうか
            
        Returns:
            更新すべきならTrue
        """
        ...
    
    def get_pending_frame(self) -> Optional[int]:
        """保留中のフレームを取得
        
        Returns:
            保留中のフレーム番号（なければNone）
        """
        ...
    
    def set_fps_limit(self, fps_limit: int) -> None:
        """FPS制限を設定
        
        Args:
            fps_limit: 最大FPS
        """
        ...
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得
        
        Returns:
            統計情報の辞書
        """
        ...
    
    def reset_stats(self) -> None:
        """統計をリセット"""
        ...


class IUIUpdateOptimizer(Protocol):
    """UI更新最適化サービスのインターフェース
    
    再生中のUI更新を最適化し、各コンポーネントの更新頻度を制御。
    """
    
    def set_playing_state(self, is_playing: bool) -> None:
        """再生状態を設定
        
        Args:
            is_playing: 再生中かどうか
        """
        ...
    
    def should_update_component(self, component_name: str, frame_index: int) -> bool:
        """特定のコンポーネントを更新すべきかを判定
        
        Args:
            component_name: コンポーネント名
            frame_index: フレーム番号
            
        Returns:
            更新すべきならTrue
        """
        ...
    
    def set_update_interval(self, component_name: str, interval: int) -> None:
        """コンポーネントの更新間隔を設定
        
        Args:
            component_name: コンポーネント名
            interval: 更新間隔（フレーム数）
        """
        ...


class IPerformanceMonitor(Protocol):
    """パフォーマンスモニタリングサービスのインターフェース
    
    アプリケーション全体のパフォーマンスをモニタリング。
    """
    
    def start_operation(self, operation_name: str) -> None:
        """操作の開始を記録
        
        Args:
            operation_name: 操作名
        """
        ...
    
    def end_operation(self, operation_name: str) -> None:
        """操作の終了を記録
        
        Args:
            operation_name: 操作名
        """
        ...
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """特定操作の統計を取得
        
        Args:
            operation_name: 操作名
            
        Returns:
            統計情報（平均時間、最大時間、呼び出し回数等）
        """
        ...
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """全操作の統計を取得
        
        Returns:
            操作名をキーとした統計情報の辞書
        """
        ...
    
    def reset_stats(self, operation_name: Optional[str] = None) -> None:
        """統計をリセット
        
        Args:
            operation_name: リセットする操作名（Noneの場合は全て）
        """
        ...


class IMemoryOptimizer(Protocol):
    """メモリ最適化サービスのインターフェース
    
    メモリ使用量を最適化し、ガベージコレクションを制御。
    """
    
    def optimize_memory(self) -> None:
        """メモリ最適化を実行"""
        ...
    
    def get_memory_usage(self) -> Dict[str, int]:
        """現在のメモリ使用量を取得
        
        Returns:
            各種メモリ情報（使用量、利用可能量等）のバイト数
        """
        ...
    
    def set_memory_limit(self, limit_mb: int) -> None:
        """メモリ使用量の上限を設定
        
        Args:
            limit_mb: メモリ上限（MB）
        """
        ...
    
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """メモリクリーンアップ時のコールバックを登録
        
        Args:
            callback: クリーンアップ時に呼ばれる関数
        """
        ...