#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスク付きビデオウィジェット

ビデオプレビューとマスクオーバーレイを統合したウィジェット。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtWidgets import QWidget, QStackedLayout

from ui.video_preview import VideoPreviewWidget
from ui.mask_overlay_widget import MaskOverlayWidget
from domain.dto.frame_dto import FrameDTO
from domain.dto.mask_dto import MaskDTO, MaskOverlaySettingsDTO
from core.models import Frame

logger = logging.getLogger(__name__)


class VideoWithMaskWidget(QWidget):
    """マスク付きビデオウィジェット
    
    ビデオプレビューとマスクオーバーレイを統合。
    """
    
    # シグナル（VideoPreviewWidgetから転送）
    frame_changed = pyqtSignal(int)
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    zoom_changed = pyqtSignal(float)
    
    # マスク関連シグナル
    mask_clicked = pyqtSignal(int, QPoint)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 現在のデータ
        self.current_mask_dto: Optional[MaskDTO] = None
        self.overlay_settings = MaskOverlaySettingsDTO()
        
        # UIセットアップ
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        # スタックレイアウトで重ねる
        layout = QStackedLayout(self)
        layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # ビデオプレビュー（下層）
        self.video_preview = VideoPreviewWidget()
        layout.addWidget(self.video_preview)
        
        # マスクオーバーレイ（上層）
        self.mask_overlay = MaskOverlayWidget()
        self.mask_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        layout.addWidget(self.mask_overlay)
        
        # シグナル接続
        self.video_preview.frame_changed.connect(self._on_frame_changed)
        self.video_preview.playback_started.connect(self.playback_started)
        self.video_preview.playback_stopped.connect(self.playback_stopped)
        self.video_preview.zoom_changed.connect(self.zoom_changed)
        
        self.mask_overlay.mask_clicked.connect(self.mask_clicked)
    
    # VideoPreviewWidgetのプロキシメソッド
    def load_video(self, filepath: Union[str, Path]) -> bool:
        """動画を読み込み"""
        return self.video_preview.load_video(filepath)
    
    def play(self) -> None:
        """再生を開始"""
        self.video_preview.play()
    
    def pause(self) -> None:
        """再生を一時停止"""
        self.video_preview.pause()
    
    def stop(self) -> None:
        """再生を停止"""
        self.video_preview.stop()
    
    def seek_to_frame(self, frame_index: int) -> None:
        """指定フレームにシーク"""
        self.video_preview.seek_to_frame(frame_index)
    
    def next_frame(self) -> None:
        """次のフレームへ"""
        self.video_preview.next_frame()
    
    def previous_frame(self) -> None:
        """前のフレームへ"""
        self.video_preview.previous_frame()
    
    def set_playback_speed(self, speed: float) -> None:
        """再生速度を設定"""
        self.video_preview.set_playback_speed(speed)
    
    def set_zoom(self, zoom: float) -> None:
        """ズームレベルを設定"""
        self.video_preview.set_zoom(zoom)
    
    def fit_to_window_size(self) -> None:
        """ウィンドウサイズに合わせる"""
        self.video_preview.fit_to_window_size()
    
    def get_current_frame(self) -> Optional[Frame]:
        """現在のフレームを取得"""
        return self.video_preview.get_current_frame()
    
    def get_frame_count(self) -> int:
        """総フレーム数を取得"""
        return self.video_preview.get_frame_count()
    
    def get_fps(self) -> float:
        """FPSを取得"""
        if self.video_preview.media_reader:
            return self.video_preview.media_reader.fps
        return 30.0
    
    @property
    def media_reader(self):
        """MediaReaderへのアクセス"""
        return self.video_preview.media_reader
    
    @property
    def zoom_level(self) -> float:
        """現在のズームレベル"""
        return self.video_preview.zoom_level
    
    # マスク関連メソッド
    def set_mask(self, mask_dto: Optional[MaskDTO]) -> None:
        """マスクを設定"""
        self.current_mask_dto = mask_dto
        self.mask_overlay.set_mask(mask_dto)
    
    def set_overlay_settings(self, settings: MaskOverlaySettingsDTO) -> None:
        """オーバーレイ設定を更新"""
        self.overlay_settings = settings
        self.mask_overlay.set_overlay_settings(settings)
    
    def toggle_mask_visibility(self, mask_id: int, visible: bool) -> None:
        """特定マスクの表示/非表示を切り替え"""
        self.mask_overlay.toggle_mask_visibility(mask_id, visible)
    
    def set_mask_color(self, mask_id: int, color: str) -> None:
        """特定マスクの色を設定"""
        self.mask_overlay.set_mask_color(mask_id, color)
    
    def get_visible_mask_ids(self) -> list[int]:
        """表示中のマスクIDリストを取得"""
        return self.mask_overlay.get_visible_mask_ids()
    
    def _on_frame_changed(self, frame_index: int) -> None:
        """フレームが変更された時"""
        # フレームデータを取得してオーバーレイに設定
        frame = self.video_preview.get_current_frame()
        if frame:
            # FrameDTOに変換
            frame_dto = FrameDTO(
                index=frame_index,
                pts=frame.pts if hasattr(frame, 'pts') else frame_index,
                dts=frame.dts if hasattr(frame, 'dts') else None,
                data=frame.data,
                width=frame.data.shape[1],
                height=frame.data.shape[0],
                timecode=None
            )
            self.mask_overlay.set_frame(frame_dto)
        
        # シグナルを転送
        self.frame_changed.emit(frame_index)