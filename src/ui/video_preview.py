#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ビデオプレビューウィジェット

OpenCVベースの動画表示機能を提供。
基本的な再生制御とフレーム表示を実装。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QImage, QPixmap, QPainter, QWheelEvent, QMouseEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

from core.media_io import MediaReader
from core.models import Frame

logger = logging.getLogger(__name__)


class VideoPreviewWidget(QWidget):
    """ビデオプレビューウィジェット
    
    動画の表示と基本的な再生制御を提供。
    """
    
    # シグナル
    frame_changed = pyqtSignal(int)  # フレーム番号が変更された
    playback_started = pyqtSignal()  # 再生開始
    playback_stopped = pyqtSignal()  # 再生停止
    zoom_changed = pyqtSignal(float)  # ズームレベル変更
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        # 状態変数
        self.media_reader: Optional[MediaReader] = None
        self.current_frame_index = 0
        self.is_playing = False
        self.playback_fps = 30.0
        self.zoom_level = 1.0  # 100%
        self.fit_to_window = True
        
        # UIセットアップ
        self._setup_ui()
        
        # 再生タイマー
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_timer)
        
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 表示ラベル
        self.display_label = VideoDisplayLabel(self)
        self.display_label.setSizePolicy(QSizePolicy.Policy.Expanding, 
                                        QSizePolicy.Policy.Expanding)
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("background-color: black;")
        
        # マウスイベントの接続
        self.display_label.mouse_wheel.connect(self._on_mouse_wheel)
        self.display_label.mouse_drag.connect(self._on_mouse_drag)
        
        layout.addWidget(self.display_label)
    
    def load_video(self, filepath: Union[str, Path]) -> bool:
        """動画を読み込み
        
        Args:
            filepath: 動画ファイルパス
            
        Returns:
            成功した場合True
        """
        try:
            # 既存のリーダーをクローズ
            if self.media_reader:
                self.media_reader.close()
            
            # 新しいリーダーを作成
            self.media_reader = MediaReader(filepath)
            self.current_frame_index = 0
            self.playback_fps = self.media_reader.fps
            
            # 最初のフレームを表示
            self._display_frame(0)
            
            logger.info(f"Video loaded: {filepath}")
            logger.info(f"Resolution: {self.media_reader.width}x{self.media_reader.height}")
            logger.info(f"FPS: {self.media_reader.fps}")
            logger.info(f"Frames: {self.media_reader.frame_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load video: {e}")
            return False
    
    def play(self) -> None:
        """再生を開始"""
        if not self.media_reader or self.is_playing:
            return
        
        self.is_playing = True
        interval = int(1000 / self.playback_fps)
        self.playback_timer.start(interval)
        self.playback_started.emit()
        
        logger.debug(f"Playback started at {self.playback_fps} FPS")
    
    def pause(self) -> None:
        """再生を一時停止"""
        if not self.is_playing:
            return
        
        self.is_playing = False
        self.playback_timer.stop()
        self.playback_stopped.emit()
        
        logger.debug("Playback paused")
    
    def stop(self) -> None:
        """再生を停止"""
        self.pause()
        self.seek_to_frame(0)
        
        logger.debug("Playback stopped")
    
    def seek_to_frame(self, frame_index: int) -> None:
        """指定フレームにシーク
        
        Args:
            frame_index: フレームインデックス（0-based）
        """
        if not self.media_reader:
            return
        
        # 範囲チェック
        frame_index = max(0, min(frame_index, self.media_reader.frame_count - 1))
        
        if frame_index != self.current_frame_index:
            self.current_frame_index = frame_index
            self._display_frame(frame_index)
            self.frame_changed.emit(frame_index)
    
    def next_frame(self) -> None:
        """次のフレームへ"""
        if self.media_reader:
            self.seek_to_frame(self.current_frame_index + 1)
    
    def previous_frame(self) -> None:
        """前のフレームへ"""
        if self.media_reader:
            self.seek_to_frame(self.current_frame_index - 1)
    
    def set_playback_speed(self, speed: float) -> None:
        """再生速度を設定
        
        Args:
            speed: 再生速度倍率（1.0が標準速度）
        """
        if not self.media_reader:
            return
        
        self.playback_fps = self.media_reader.fps * speed
        
        # タイマーを再設定
        if self.is_playing:
            self.playback_timer.stop()
            interval = int(1000 / self.playback_fps)
            self.playback_timer.start(interval)
    
    def set_zoom(self, zoom: float) -> None:
        """ズームレベルを設定
        
        Args:
            zoom: ズームレベル（1.0が100%）
        """
        self.zoom_level = max(0.1, min(zoom, 10.0))
        self.fit_to_window = False
        self._update_display()
        self.zoom_changed.emit(self.zoom_level)
    
    def fit_to_window_size(self) -> None:
        """ウィンドウサイズに合わせる"""
        self.fit_to_window = True
        self._update_display()
    
    def _display_frame(self, frame_index: int) -> None:
        """フレームを表示"""
        if not self.media_reader:
            return
        
        frame = self.media_reader.get_frame(frame_index)
        if frame is None:
            return
        
        # RGB画像をQImageに変換
        height, width, channels = frame.shape
        bytes_per_line = channels * width
        
        if channels == 3:
            # RGBをBGRに変換（OpenCV形式）
            image_data = cv2.cvtColor(frame.data, cv2.COLOR_RGB2BGR)
            q_image = QImage(image_data.data, width, height, 
                           bytes_per_line, QImage.Format.Format_BGR888)
        else:
            # グレースケール
            q_image = QImage(frame.data.data, width, height,
                           width, QImage.Format.Format_Grayscale8)
        
        # 表示を更新
        self.display_label.set_image(q_image)
        self._update_display()
    
    def _update_display(self) -> None:
        """表示を更新"""
        if not self.display_label.original_pixmap:
            return
        
        if self.fit_to_window:
            # ウィンドウサイズに合わせる
            self.display_label.fit_to_window()
        else:
            # 指定ズームレベルで表示
            self.display_label.set_zoom(self.zoom_level)
    
    def _on_playback_timer(self) -> None:
        """再生タイマーのコールバック"""
        if not self.media_reader:
            return
        
        # 次のフレームへ
        next_index = self.current_frame_index + 1
        if next_index >= self.media_reader.frame_count:
            # 最後まで再生したら停止
            self.stop()
        else:
            self.seek_to_frame(next_index)
    
    def _on_mouse_wheel(self, delta: int) -> None:
        """マウスホイールイベント"""
        # Ctrlキーが押されている場合はズーム
        modifiers = self.display_label.last_modifiers
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # ズーム
            if delta > 0:
                self.set_zoom(self.zoom_level * 1.1)
            else:
                self.set_zoom(self.zoom_level / 1.1)
        else:
            # フレーム送り
            if delta > 0:
                self.previous_frame()
            else:
                self.next_frame()
    
    def _on_mouse_drag(self, delta: QPoint) -> None:
        """マウスドラッグイベント"""
        # パン操作（将来実装）
        pass
    
    def get_current_frame(self) -> Optional[Frame]:
        """現在のフレームを取得"""
        if self.media_reader:
            return self.media_reader.get_frame(self.current_frame_index)
        return None
    
    def get_frame_count(self) -> int:
        """総フレーム数を取得"""
        if self.media_reader:
            return self.media_reader.frame_count
        return 0


