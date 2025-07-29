#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タイムラインウィジェットのテスト
"""
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import QPoint

from src.ui.timeline_widget import TimelineWidget, TimelineRuler, TimelineTrack
from src.domain.dto.timeline_dto import FrameStatus, TimelineMarkerDTO


@pytest.fixture(scope="module")
def qapp():
    """PyQt6アプリケーションのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def timeline_widget(qapp):
    """タイムラインウィジェットのフィクスチャ"""
    widget = TimelineWidget()
    widget.show()
    return widget


class TestTimelineWidget:
    """TimelineWidgetのテスト"""
    
    def test_initialization(self, timeline_widget):
        """初期化テスト"""
        assert timeline_widget.state.total_frames == 100
        assert timeline_widget.state.fps == 30.0
        assert timeline_widget.state.current_frame == 0
        assert timeline_widget.state.zoom_level == 1.0
        assert timeline_widget.state.time_unit == "frames"
    
    def test_set_timeline_info(self, timeline_widget):
        """タイムライン情報設定テスト"""
        timeline_widget.set_timeline_info(300, 24.0)
        
        assert timeline_widget.state.total_frames == 300
        assert timeline_widget.state.fps == 24.0
        assert timeline_widget.state.duration == 300 / 24.0
    
    def test_set_current_frame(self, timeline_widget):
        """現在フレーム設定テスト"""
        timeline_widget.set_timeline_info(300, 30.0)
        timeline_widget.set_current_frame(150)
        
        assert timeline_widget.state.current_frame == 150
        assert timeline_widget.frame_label.text() == "Frame: 150"
    
    def test_zoom_in_out(self, timeline_widget):
        """ズームイン/アウトテスト"""
        initial_zoom = timeline_widget.state.zoom_level
        
        # ズームイン
        timeline_widget.zoom_in()
        assert timeline_widget.state.zoom_level > initial_zoom
        
        # ズームアウト
        timeline_widget.zoom_out()
        timeline_widget.zoom_out()
        assert timeline_widget.state.zoom_level < initial_zoom
    
    def test_zoom_limits(self, timeline_widget):
        """ズーム制限テスト"""
        # 最大ズーム
        timeline_widget.set_zoom_level(20.0)
        assert timeline_widget.state.zoom_level <= timeline_widget.max_zoom
        
        # 最小ズーム
        timeline_widget.set_zoom_level(0.01)
        assert timeline_widget.state.zoom_level >= timeline_widget.min_zoom
    
    def test_fit_to_window(self, timeline_widget):
        """ウィンドウフィットテスト"""
        timeline_widget.set_timeline_info(500, 30.0)
        timeline_widget.fit_to_window()
        
        # 全フレームが表示される
        visible_frames = timeline_widget.state.visible_end - timeline_widget.state.visible_start
        assert visible_frames >= timeline_widget.state.total_frames - 1
    
    def test_time_unit_change(self, timeline_widget):
        """時間単位変更テスト"""
        timeline_widget.time_unit_combo.setCurrentText("Seconds")
        assert timeline_widget.state.time_unit == "seconds"
        
        timeline_widget.time_unit_combo.setCurrentText("Timecode")
        assert timeline_widget.state.time_unit == "timecode"
    
    def test_frame_signal(self, timeline_widget, qtbot):
        """フレーム変更シグナルテスト"""
        with qtbot.waitSignal(timeline_widget.frameChanged) as blocker:
            timeline_widget.set_current_frame(50)
        
        assert blocker.args == [50]
    
    def test_zoom_signal(self, timeline_widget, qtbot):
        """ズーム変更シグナルテスト"""
        with qtbot.waitSignal(timeline_widget.zoomChanged) as blocker:
            timeline_widget.set_zoom_level(2.0)
        
        assert abs(blocker.args[0] - 2.0) < 0.01


