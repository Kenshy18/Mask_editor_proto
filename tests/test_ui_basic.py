#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本UIのテスト

メインウィンドウとビデオプレビューウィジェットの基本動作を検証します。
"""
import sys
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox

# テスト対象のインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ui import init_i18n, MainWindow
from ui.video_preview import VideoPreviewWidget


@pytest.fixture(scope="session")
def qapp():
    """Qt アプリケーションのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # i18nの初期化
    i18n = init_i18n(app)
    i18n.set_locale("ja_JP")
    
    yield app
    
    # クリーンアップは不要（pytestが管理）


@pytest.fixture
def main_window(qapp):
    """メインウィンドウのフィクスチャ"""
    window = MainWindow()
    window.show()
    QTest.qWaitForWindowExposed(window)
    yield window
    window.close()


class TestMainWindow:
    """メインウィンドウのテスト"""
    
    def test_window_creation(self, main_window):
        """ウィンドウ作成の基本テスト"""
        assert main_window is not None
        assert main_window.isVisible()
        assert main_window.windowTitle() == "Mask Editor GOD"
    
    def test_menu_structure(self, main_window):
        """メニュー構造のテスト"""
        menubar = main_window.menuBar()
        assert menubar is not None
        
        # メニューの存在確認
        menus = [action.text() for action in menubar.actions()]
        assert "ファイル(&F)" in menus
        assert "編集(&E)" in menus
        assert "表示(&V)" in menus
        assert "ツール(&T)" in menus
        assert "ヘルプ(&H)" in menus
    
    def test_toolbar_structure(self, main_window):
        """ツールバー構造のテスト"""
        from PyQt6.QtWidgets import QToolBar
        toolbars = main_window.findChildren(QToolBar)
        assert len(toolbars) >= 3  # メイン、再生、ズームツールバー
        
        # ツールバーの名前確認
        toolbar_names = [tb.objectName() for tb in toolbars]
        assert "MainToolBar" in toolbar_names
        assert "PlaybackToolBar" in toolbar_names
        assert "ZoomToolBar" in toolbar_names
    
    def test_statusbar_exists(self, main_window):
        """ステータスバーの存在確認"""
        statusbar = main_window.statusBar()
        assert statusbar is not None
        assert statusbar.isVisible()
    
    def test_central_widget(self, main_window):
        """中央ウィジェットのテスト"""
        central = main_window.centralWidget()
        assert central is not None
        
        # ビデオプレビューが含まれているか
        assert main_window.video_preview is not None
        assert isinstance(main_window.video_preview, VideoPreviewWidget)
    
    def test_action_states_without_project(self, main_window):
        """プロジェクトなしでのアクション状態"""
        # プロジェクトなしでは無効になるべきアクション
        assert not main_window.action_save_project.isEnabled()
        assert not main_window.action_save_project_as.isEnabled()
        assert not main_window.action_export_video.isEnabled()
        assert not main_window.action_undo.isEnabled()
        assert not main_window.action_redo.isEnabled()
        
        # 常に有効なアクション
        assert main_window.action_new_project.isEnabled()
        assert main_window.action_open_project.isEnabled()
        assert main_window.action_import_video.isEnabled()
    
    def test_new_project_action(self, main_window, monkeypatch):
        """新規プロジェクトアクションのテスト"""
        # メッセージボックスを自動的に閉じる
        monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
        
        # 新規プロジェクトアクションを実行
        main_window.action_new_project.trigger()
        
        # プロジェクトが作成されたか確認
        assert main_window.current_project is not None
        assert main_window.current_project.name == "Untitled Project"
        assert not main_window.is_modified
        
        # UIが更新されたか確認
        assert main_window.action_save_project.isEnabled()
        assert main_window.action_save_project_as.isEnabled()
    
    def test_fullscreen_toggle(self, main_window):
        """フルスクリーン切り替えのテスト"""
        # フルスクリーンでない状態から開始
        assert not main_window.isFullScreen()
        assert not main_window.action_fullscreen.isChecked()
        
        # フルスクリーンに切り替え
        main_window.action_fullscreen.trigger()
        assert main_window.action_fullscreen.isChecked()
        # 注: isFullScreen()はウィンドウマネージャーによって遅延する場合がある
        
        # 通常表示に戻す
        main_window.action_fullscreen.trigger()
        assert not main_window.action_fullscreen.isChecked()


