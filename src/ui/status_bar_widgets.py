#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ステータスバーウィジェット

カスタムステータスバーウィジェットのコレクション。
より洗練されたステータス表示を提供。
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QProgressBar

from .i18n import tr
from .theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class AnimatedProgressBar(QWidget):
    """アニメーション付きプログレスバー
    
    スムーズなアニメーションと視覚的フィードバックを提供。
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self._progress = 0.0
        # プロパティを作成
        self.setProperty("progress", 0.0)
        
        self._animation = QPropertyAnimation(self, b"progress")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # テーマカラー
        theme = get_theme_manager()
        self.progress_color = QColor(theme.color_scheme.primary)
        self.background_color = QColor(theme.color_scheme.surface_light)
    
    @pyqtProperty(float)
    def progress(self) -> float:
        return self._progress
    
    @progress.setter
    def progress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self.update()
    
    def set_progress(self, value: float, animated: bool = True) -> None:
        """プログレスを設定
        
        Args:
            value: 0.0～1.0の値
            animated: アニメーションを使用するか
        """
        if animated:
            self._animation.setStartValue(self._progress)
            self._animation.setEndValue(value)
            self._animation.start()
        else:
            self.progress = value
    
    def paintEvent(self, event):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        painter.fillRect(self.rect(), self.background_color)
        
        # プログレス
        if self._progress > 0:
            progress_rect = QRect(
                0, 0,
                int(self.width() * self._progress),
                self.height()
            )
            
            # グラデーション効果
            gradient = QLinearGradient(0, 0, progress_rect.width(), 0)
            gradient.setColorAt(0, self.progress_color.darker(110))
            gradient.setColorAt(0.5, self.progress_color)
            gradient.setColorAt(1, self.progress_color.darker(110))
            
            painter.fillRect(progress_rect, gradient)


class ResourceMonitor(QWidget):
    """リソースモニターウィジェット
    
    CPU、メモリ、GPU使用率を視覚的に表示。
    """
    
    def __init__(self, resource_type: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.resource_type = resource_type
        self._value = 0
        self._max_value = 100
        
        self._setup_ui()
        
        # テーマカラー
        self._update_colors()
    
    def _setup_ui(self):
        """UIをセットアップ"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        # ラベル
        self.label = QLabel()
        self.label.setMinimumWidth(40)
        layout.addWidget(self.label)
        
        # 値表示
        self.value_label = QLabel("0%")
        self.value_label.setMinimumWidth(40)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.value_label)
        
        # リソースタイプに応じたラベル設定
        if self.resource_type == "cpu":
            self.label.setText("CPU:")
        elif self.resource_type == "memory":
            self.label.setText("RAM:")
        elif self.resource_type == "gpu":
            self.label.setText("GPU:")
        
        self.setFixedHeight(20)
        self.setMinimumWidth(100)
    
    def _update_colors(self):
        """テーマカラーを更新"""
        theme = get_theme_manager()
        
        # 使用率に応じた色分け
        if self._value < 60:
            color = theme.color_scheme.success
        elif self._value < 80:
            color = theme.color_scheme.warning
        else:
            color = theme.color_scheme.error
        
        self.value_label.setStyleSheet(f"color: {color};")
    
    def set_value(self, value: int):
        """値を設定
        
        Args:
            value: 使用率（0-100）
        """
        self._value = max(0, min(100, value))
        self.value_label.setText(f"{self._value}%")
        self._update_colors()
        self.update()
    
    def paintEvent(self, event):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景バー
        theme = get_theme_manager()
        bg_rect = QRect(
            self.label.width() + 8,
            self.height() - 4,
            self.width() - self.label.width() - self.value_label.width() - 16,
            3
        )
        painter.fillRect(bg_rect, QColor(theme.color_scheme.surface_light))
        
        # 値バー
        if self._value > 0:
            value_width = int(bg_rect.width() * (self._value / 100))
            value_rect = QRect(bg_rect.x(), bg_rect.y(), value_width, bg_rect.height())
            
            # 色分け
            if self._value < 60:
                color = QColor(theme.color_scheme.success)
            elif self._value < 80:
                color = QColor(theme.color_scheme.warning)
            else:
                color = QColor(theme.color_scheme.error)
            
            painter.fillRect(value_rect, color)


class StatusMessage(QLabel):
    """ステータスメッセージウィジェット
    
    アイコン付きステータスメッセージを表示。
    自動的にフェードアウトする機能付き。
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._fade_out)
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(500)
        self._fade_animation.finished.connect(self.hide)
    
    def show_message(self, text: str, message_type: str = "info", duration: int = 3000):
        """メッセージを表示
        
        Args:
            text: メッセージテキスト
            message_type: メッセージタイプ（info, success, warning, error）
            duration: 表示時間（ミリ秒）。0の場合は自動的に消えない
        """
        theme = get_theme_manager()
        
        # メッセージタイプに応じた色設定
        colors = {
            "info": theme.color_scheme.info,
            "success": theme.color_scheme.success,
            "warning": theme.color_scheme.warning,
            "error": theme.color_scheme.error
        }
        color = colors.get(message_type, theme.color_scheme.info)
        
        # スタイル設定
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                padding: 4px 8px;
                background-color: {theme.color_scheme.surface};
                border: 1px solid {color};
                border-radius: 4px;
            }}
        """)
        
        self.setText(text)
        self.show()
        self.setWindowOpacity(1.0)
        
        # タイマー設定
        if duration > 0:
            self._timer.stop()
            self._timer.start(duration)
    
    def _fade_out(self):
        """フェードアウト"""
        self._timer.stop()
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.start()


class FrameCounter(QWidget):
    """フレームカウンターウィジェット
    
    現在のフレーム番号と総フレーム数を表示。
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_frame = 0
        self._total_frames = 0
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UIをセットアップ"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        # アイコン（フレームインジケーター）
        self.icon_label = QLabel("🎬")
        layout.addWidget(self.icon_label)
        
        # フレーム表示
        self.frame_label = QLabel("0 / 0")
        self.frame_label.setMinimumWidth(100)
        layout.addWidget(self.frame_label)
    
    def set_frame_info(self, current: int, total: int):
        """フレーム情報を設定
        
        Args:
            current: 現在のフレーム番号
            total: 総フレーム数
        """
        self._current_frame = current
        self._total_frames = total
        
        # フォーマット済みテキスト
        self.frame_label.setText(f"{current:,} / {total:,}")
        
        # ツールチップ
        if total > 0:
            percentage = (current / total) * 100
            self.setToolTip(f"Frame {current} of {total} ({percentage:.1f}%)")


class ProcessingIndicator(QWidget):
    """処理中インジケーター
    
    処理中であることを示すアニメーション付きインジケーター。
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._is_processing = False
        
        # テーマカラー
        theme = get_theme_manager()
        self.color = QColor(theme.color_scheme.primary)
    
    def start_processing(self):
        """処理開始"""
        self._is_processing = True
        self._timer.start(50)  # 50ms間隔で更新
        self.show()
    
    def stop_processing(self):
        """処理停止"""
        self._is_processing = False
        self._timer.stop()
        self.hide()
    
    def _rotate(self):
        """回転アニメーション"""
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """描画イベント"""
        if not self._is_processing:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 中心点
        center = self.rect().center()
        
        # 回転する円弧を描画
        pen = QPen(self.color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # 円弧の描画
        radius = 8
        rect = QRect(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2
        )
        
        start_angle = self._angle * 16  # QPainterは1/16度単位
        span_angle = 270 * 16  # 270度の円弧
        
        painter.drawArc(rect, start_angle, span_angle)