class TestTimelineRuler:
    """TimelineRulerのテスト"""
    
    def test_ruler_initialization(self, qapp):
        """ルーラー初期化テスト"""
        ruler = TimelineRuler()
        assert ruler.fps == 30.0
        assert ruler.zoom_level == 1.0
        assert ruler.time_unit == "frames"
    
    def test_ruler_time_unit(self, qapp):
        """ルーラー時間単位テスト"""
        ruler = TimelineRuler()
        
        ruler.set_time_unit("seconds")
        assert ruler.time_unit == "seconds"
        
        ruler.set_time_unit("timecode")
        assert ruler.time_unit == "timecode"
    
    def test_label_formatting(self, qapp):
        """ラベルフォーマットテスト"""
        ruler = TimelineRuler()
        
        # フレーム単位
        ruler.set_time_unit("frames")
        assert ruler._format_label(30) == "30"
        
        # 秒単位
        ruler.set_time_unit("seconds")
        ruler.fps = 30.0
        assert ruler._format_label(30) == "1.0s"
        
        # タイムコード
        ruler.set_time_unit("timecode")
        assert ruler._format_label(90) == "00:03"  # 3秒


class TestTimelineTrack:
    """TimelineTrackのテスト"""
    
    def test_track_initialization(self, qapp):
        """トラック初期化テスト"""
        track = TimelineTrack()
        assert track.total_frames == 100
        assert track.fps == 30.0
        assert track.current_frame == 0
        assert not track.is_scrubbing
    
    def test_frame_status(self, qapp):
        """フレーム状態テスト"""
        track = TimelineTrack()
        
        # 単一フレーム状態設定
        track.set_frame_status(10, FrameStatus.CONFIRMED)
        assert track.frame_statuses[10] == FrameStatus.CONFIRMED
        
        # 複数フレーム状態設定
        statuses = {
            20: FrameStatus.EDITED,
            21: FrameStatus.ALERT,
            22: FrameStatus.UNCONFIRMED
        }
        track.set_frame_statuses(statuses)
        
        assert track.frame_statuses[20] == FrameStatus.EDITED
        assert track.frame_statuses[21] == FrameStatus.ALERT
        assert track.frame_statuses[22] == FrameStatus.UNCONFIRMED
    
    def test_alert_management(self, qapp):
        """アラート管理テスト"""
        track = TimelineTrack()
        
        alert_data = {
            "level": "required",
            "reason": "Detection confidence too low",
            "confidence": 0.3
        }
        
        track.add_alert(50, alert_data)
        assert 50 in track.alerts
        assert len(track.alerts[50]) == 1
        assert track.alerts[50][0]["reason"] == "Detection confidence too low"
    
    def test_marker_management(self, qapp):
        """マーカー管理テスト"""
        track = TimelineTrack()
        
        marker = TimelineMarkerDTO(
            id="marker1",
            frame_index=75,
            label="Important",
            color="#FF0000",
            created_at="2025-07-28T10:00:00"
        )
        
        track.add_marker(marker)
        assert len(track.markers) == 1
        assert track.markers[0].frame_index == 75
    
    def test_frame_at_position(self, qapp):
        """座標からフレーム取得テスト"""
        track = TimelineTrack()
        track.resize(1000, 60)
        track.set_timeline_info(100, 30.0, 0, 100)
        
        # 幅1000pxで100フレーム表示なので、1フレーム10px
        assert track._get_frame_at_position(0) == 0
        assert track._get_frame_at_position(50) == 5
        assert track._get_frame_at_position(995) == 99
    
    def test_mouse_interaction(self, qapp, qtbot):
        """マウスインタラクションテスト"""
        track = TimelineTrack()
        track.resize(1000, 60)
        track.set_timeline_info(100, 30.0, 0, 100)
        track.show()
        
        # フレームクリックテスト
        with qtbot.waitSignal(track.frameClicked) as blocker:
            QTest.mouseClick(track, Qt.MouseButton.LeftButton, pos=QPoint(100, 30))
        
        assert blocker.args[0] == 10  # 100px = フレーム10
        
        # スクラブテスト
        with qtbot.waitSignal(track.scrubStarted):
            QTest.mousePress(track, Qt.MouseButton.LeftButton, pos=QPoint(200, 30))
        
        assert track.is_scrubbing
        
        with qtbot.waitSignal(track.scrubEnded):
            QTest.mouseRelease(track, Qt.MouseButton.LeftButton, pos=QPoint(300, 30))