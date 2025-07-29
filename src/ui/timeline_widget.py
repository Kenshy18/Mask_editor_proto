#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タイムラインウィジェット

フレーム単位での表示、ズーム、スクラブ機能を提供するタイムラインUI。
"""
import math
from typing import Optional, Dict, List, Tuple, Callable
from datetime import timedelta

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel, QToolButton, QComboBox
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QWheelEvent, QPaintEvent

from domain.dto.timeline_dto import TimelineStateDTO, FrameStatus, TimelineMarkerDTO


class TimelineRuler(QWidget):
    """タイムラインルーラー（目盛り表示）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.fps = 30.0
        self.zoom_level = 1.0
        self.visible_start = 0
        self.visible_end = 100
        self.time_unit = "frames"  # frames, seconds, timecode
        
        # スタイル設定
        self.background_color = QColor(40, 40, 40)
        self.text_color = QColor(200, 200, 200)
        self.line_color = QColor(100, 100, 100)
        self.major_line_color = QColor(150, 150, 150)
    
    def set_timeline_info(self, fps: float, visible_start: int, visible_end: int, zoom_level: float):
        """タイムライン情報を設定"""
        self.fps = fps
        self.visible_start = visible_start
        self.visible_end = visible_end
        self.zoom_level = zoom_level
        self.update()
    
    def set_time_unit(self, unit: str):
        """時間単位を設定"""
        self.time_unit = unit
        self.update()
    
    def paintEvent(self, event: QPaintEvent):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        painter.fillRect(self.rect(), self.background_color)
        
        # フレーム幅の計算
        total_frames = self.visible_end - self.visible_start
        if total_frames <= 0:
            return
        
        frame_width = self.width() / total_frames
        
        # 目盛りの間隔を決定
        if self.time_unit == "frames":
            interval = self._calculate_frame_interval(frame_width)
        elif self.time_unit == "seconds":
            interval = self._calculate_second_interval(frame_width)
        else:  # timecode
            interval = self._calculate_timecode_interval(frame_width)
        
        # 目盛りを描画 - アプリケーションのデフォルトフォントを使用（日本語対応）
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        
        for i in range(self.visible_start, self.visible_end + 1, interval):
            x = (i - self.visible_start) * frame_width
            
            # 主目盛り
            painter.setPen(QPen(self.major_line_color, 1))
            painter.drawLine(int(x), 15, int(x), 30)
            
            # ラベル
            painter.setPen(QPen(self.text_color, 1))
            label = self._format_label(i)
            painter.drawText(int(x - 20), 12, 40, 15, Qt.AlignmentFlag.AlignCenter, label)
    
    def _calculate_frame_interval(self, frame_width: float) -> int:
        """フレーム単位の目盛り間隔を計算"""
        min_pixel_spacing = 50
        frames_per_mark = max(1, int(min_pixel_spacing / frame_width))
        
        # きりの良い数値に調整
        if frames_per_mark <= 5:
            return 5
        elif frames_per_mark <= 10:
            return 10
        elif frames_per_mark <= 25:
            return 25
        elif frames_per_mark <= 50:
            return 50
        else:
            return 100 * ((frames_per_mark + 99) // 100)
    
    def _calculate_second_interval(self, frame_width: float) -> int:
        """秒単位の目盛り間隔を計算"""
        frames_per_second = int(self.fps)
        return frames_per_second * max(1, int(50 / (frame_width * frames_per_second)))
    
    def _calculate_timecode_interval(self, frame_width: float) -> int:
        """タイムコード単位の目盛り間隔を計算"""
        # 1秒単位で表示
        return int(self.fps)
    
    def _format_label(self, frame: int) -> str:
        """ラベルをフォーマット"""
        if self.time_unit == "frames":
            return str(frame)
        elif self.time_unit == "seconds":
            seconds = frame / self.fps
            return f"{seconds:.1f}s"
        else:  # timecode
            total_seconds = frame / self.fps
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            frames = int((total_seconds % 1) * self.fps)
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"


class TimelineTrack(QWidget):
    """タイムライントラック（フレーム状態表示）"""
    
    # シグナル
    frameClicked = pyqtSignal(int)  # フレームクリック
    scrubStarted = pyqtSignal()     # スクラブ開始
    scrubMoved = pyqtSignal(int)    # スクラブ移動
    scrubEnded = pyqtSignal()       # スクラブ終了
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setMouseTracking(True)
        
        # タイムライン情報
        self.total_frames = 100
        self.fps = 30.0
        self.visible_start = 0
        self.visible_end = 100
        self.current_frame = 0
        
        # フレーム状態
        self.frame_statuses: Dict[int, FrameStatus] = {}
        self.alerts: Dict[int, List[Dict]] = {}
        self.markers: List[TimelineMarkerDTO] = []
        
        # インタラクション状態
        self.is_scrubbing = False
        self.hover_frame: Optional[int] = None
        
        # スタイル設定
        self.background_color = QColor(30, 30, 30)
        self.frame_colors = {
            FrameStatus.UNPROCESSED: QColor(60, 60, 60),
            FrameStatus.UNCONFIRMED: QColor(100, 100, 50),
            FrameStatus.CONFIRMED: QColor(50, 100, 50),
            FrameStatus.EDITED: QColor(50, 50, 100),
            FrameStatus.ALERT: QColor(150, 50, 50)
        }
        self.playhead_color = QColor(255, 255, 255)
        self.marker_color = QColor(255, 200, 0)
        self.hover_color = QColor(255, 255, 255, 50)
    
    def set_timeline_info(self, total_frames: int, fps: float, visible_start: int, visible_end: int):
        """タイムライン情報を設定"""
        self.total_frames = total_frames
        self.fps = fps
        self.visible_start = visible_start
        self.visible_end = visible_end
        self.update()
    
    def set_current_frame(self, frame: int):
        """現在のフレームを設定"""
        self.current_frame = frame
        self.update()
    
    def set_frame_status(self, frame: int, status: FrameStatus):
        """フレーム状態を設定"""
        self.frame_statuses[frame] = status
        self.update()
    
    def set_frame_statuses(self, statuses: Dict[int, FrameStatus]):
        """複数のフレーム状態を設定"""
        self.frame_statuses.update(statuses)
        self.update()
    
    def add_alert(self, frame: int, alert_data: Dict):
        """アラートを追加"""
        if frame not in self.alerts:
            self.alerts[frame] = []
        self.alerts[frame].append(alert_data)
        self.update()
    
    def add_marker(self, marker: TimelineMarkerDTO):
        """マーカーを追加"""
        self.markers.append(marker)
        self.update()
    
    def paintEvent(self, event: QPaintEvent):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        painter.fillRect(self.rect(), self.background_color)
        
        # フレーム幅の計算
        visible_frames = self.visible_end - self.visible_start
        if visible_frames <= 0:
            return
        
        frame_width = self.width() / visible_frames
        
        # フレーム状態を描画
        for frame in range(self.visible_start, self.visible_end + 1):
            x = (frame - self.visible_start) * frame_width
            
            # フレーム状態
            status = self.frame_statuses.get(frame, FrameStatus.UNPROCESSED)
            color = self.frame_colors[status]
            
            # アラートがある場合は色を変更
            if frame in self.alerts:
                color = self.frame_colors[FrameStatus.ALERT]
            
            painter.fillRect(int(x), 10, max(1, int(frame_width - 1)), 40, color)
        
        # マーカーを描画
        painter.setPen(QPen(self.marker_color, 2))
        for marker in self.markers:
            if self.visible_start <= marker.frame_index <= self.visible_end:
                x = (marker.frame_index - self.visible_start) * frame_width
                painter.drawLine(int(x), 0, int(x), self.height())
        
        # ホバー表示
        if self.hover_frame is not None and self.visible_start <= self.hover_frame <= self.visible_end:
            x = (self.hover_frame - self.visible_start) * frame_width
            painter.fillRect(int(x), 0, max(1, int(frame_width)), self.height(), self.hover_color)
        
        # 再生ヘッドを描画
        if self.visible_start <= self.current_frame <= self.visible_end:
            x = (self.current_frame - self.visible_start) * frame_width
            painter.setPen(QPen(self.playhead_color, 2))
            painter.drawLine(int(x), 0, int(x), self.height())
            
            # 再生ヘッドの三角形
            painter.setBrush(QBrush(self.playhead_color))
            painter.drawPolygon([
                QPoint(int(x - 5), 0),
                QPoint(int(x + 5), 0),
                QPoint(int(x), 8)
            ])
    
    def mousePressEvent(self, event: QMouseEvent):
        """マウス押下イベント"""
        if event.button() == Qt.MouseButton.LeftButton:
            frame = self._get_frame_at_position(event.position().x())
            if frame is not None:
                self.is_scrubbing = True
                self.scrubStarted.emit()
                self.frameClicked.emit(frame)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """マウス移動イベント"""
        frame = self._get_frame_at_position(event.position().x())
        
        if self.is_scrubbing and frame is not None:
            self.scrubMoved.emit(frame)
        
        self.hover_frame = frame
        self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """マウスリリースイベント"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_scrubbing:
            self.is_scrubbing = False
            self.scrubEnded.emit()
    
    def wheelEvent(self, event: QWheelEvent):
        """ホイールイベント"""
        # ズーム機能（親ウィジェットに伝播）
        event.ignore()
    
    def _get_frame_at_position(self, x: float) -> Optional[int]:
        """座標からフレーム番号を取得"""
        visible_frames = self.visible_end - self.visible_start
        if visible_frames <= 0:
            return None
        
        frame_width = self.width() / visible_frames
        frame = int(x / frame_width) + self.visible_start
        
        if 0 <= frame < self.total_frames:
            return frame
        return None


class TimelineWidget(QWidget):
    """
    タイムラインウィジェット
    
    ルーラーとトラックを組み合わせた完全なタイムライン。
    """
    
    # シグナル
    frameChanged = pyqtSignal(int)
    zoomChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # タイムライン状態
        self.state = TimelineStateDTO(
            total_frames=100,
            fps=30.0,
            duration=100/30.0,
            current_frame=0,
            zoom_level=1.0,
            visible_start=0,
            visible_end=100,
            time_unit="frames",
            is_scrubbing=False,
            scrub_frame=None
        )
        
        # ズームの制限
        self.min_zoom = 0.1
        self.max_zoom = 10.0
    
    def setup_ui(self):
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # コントロールバー
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        # 時間単位選択
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.addItems(["Frames", "Seconds", "Timecode"])
        self.time_unit_combo.currentTextChanged.connect(self._on_time_unit_changed)
        control_layout.addWidget(QLabel("Unit:"))
        control_layout.addWidget(self.time_unit_combo)
        
        # ズームコントロール
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setText("-")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 1000)  # 0.1x to 10x (×100)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setText("+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        
        self.zoom_fit_btn = QToolButton()
        self.zoom_fit_btn.setText("Fit")
        self.zoom_fit_btn.clicked.connect(self.fit_to_window)
        
        control_layout.addWidget(QLabel("Zoom:"))
        control_layout.addWidget(self.zoom_out_btn)
        control_layout.addWidget(self.zoom_slider)
        control_layout.addWidget(self.zoom_in_btn)
        control_layout.addWidget(self.zoom_fit_btn)
        
        control_layout.addStretch()
        
        # 現在フレーム表示
        self.frame_label = QLabel("Frame: 0")
        control_layout.addWidget(self.frame_label)
        
        layout.addLayout(control_layout)
        
        # ルーラー
        self.ruler = TimelineRuler()
        layout.addWidget(self.ruler)
        
        # トラック
        self.track = TimelineTrack()
        self.track.frameClicked.connect(self._on_frame_clicked)
        self.track.scrubStarted.connect(self._on_scrub_started)
        self.track.scrubMoved.connect(self._on_scrub_moved)
        self.track.scrubEnded.connect(self._on_scrub_ended)
        layout.addWidget(self.track)
    
    def set_timeline_info(self, total_frames: int, fps: float):
        """タイムライン情報を設定"""
        self.state = TimelineStateDTO(
            total_frames=total_frames,
            fps=fps,
            duration=total_frames/fps,
            current_frame=min(self.state.current_frame, total_frames - 1),
            zoom_level=self.state.zoom_level,
            visible_start=0,
            visible_end=min(int(100 * self.state.zoom_level), total_frames),
            time_unit=self.state.time_unit,
            is_scrubbing=False,
            scrub_frame=None
        )
        self._update_display()
    
    def set_current_frame(self, frame: int):
        """現在のフレームを設定"""
        if 0 <= frame < self.state.total_frames:
            self.state = TimelineStateDTO(
                total_frames=self.state.total_frames,
                fps=self.state.fps,
                duration=self.state.duration,
                current_frame=frame,
                zoom_level=self.state.zoom_level,
                visible_start=self.state.visible_start,
                visible_end=self.state.visible_end,
                time_unit=self.state.time_unit,
                is_scrubbing=self.state.is_scrubbing,
                scrub_frame=self.state.scrub_frame
            )
            self.track.set_current_frame(frame)
            self.frame_label.setText(f"Frame: {frame}")
            
            # 自動スクロール（現在フレームが見えるように）
            if frame < self.state.visible_start or frame > self.state.visible_end:
                self._center_on_frame(frame)
    
    def zoom_in(self):
        """ズームイン"""
        new_zoom = min(self.state.zoom_level * 1.2, self.max_zoom)
        self.set_zoom_level(new_zoom)
    
    def zoom_out(self):
        """ズームアウト"""
        new_zoom = max(self.state.zoom_level / 1.2, self.min_zoom)
        self.set_zoom_level(new_zoom)
    
    def set_zoom_level(self, zoom: float):
        """ズームレベルを設定"""
        zoom = max(self.min_zoom, min(zoom, self.max_zoom))
        
        # 中心フレームを維持
        center_frame = (self.state.visible_start + self.state.visible_end) // 2
        visible_frames = int(100 / zoom)
        
        visible_start = max(0, center_frame - visible_frames // 2)
        visible_end = min(self.state.total_frames - 1, visible_start + visible_frames)
        
        # 端の調整
        if visible_end == self.state.total_frames - 1:
            visible_start = max(0, visible_end - visible_frames)
        
        self.state = TimelineStateDTO(
            total_frames=self.state.total_frames,
            fps=self.state.fps,
            duration=self.state.duration,
            current_frame=self.state.current_frame,
            zoom_level=zoom,
            visible_start=visible_start,
            visible_end=visible_end,
            time_unit=self.state.time_unit,
            is_scrubbing=self.state.is_scrubbing,
            scrub_frame=self.state.scrub_frame
        )
        
        self.zoom_slider.setValue(int(zoom * 100))
        self._update_display()
        self.zoomChanged.emit(zoom)
    
    def fit_to_window(self):
        """ウィンドウに合わせる"""
        # 全フレームが表示されるズームレベルを計算
        zoom = 100.0 / self.state.total_frames
        self.set_zoom_level(zoom)
    
    def _center_on_frame(self, frame: int):
        """指定フレームを中心に表示"""
        visible_frames = self.state.visible_end - self.state.visible_start
        visible_start = max(0, frame - visible_frames // 2)
        visible_end = min(self.state.total_frames - 1, visible_start + visible_frames)
        
        if visible_end == self.state.total_frames - 1:
            visible_start = max(0, visible_end - visible_frames)
        
        self.state = TimelineStateDTO(
            total_frames=self.state.total_frames,
            fps=self.state.fps,
            duration=self.state.duration,
            current_frame=self.state.current_frame,
            zoom_level=self.state.zoom_level,
            visible_start=visible_start,
            visible_end=visible_end,
            time_unit=self.state.time_unit,
            is_scrubbing=self.state.is_scrubbing,
            scrub_frame=self.state.scrub_frame
        )
        self._update_display()
    
    def _update_display(self):
        """表示を更新"""
        self.ruler.set_timeline_info(
            self.state.fps,
            self.state.visible_start,
            self.state.visible_end,
            self.state.zoom_level
        )
        
        self.track.set_timeline_info(
            self.state.total_frames,
            self.state.fps,
            self.state.visible_start,
            self.state.visible_end
        )
    
    def _on_time_unit_changed(self, text: str):
        """時間単位変更"""
        unit_map = {"Frames": "frames", "Seconds": "seconds", "Timecode": "timecode"}
        unit = unit_map.get(text, "frames")
        self.ruler.set_time_unit(unit)
        
        # 状態を更新
        self.state = TimelineStateDTO(
            total_frames=self.state.total_frames,
            fps=self.state.fps,
            duration=self.state.duration,
            current_frame=self.state.current_frame,
            zoom_level=self.state.zoom_level,
            visible_start=self.state.visible_start,
            visible_end=self.state.visible_end,
            time_unit=unit,
            is_scrubbing=self.state.is_scrubbing,
            scrub_frame=self.state.scrub_frame
        )
    
    def _on_zoom_slider_changed(self, value: int):
        """ズームスライダー変更"""
        zoom = value / 100.0
        if abs(zoom - self.state.zoom_level) > 0.01:
            self.set_zoom_level(zoom)
    
    def _on_frame_clicked(self, frame: int):
        """フレームクリック"""
        self.set_current_frame(frame)
        self.frameChanged.emit(frame)
    
    def _on_scrub_started(self):
        """スクラブ開始"""
        self.state = TimelineStateDTO(
            total_frames=self.state.total_frames,
            fps=self.state.fps,
            duration=self.state.duration,
            current_frame=self.state.current_frame,
            zoom_level=self.state.zoom_level,
            visible_start=self.state.visible_start,
            visible_end=self.state.visible_end,
            time_unit=self.state.time_unit,
            is_scrubbing=True,
            scrub_frame=self.state.current_frame
        )
    
    def _on_scrub_moved(self, frame: int):
        """スクラブ移動"""
        self.state = TimelineStateDTO(
            total_frames=self.state.total_frames,
            fps=self.state.fps,
            duration=self.state.duration,
            current_frame=self.state.current_frame,
            zoom_level=self.state.zoom_level,
            visible_start=self.state.visible_start,
            visible_end=self.state.visible_end,
            time_unit=self.state.time_unit,
            is_scrubbing=True,
            scrub_frame=frame
        )
        self.set_current_frame(frame)
        self.frameChanged.emit(frame)
    
    def _on_scrub_ended(self):
        """スクラブ終了"""
        self.state = TimelineStateDTO(
            total_frames=self.state.total_frames,
            fps=self.state.fps,
            duration=self.state.duration,
            current_frame=self.state.current_frame,
            zoom_level=self.state.zoom_level,
            visible_start=self.state.visible_start,
            visible_end=self.state.visible_end,
            time_unit=self.state.time_unit,
            is_scrubbing=False,
            scrub_frame=None
        )