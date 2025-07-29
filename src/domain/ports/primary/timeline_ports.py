#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タイムラインポート定義

タイムラインコンポーネントのインターフェース。
フレーム単位での表示、ズーム、状態管理などを定義。
"""
from typing import Protocol, List, Optional, Dict, Any, Callable, Tuple
from enum import Enum
from datetime import timedelta


class FrameStatus(Enum):
    """フレームの処理状態"""
    UNPROCESSED = "unprocessed"    # 未処理
    UNCONFIRMED = "unconfirmed"    # 未確認
    CONFIRMED = "confirmed"         # 確認済み
    EDITED = "edited"              # 編集済み
    ALERT = "alert"                # アラート有り


class TimeUnit(Enum):
    """時間単位"""
    FRAMES = "frames"
    SECONDS = "seconds"
    TIMECODE = "timecode"


class ITimelineController(Protocol):
    """
    タイムラインコントローラインターフェース
    
    タイムラインの表示、操作、状態管理を行う。
    """
    
    # タイムライン情報
    def get_total_frames(self) -> int:
        """総フレーム数を取得"""
        ...
    
    def get_fps(self) -> float:
        """フレームレートを取得"""
        ...
    
    def get_duration(self) -> timedelta:
        """総時間を取得"""
        ...
    
    # 現在位置管理
    def get_current_frame(self) -> int:
        """現在のフレーム番号を取得"""
        ...
    
    def set_current_frame(self, frame_index: int) -> None:
        """
        現在のフレームを設定
        
        Args:
            frame_index: フレーム番号（0-based）
        """
        ...
    
    def get_current_time(self) -> timedelta:
        """現在の時間位置を取得"""
        ...
    
    def set_current_time(self, time: timedelta) -> None:
        """現在の時間位置を設定"""
        ...
    
    # ズーム・表示制御
    def get_zoom_level(self) -> float:
        """
        ズームレベルを取得
        
        Returns:
            ズームレベル（1.0が標準）
        """
        ...
    
    def set_zoom_level(self, zoom: float) -> None:
        """
        ズームレベルを設定
        
        Args:
            zoom: ズームレベル（0.1-10.0）
        """
        ...
    
    def get_visible_range(self) -> Tuple[int, int]:
        """
        表示中のフレーム範囲を取得
        
        Returns:
            (start_frame, end_frame)のタプル
        """
        ...
    
    def set_visible_range(self, start: int, end: int) -> None:
        """表示範囲を設定"""
        ...
    
    def fit_to_window(self) -> None:
        """ウィンドウサイズに合わせて表示"""
        ...
    
    # 時間単位
    def get_time_unit(self) -> TimeUnit:
        """現在の時間単位を取得"""
        ...
    
    def set_time_unit(self, unit: TimeUnit) -> None:
        """時間単位を設定"""
        ...
    
    # フレーム状態管理
    def get_frame_status(self, frame_index: int) -> FrameStatus:
        """
        フレームの状態を取得
        
        Args:
            frame_index: フレーム番号
            
        Returns:
            フレーム状態
        """
        ...
    
    def set_frame_status(self, frame_index: int, status: FrameStatus) -> None:
        """フレーム状態を設定"""
        ...
    
    def get_frame_statuses(self, start: int, end: int) -> Dict[int, FrameStatus]:
        """
        範囲内のフレーム状態を取得
        
        Args:
            start: 開始フレーム
            end: 終了フレーム
            
        Returns:
            フレーム番号→状態のマッピング
        """
        ...
    
    # アラート管理
    def get_alerts(self, frame_index: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        アラートを取得
        
        Args:
            frame_index: 特定フレームのアラートのみ取得（Noneの場合は全て）
            
        Returns:
            アラートDTOのリスト
        """
        ...
    
    def add_alert(self, alert_data: Dict[str, Any]) -> None:
        """アラートを追加"""
        ...
    
    def clear_alerts(self, frame_index: Optional[int] = None) -> None:
        """アラートをクリア"""
        ...
    
    # スクラブ操作
    def start_scrubbing(self) -> None:
        """スクラブ開始"""
        ...
    
    def update_scrub_position(self, frame_index: int) -> None:
        """
        スクラブ位置を更新
        
        Args:
            frame_index: スクラブ中のフレーム番号
        """
        ...
    
    def end_scrubbing(self) -> None:
        """スクラブ終了"""
        ...
    
    def is_scrubbing(self) -> bool:
        """スクラブ中かどうか"""
        ...
    
    # マーカー管理
    def add_marker(self, frame_index: int, label: str, color: Optional[str] = None) -> str:
        """
        マーカーを追加
        
        Args:
            frame_index: フレーム番号
            label: マーカーラベル
            color: マーカー色（オプション）
            
        Returns:
            マーカーID
        """
        ...
    
    def remove_marker(self, marker_id: str) -> None:
        """マーカーを削除"""
        ...
    
    def get_markers(self) -> List[Dict[str, Any]]:
        """全マーカーを取得"""
        ...
    
    # イベントハンドラ
    def on_frame_changed(self, callback: Callable[[int], None]) -> None:
        """フレーム変更イベントハンドラを登録"""
        ...
    
    def on_zoom_changed(self, callback: Callable[[float], None]) -> None:
        """ズーム変更イベントハンドラを登録"""
        ...
    
    def on_scrub(self, callback: Callable[[int], None]) -> None:
        """スクラブイベントハンドラを登録"""
        ...


class ITimelineRenderer(Protocol):
    """
    タイムラインレンダラインターフェース
    
    タイムラインの描画を担当。
    """
    
    def render(self, visible_range: Tuple[int, int], zoom_level: float) -> None:
        """
        タイムラインを描画
        
        Args:
            visible_range: 表示範囲
            zoom_level: ズームレベル
        """
        ...
    
    def render_frame_status(self, frame_index: int, status: FrameStatus) -> None:
        """フレーム状態を描画"""
        ...
    
    def render_playhead(self, frame_index: int) -> None:
        """再生ヘッドを描画"""
        ...
    
    def render_markers(self, markers: List[Dict[str, Any]]) -> None:
        """マーカーを描画"""
        ...
    
    def render_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """アラートを描画"""
        ...
    
    def render_timecode(self, frame_index: int, timecode: str) -> None:
        """タイムコードを描画"""
        ...
    
    def get_frame_at_position(self, x: int, y: int) -> Optional[int]:
        """
        座標からフレーム番号を取得
        
        Args:
            x: X座標
            y: Y座標
            
        Returns:
            フレーム番号（該当なしの場合None）
        """
        ...