class VideoDisplayLabel(QLabel):
    """ビデオ表示用のカスタムラベル
    
    マウスイベントとズーム機能を追加。
    """
    
    # シグナル
    mouse_wheel = pyqtSignal(int)  # ホイール回転量
    mouse_drag = pyqtSignal(QPoint)  # ドラッグ量
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.original_pixmap: Optional[QPixmap] = None
        self.zoom_level = 1.0
        self.last_mouse_pos = QPoint()
        self.last_modifiers = Qt.KeyboardModifier.NoModifier
        
        # マウストラッキングを有効化
        self.setMouseTracking(True)
    
    def set_image(self, image: QImage) -> None:
        """画像を設定"""
        self.original_pixmap = QPixmap.fromImage(image)
        self.update_display()
    
    def set_zoom(self, zoom: float) -> None:
        """ズームレベルを設定"""
        self.zoom_level = zoom
        self.update_display()
    
    def fit_to_window(self) -> None:
        """ウィンドウサイズに合わせる"""
        if not self.original_pixmap:
            return
        
        # アスペクト比を保持してスケール
        self.setPixmap(self.original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
    
    def update_display(self) -> None:
        """表示を更新"""
        if not self.original_pixmap:
            return
        
        # ズームレベルに応じてスケール
        new_size = self.original_pixmap.size() * self.zoom_level
        scaled_pixmap = self.original_pixmap.scaled(
            new_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """マウスホイールイベント"""
        self.last_modifiers = event.modifiers()
        delta = event.angleDelta().y()
        self.mouse_wheel.emit(delta)
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """マウスプレスイベント"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """マウス移動イベント"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.pos() - self.last_mouse_pos
            self.mouse_drag.emit(delta)
            self.last_mouse_pos = event.pos()
        super().mouseMoveEvent(event)