class TestVideoPreviewWidget:
    """ビデオプレビューウィジェットのテスト"""
    
    @pytest.fixture
    def video_preview(self, qapp):
        """ビデオプレビューウィジェットのフィクスチャ"""
        widget = VideoPreviewWidget()
        widget.show()
        QTest.qWaitForWindowExposed(widget)
        yield widget
        widget.close()
    
    def test_widget_creation(self, video_preview):
        """ウィジェット作成の基本テスト"""
        assert video_preview is not None
        assert video_preview.isVisible()
        assert video_preview.display_label is not None
    
    def test_initial_state(self, video_preview):
        """初期状態のテスト"""
        assert video_preview.media_reader is None
        assert video_preview.current_frame_index == 0
        assert not video_preview.is_playing
        assert video_preview.zoom_level == 1.0
        assert video_preview.fit_to_window
    
    def test_playback_controls_without_video(self, video_preview):
        """動画なしでの再生制御テスト"""
        # 動画なしでは再生できない
        video_preview.play()
        assert not video_preview.is_playing
        
        # シークも効果なし
        video_preview.seek_to_frame(10)
        assert video_preview.current_frame_index == 0
    
    def test_zoom_controls(self, video_preview):
        """ズーム制御のテスト"""
        # ズームイン
        video_preview.set_zoom(2.0)
        assert video_preview.zoom_level == 2.0
        assert not video_preview.fit_to_window
        
        # ズームアウト
        video_preview.set_zoom(0.5)
        assert video_preview.zoom_level == 0.5
        
        # 範囲制限
        video_preview.set_zoom(0.05)
        assert video_preview.zoom_level == 0.1  # 最小値
        
        video_preview.set_zoom(20.0)
        assert video_preview.zoom_level == 10.0  # 最大値
        
        # ウィンドウに合わせる
        video_preview.fit_to_window_size()
        assert video_preview.fit_to_window
    
    def test_playback_speed(self, video_preview):
        """再生速度のテスト"""
        # 動画なしでもplayback_fpsは確認できる
        assert video_preview.playback_fps == 30.0  # デフォルト値
        
        # set_playback_speedメソッドのテスト
        # 動画がロードされていない場合、playback_fpsは変更されない
        video_preview.set_playback_speed(2.0)
        assert video_preview.playback_fps == 30.0  # 変更されない
        
        video_preview.set_playback_speed(0.5)
        assert video_preview.playback_fps == 30.0  # 変更されない
    
    def test_mouse_wheel_zoom(self, video_preview):
        """マウスホイールによるズームテスト"""
        original_zoom = video_preview.zoom_level
        
        # Ctrlキーを押しながらホイール（ズーム）
        video_preview.display_label.last_modifiers = Qt.KeyboardModifier.ControlModifier
        video_preview._on_mouse_wheel(120)  # 上方向
        assert video_preview.zoom_level > original_zoom
        
        video_preview._on_mouse_wheel(-120)  # 下方向
        assert video_preview.zoom_level == pytest.approx(original_zoom, rel=0.01)
    
    def test_mouse_wheel_frame_navigation(self, video_preview):
        """マウスホイールによるフレームナビゲーションテスト"""
        # 動画なしでは効果なし
        video_preview.display_label.last_modifiers = Qt.KeyboardModifier.NoModifier
        video_preview._on_mouse_wheel(120)  # 上方向（前のフレーム）
        assert video_preview.current_frame_index == 0
        
        video_preview._on_mouse_wheel(-120)  # 下方向（次のフレーム）
        assert video_preview.current_frame_index == 0


class TestI18n:
    """国際化機能のテスト"""
    
    def test_japanese_translations(self, qapp):
        """日本語翻訳のテスト"""
        from ui.i18n import get_i18n, tr
        
        i18n = get_i18n()
        i18n.set_locale("ja_JP")
        
        # メニュー項目
        assert tr("menu.file") == "ファイル(&F)"
        assert tr("menu.file.new_project") == "新規プロジェクト(&N)"
        assert tr("menu.edit.undo") == "元に戻す(&U)"
        
        # ツールバー項目
        assert tr("toolbar.play") == "再生"
        assert tr("toolbar.stop") == "停止"
        
        # ステータスバー
        assert tr("status.ready") == "準備完了"
        assert tr("status.loading") == "読み込み中..."
    
    def test_english_translations(self, qapp):
        """英語翻訳のテスト"""
        from ui.i18n import get_i18n, tr
        
        i18n = get_i18n()
        i18n.set_locale("en_US")
        
        # メニュー項目
        assert tr("menu.file") == "&File"
        assert tr("menu.file.new_project") == "&New Project"
        assert tr("menu.edit.undo") == "&Undo"
        
        # ツールバー項目
        assert tr("toolbar.play") == "Play"
        assert tr("toolbar.stop") == "Stop"
        
        # ステータスバー
        assert tr("status.ready") == "Ready"
        assert tr("status.loading") == "Loading..."
    
    def test_translation_with_variables(self, qapp):
        """変数を含む翻訳のテスト"""
        from ui.i18n import tr
        
        # フレーム情報
        result = tr("status.frame_info", current=10, total=100)
        assert "10" in result
        assert "100" in result
        
        # ズームレベル
        result = tr("status.zoom_level", zoom=150)
        assert "150" in result
    
    def test_available_locales(self, qapp):
        """利用可能なロケールのテスト"""
        from ui.i18n import get_i18n
        
        i18n = get_i18n()
        locales = i18n.get_available_locales()
        
        assert "ja_JP" in locales
        assert "en_US" in locales
        
        # 表示名の確認
        assert i18n.get_locale_display_name("ja_JP") == "日本語"
        assert i18n.get_locale_display_name("en_US") == "English"