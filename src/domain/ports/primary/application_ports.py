#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリケーション制御ポート定義

UIからアプリケーションロジックへのアクセスインターフェース。
"""
from typing import Protocol, Optional, Dict, Any, List, Callable, Tuple
from pathlib import Path
from enum import Enum


class PlaybackState(Enum):
    """再生状態"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class ViewMode(Enum):
    """表示モード"""
    SINGLE = "single"
    DUAL = "dual"
    TRIPLE = "triple"


class IApplicationController(Protocol):
    """アプリケーションコントローラインターフェース"""
    
    # プロジェクト管理
    def new_project(self, name: str = "Untitled Project") -> Dict[str, Any]:
        """新規プロジェクト作成"""
        ...
    
    def open_project(self, path: Path) -> Dict[str, Any]:
        """プロジェクトを開く"""
        ...
    
    def save_project(self, path: Optional[Path] = None) -> bool:
        """プロジェクトを保存"""
        ...
    
    def close_project(self) -> bool:
        """プロジェクトを閉じる"""
        ...
    
    def get_current_project(self) -> Optional[Dict[str, Any]]:
        """現在のプロジェクトを取得"""
        ...
    
    # ビデオ管理
    def load_video(self, path: Path) -> Dict[str, Any]:
        """ビデオを読み込む"""
        ...
    
    def unload_video(self) -> bool:
        """ビデオをアンロード"""
        ...
    
    def get_video_metadata(self) -> Optional[Dict[str, Any]]:
        """ビデオメタデータを取得"""
        ...
    
    # マスク管理
    def load_masks(self, path: Path) -> bool:
        """マスクシーケンスを読み込む"""
        ...
    
    def save_masks(self, path: Path) -> bool:
        """マスクシーケンスを保存"""
        ...
    
    def get_mask_at_frame(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """指定フレームのマスクを取得"""
        ...
    
    def update_mask_at_frame(self, frame_index: int, mask_data: Dict[str, Any]) -> bool:
        """指定フレームのマスクを更新"""
        ...
    
    # 再生制御
    def play(self) -> bool:
        """再生開始"""
        ...
    
    def pause(self) -> bool:
        """一時停止"""
        ...
    
    def stop(self) -> bool:
        """停止"""
        ...
    
    def seek(self, frame_index: int) -> bool:
        """指定フレームにシーク"""
        ...
    
    def get_playback_state(self) -> PlaybackState:
        """再生状態を取得"""
        ...
    
    def set_playback_speed(self, speed: float) -> bool:
        """再生速度を設定"""
        ...
    
    # エフェクト管理
    def apply_effect(
        self,
        effect_type: str,
        parameters: Dict[str, Any],
        frame_range: Optional[Tuple[int, int]] = None,
        object_ids: Optional[List[int]] = None
    ) -> bool:
        """エフェクトを適用"""
        ...
    
    def preview_effect(
        self,
        effect_type: str,
        parameters: Dict[str, Any],
        frame_index: int
    ) -> Optional[Dict[str, Any]]:
        """エフェクトをプレビュー"""
        ...
    
    # エクスポート
    def export_video(
        self,
        path: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """ビデオをエクスポート"""
        ...
    
    # Undo/Redo
    def undo(self) -> bool:
        """アンドゥ"""
        ...
    
    def redo(self) -> bool:
        """リドゥ"""
        ...
    
    def can_undo(self) -> bool:
        """アンドゥ可能か"""
        ...
    
    def can_redo(self) -> bool:
        """リドゥ可能か"""
        ...


class IVideoViewer(Protocol):
    """ビデオビューアインターフェース"""
    
    def set_frame(self, frame_data: Dict[str, Any]) -> None:
        """フレームを表示"""
        ...
    
    def set_mask_overlay(self, mask_data: Optional[Dict[str, Any]]) -> None:
        """マスクオーバーレイを設定"""
        ...
    
    def set_mask_opacity(self, opacity: float) -> None:
        """マスクの不透明度を設定（0.0-1.0）"""
        ...
    
    def set_view_mode(self, mode: ViewMode) -> None:
        """表示モードを設定"""
        ...
    
    def set_zoom(self, zoom: float) -> None:
        """ズーム倍率を設定"""
        ...
    
    def fit_to_window(self) -> None:
        """ウィンドウに合わせる"""
        ...
    
    def refresh(self) -> None:
        """表示を更新"""
        ...