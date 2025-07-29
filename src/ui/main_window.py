#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メインウィンドウ

Mask Editor Prototypeのメインアプリケーションウィンドウ。
メニューバー、ツールバー、ステータスバーを含む。
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QSettings, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QLabel,
    QDockWidget, QSplitter, QToolButton
)

from .i18n import tr, get_i18n
from .icon_manager import get_icon_manager
from .theme_manager import get_theme_manager
from .video_with_mask_widget import VideoWithMaskWidget
from .compact_layout_config import CompactLayoutConfig, optimize_widget_for_compact_display
from .timeline_widget import TimelineWidget
from .mask_edit_panel import MaskEditPanel
from .mask_display_panel import MaskDisplayPanel
from .project_panel import ProjectManagementPanel
from .effect_panel import EffectPanel
from core.models import Project
from domain.dto.mask_dto import MaskDTO, MaskOverlaySettingsDTO
from domain.dto.effect_dto import EffectConfigDTO
from domain.dto.brush_dto import BrushConfigDTO, BrushStrokeDTO
from domain.ports.secondary.input_data_ports import IInputDataSource
from domain.ports.secondary.effect_ports import IEffectEngine, IEffectPresetManager, IEffectPreview
from infrastructure.adapters.input_data_source_factory import InputDataSourceFactory

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """メインウィンドウクラス
    
    アプリケーションのメインフレームを提供。
    """
    
    # シグナル
    project_changed = pyqtSignal(Project)  # プロジェクトが変更された
    
    def __init__(self, di_container=None):
        logger.debug("MainWindow.__init__ started")
        super().__init__()
        logger.debug("QMainWindow.__init__ completed")
        
        # DIコンテナ
        self.di_container = di_container
        
        # アプリケーション状態
        self.current_project: Optional[Project] = None
        self.is_modified = False
        self.input_data_source: Optional[IInputDataSource] = None
        
        # 設定
        logger.debug("Creating QSettings...")
        self.settings = QSettings("MaskEditorPrototype", "MainWindow")
        logger.debug("QSettings created")
        
        # ブラシエンジンを先に初期化（UIセットアップで必要）
        self._init_brush_engine()
        
        # UIセットアップ
        logger.debug("Calling _setup_ui...")
        self._setup_ui()
        logger.debug("_setup_ui completed")
        
        logger.debug("Calling _setup_menus...")
        self._setup_menus()
        logger.debug("_setup_menus completed")
        
        logger.debug("Calling _setup_toolbars...")
        self._setup_toolbars()
        logger.debug("_setup_toolbars completed")
        
        logger.debug("Calling _setup_statusbar...")
        self._setup_statusbar()
        logger.debug("_setup_statusbar completed")
        
        logger.debug("Calling _setup_docks...")
        self._setup_docks()
        logger.debug("_setup_docks completed")
        
        # 初期状態の設定
        logger.debug("Calling _update_ui_state...")
        self._update_ui_state()
        logger.debug("_update_ui_state completed")
        
        # ウィンドウ設定の復元
        logger.debug("Calling _restore_window_state...")
        self._restore_window_state()
        logger.debug("_restore_window_state completed")
        
        # リソースモニタリング
        logger.debug("Calling _setup_resource_monitor...")
        self._setup_resource_monitor()
        logger.debug("_setup_resource_monitor completed")
        
        logger.debug("MainWindow.__init__ completed")
    
    def _init_brush_engine(self) -> None:
        """ブラシエンジンを初期化"""
        if self.di_container:
            from domain.ports.secondary.brush_ports import IBrushEngine, IBrushPreview
            try:
                self._brush_engine = self.di_container.resolve(IBrushEngine)
                self._brush_preview = self.di_container.resolve(IBrushPreview)
            except:
                # 登録されていない場合は作成
                from adapters.secondary.opencv_brush_engine import OpenCVBrushEngine
                from adapters.secondary.brush_preview import BrushPreviewAdapter
                self._brush_engine = OpenCVBrushEngine()
                self._brush_preview = BrushPreviewAdapter()
        else:
            # DIコンテナがない場合も作成
            from adapters.secondary.opencv_brush_engine import OpenCVBrushEngine
            from adapters.secondary.brush_preview import BrushPreviewAdapter
            self._brush_engine = OpenCVBrushEngine()
            self._brush_preview = BrushPreviewAdapter()
        
        logger.debug("Brush engine initialized")
    
    def _setup_ui(self) -> None:
        """基本UIをセットアップ"""
        # ウィンドウタイトル
        self.setWindowTitle("Mask Editor Prototype")
        
        # 中央ウィジェット
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # スプリッター（将来の拡張用）
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.main_splitter)
        
        # ブラシエンジンと履歴を初期化（後でDIコンテナから取得）
        if self.di_container:
            try:
                from domain.ports.secondary.brush_ports import IBrushHistory
                self._brush_history = self.di_container.resolve(IBrushHistory)
            except:
                from adapters.secondary.brush_history import BrushHistoryAdapter
                self._brush_history = BrushHistoryAdapter()
        else:
            from adapters.secondary.brush_history import BrushHistoryAdapter
            self._brush_history = BrushHistoryAdapter()
        
        # マスク付きビデオプレビュー（ブラシ対応）
        if hasattr(self, '_brush_engine') and hasattr(self, '_brush_preview'):
            from .brush_overlay_widget import BrushOverlayWidget
            self.video_preview = BrushOverlayWidget(
                self._brush_engine,
                self._brush_preview,
                self
            )
            # ブラシ関連のシグナル接続
            self.video_preview.stroke_completed.connect(self._on_brush_stroke_completed)
            self.video_preview.mask_updated.connect(self._on_brush_mask_updated)
        else:
            # ブラシエンジンがない場合は通常のビデオプレビュー
            self.video_preview = VideoWithMaskWidget(self)
        
        # 共通のシグナル接続
        self.video_preview.frame_changed.connect(self._on_frame_changed)
        self.video_preview.playback_started.connect(self._on_playback_started)
        self.video_preview.playback_stopped.connect(self._on_playback_stopped)
        self.video_preview.zoom_changed.connect(self._on_zoom_changed)
        self.video_preview.mask_clicked.connect(self._on_mask_clicked)
        
        self.main_splitter.addWidget(self.video_preview)
        
        # コンパクトレイアウト設定を適用
        CompactLayoutConfig.apply_compact_window_settings(self)
    
    def _setup_menus(self) -> None:
        """メニューバーをセットアップ"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu(tr("menu.file"))
        
        # 新規プロジェクト
        self.action_new_project = QAction(tr("menu.file.new_project"), self)
        self.action_new_project.setShortcut(QKeySequence.StandardKey.New)
        self.action_new_project.triggered.connect(self._on_new_project)
        file_menu.addAction(self.action_new_project)
        
        # プロジェクトを開く
        self.action_open_project = QAction(tr("menu.file.open_project"), self)
        self.action_open_project.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open_project.triggered.connect(self._on_open_project)
        file_menu.addAction(self.action_open_project)
        
        # プロジェクトを保存
        self.action_save_project = QAction(tr("menu.file.save_project"), self)
        self.action_save_project.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save_project.triggered.connect(self._on_save_project)
        file_menu.addAction(self.action_save_project)
        
        # プロジェクトに名前を付けて保存
        self.action_save_project_as = QAction(tr("menu.file.save_project_as"), self)
        self.action_save_project_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_project_as.triggered.connect(self._on_save_project_as)
        file_menu.addAction(self.action_save_project_as)
        
        file_menu.addSeparator()
        
        # 動画をインポート
        self.action_import_video = QAction(tr("menu.file.import_video"), self)
        self.action_import_video.setShortcut(QKeySequence("Ctrl+I"))
        self.action_import_video.triggered.connect(self._on_import_video)
        file_menu.addAction(self.action_import_video)
        
        # 動画をエクスポート
        self.action_export_video = QAction(tr("menu.file.export_video"), self)
        self.action_export_video.setShortcut(QKeySequence("Ctrl+E"))
        self.action_export_video.triggered.connect(self._on_export_video)
        file_menu.addAction(self.action_export_video)
        
        file_menu.addSeparator()
        
        # 終了
        self.action_exit = QAction(tr("menu.file.exit"), self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)
        file_menu.addAction(self.action_exit)
        
        # 編集メニュー
        edit_menu = menubar.addMenu(tr("menu.edit"))
        
        # 元に戻す
        self.action_undo = QAction(tr("menu.edit.undo"), self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(self._on_undo)
        edit_menu.addAction(self.action_undo)
        
        # やり直す
        self.action_redo = QAction(tr("menu.edit.redo"), self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(self._on_redo)
        edit_menu.addAction(self.action_redo)
        
        edit_menu.addSeparator()
        
        # 環境設定
        self.action_preferences = QAction(tr("menu.edit.preferences"), self)
        self.action_preferences.setShortcut(QKeySequence("Ctrl+,"))
        self.action_preferences.triggered.connect(self._on_preferences)
        edit_menu.addAction(self.action_preferences)
        
        # 表示メニュー
        view_menu = menubar.addMenu(tr("menu.view"))
        
        # ズーム
        self.action_zoom_in = QAction(tr("menu.view.zoom_in"), self)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.action_zoom_in.triggered.connect(self._on_zoom_in)
        view_menu.addAction(self.action_zoom_in)
        
        self.action_zoom_out = QAction(tr("menu.view.zoom_out"), self)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.action_zoom_out.triggered.connect(self._on_zoom_out)
        view_menu.addAction(self.action_zoom_out)
        
        self.action_zoom_fit = QAction(tr("menu.view.zoom_fit"), self)
        self.action_zoom_fit.setShortcut(QKeySequence("Ctrl+0"))
        self.action_zoom_fit.triggered.connect(self._on_zoom_fit)
        view_menu.addAction(self.action_zoom_fit)
        
        self.action_zoom_100 = QAction(tr("menu.view.zoom_100"), self)
        self.action_zoom_100.setShortcut(QKeySequence("Ctrl+1"))
        self.action_zoom_100.triggered.connect(self._on_zoom_100)
        view_menu.addAction(self.action_zoom_100)
        
        view_menu.addSeparator()
        
        # フルスクリーン
        self.action_fullscreen = QAction(tr("menu.view.fullscreen"), self)
        self.action_fullscreen.setShortcut(QKeySequence.StandardKey.FullScreen)
        self.action_fullscreen.setCheckable(True)
        self.action_fullscreen.triggered.connect(self._on_fullscreen)
        view_menu.addAction(self.action_fullscreen)
        
        # ツールメニュー
        tools_menu = menubar.addMenu(tr("menu.tools"))
        
        # ヘルプメニュー
        help_menu = menubar.addMenu(tr("menu.help"))
        
        # About
        self.action_about = QAction(tr("menu.help.about"), self)
        self.action_about.triggered.connect(self._on_about)
        help_menu.addAction(self.action_about)
    
    def _setup_toolbars(self) -> None:
        """ツールバーをセットアップ"""
        icon_manager = get_icon_manager()
        
        # ツールバーのスタイリング
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        
        # メインツールバー
        main_toolbar = self.addToolBar(tr("toolbar.main"))
        main_toolbar.setObjectName("MainToolBar")
        main_toolbar.setMovable(False)  # より統一感のあるUI
        main_toolbar.setIconSize(QSize(24, 24))
        
        # ファイル操作（アイコン付き）
        self.action_new_project.setIcon(icon_manager.get_icon("new_project"))
        self.action_open_project.setIcon(icon_manager.get_icon("open_project"))
        self.action_save_project.setIcon(icon_manager.get_icon("save_project"))
        
        main_toolbar.addAction(self.action_new_project)
        main_toolbar.addAction(self.action_open_project)
        main_toolbar.addAction(self.action_save_project)
        main_toolbar.addSeparator()
        
        # 編集操作（アイコン付き）
        self.action_undo.setIcon(icon_manager.get_icon("undo"))
        self.action_redo.setIcon(icon_manager.get_icon("redo"))
        
        main_toolbar.addAction(self.action_undo)
        main_toolbar.addAction(self.action_redo)
        main_toolbar.addSeparator()
        
        # 再生コントロールツールバー
        playback_toolbar = self.addToolBar(tr("toolbar.playback"))
        playback_toolbar.setObjectName("PlaybackToolBar")
        playback_toolbar.setMovable(False)
        playback_toolbar.setIconSize(QSize(32, 32))  # 再生コントロールは大きめに
        
        # 再生/一時停止（アイコン付き）
        self.action_play_pause = QAction(tr("toolbar.play"), self)
        self.action_play_pause.setIcon(icon_manager.get_icon("play", size=QSize(32, 32)))
        self.action_play_pause.setShortcut(QKeySequence("Space"))
        self.action_play_pause.setCheckable(True)
        self.action_play_pause.triggered.connect(self._on_play_pause)
        playback_toolbar.addAction(self.action_play_pause)
        
        # 停止（アイコン付き）
        self.action_stop = QAction(tr("toolbar.stop"), self)
        self.action_stop.setIcon(icon_manager.get_icon("stop", size=QSize(32, 32)))
        self.action_stop.triggered.connect(self._on_stop)
        playback_toolbar.addAction(self.action_stop)
        
        playback_toolbar.addSeparator()
        
        # フレーム移動（アイコン付き）
        self.action_previous_frame = QAction(tr("toolbar.previous_frame"), self)
        self.action_previous_frame.setIcon(icon_manager.get_icon("prev_frame", size=QSize(24, 24)))
        self.action_previous_frame.setShortcut(QKeySequence("Left"))
        self.action_previous_frame.triggered.connect(self._on_previous_frame)
        playback_toolbar.addAction(self.action_previous_frame)
        
        self.action_next_frame = QAction(tr("toolbar.next_frame"), self)
        self.action_next_frame.setIcon(icon_manager.get_icon("next_frame", size=QSize(24, 24)))
        self.action_next_frame.setShortcut(QKeySequence("Right"))
        self.action_next_frame.triggered.connect(self._on_next_frame)
        playback_toolbar.addAction(self.action_next_frame)
        
        # ズームツールバー
        zoom_toolbar = self.addToolBar(tr("toolbar.zoom"))
        zoom_toolbar.setObjectName("ZoomToolBar")
        zoom_toolbar.setMovable(False)
        zoom_toolbar.setIconSize(QSize(20, 20))
        
        # ズーム操作（アイコン付き）
        self.action_zoom_in.setIcon(icon_manager.get_icon("zoom_in", size=QSize(20, 20)))
        self.action_zoom_out.setIcon(icon_manager.get_icon("zoom_out", size=QSize(20, 20)))
        self.action_zoom_fit.setIcon(icon_manager.get_icon("zoom_fit", size=QSize(20, 20)))
        self.action_zoom_100.setIcon(icon_manager.get_icon("zoom_100", size=QSize(20, 20)))
        
        zoom_toolbar.addAction(self.action_zoom_in)
        zoom_toolbar.addAction(self.action_zoom_out)
        zoom_toolbar.addAction(self.action_zoom_fit)
        zoom_toolbar.addAction(self.action_zoom_100)
        
        # ツールバーにスペーサーを追加してレイアウトを整える
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        zoom_toolbar.addWidget(spacer)
    
    def _setup_statusbar(self) -> None:
        """ステータスバーをセットアップ"""
        from .status_bar_widgets import (
            AnimatedProgressBar, ResourceMonitor, StatusMessage,
            FrameCounter, ProcessingIndicator
        )
        
        statusbar = self.statusBar()
        statusbar.setContentsMargins(8, 4, 8, 4)
        
        # プログレスバー（ステータスバーの上部に表示）
        self.progress_bar = AnimatedProgressBar(statusbar)
        self.progress_bar.setGeometry(0, 0, statusbar.width(), 4)
        self.progress_bar.hide()  # 初期状態では非表示
        
        # 処理中インジケーター
        self.processing_indicator = ProcessingIndicator()
        statusbar.addWidget(self.processing_indicator)
        self.processing_indicator.hide()
        
        # ステータスメッセージ
        self.status_message = StatusMessage()
        statusbar.addWidget(self.status_message, 1)  # 伸縮可能
        self.status_message.show_message(tr("status.ready"), "info", 0)
        
        # フレームカウンター
        self.frame_counter = FrameCounter()
        statusbar.addWidget(self.frame_counter)
        
        # ズームレベル
        self.zoom_level_label = QLabel()
        self.zoom_level_label.setMinimumWidth(80)
        statusbar.addWidget(self.zoom_level_label)
        
        # セパレーター
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #404040;")
        statusbar.addPermanentWidget(separator1)
        
        # リソースモニター（右側）
        # CPU
        self.cpu_monitor = ResourceMonitor("cpu")
        statusbar.addPermanentWidget(self.cpu_monitor)
        
        # メモリ
        self.memory_monitor = ResourceMonitor("memory")
        statusbar.addPermanentWidget(self.memory_monitor)
        
        # GPU
        self.gpu_monitor = ResourceMonitor("gpu")
        statusbar.addPermanentWidget(self.gpu_monitor)
        
        # ステータスバーのリサイズイベントでプログレスバーをリサイズ
        def resize_progress_bar():
            self.progress_bar.setGeometry(0, 0, statusbar.width(), 4)
        
        statusbar.resizeEvent = lambda e: resize_progress_bar()
    
    def _setup_docks(self) -> None:
        """ドックウィジェットをセットアップ"""
        from .custom_dock_widget import CustomDockWidget, CollapsibleDockWidget
        
        # プロジェクト管理ドック
        self.project_dock = CustomDockWidget(tr("dock.project"), self)
        self.project_dock.setObjectName("ProjectDock")
        
        # DIコンテナからサービスを取得
        if self.di_container:
            from domain.ports.secondary.project_ports import IProjectRepository, IProjectAutoSaver
            repository = self.di_container.resolve(IProjectRepository)
            auto_saver = self.di_container.resolve(IProjectAutoSaver)
            self.project_panel = ProjectManagementPanel(repository, auto_saver, parent=self.project_dock)
        else:
            # DIコンテナがない場合はダミーパネル
            self.project_panel = QWidget(self.project_dock)
        
        self.project_dock.setWidget(self.project_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)
        CompactLayoutConfig.apply_compact_dock_settings(self.project_dock, "left")
        optimize_widget_for_compact_display(self.project_panel)
        
        # プロジェクトシグナル接続
        if hasattr(self.project_panel, 'project_new_requested'):
            self.project_panel.project_new_requested.connect(self._on_new_project)
            self.project_panel.project_opened.connect(self._on_project_opened)
            self.project_panel.project_saved.connect(self._on_project_saved)
        
        # タイムラインドック
        self.timeline_dock = CustomDockWidget(tr("dock.timeline"), self)
        self.timeline_dock.setObjectName("TimelineDock")
        self.timeline_widget = TimelineWidget(self.timeline_dock)
        self.timeline_dock.setWidget(self.timeline_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.timeline_dock)
        CompactLayoutConfig.apply_compact_dock_settings(self.timeline_dock, "bottom")
        optimize_widget_for_compact_display(self.timeline_widget)
        
        # タイムラインシグナル接続
        self.timeline_widget.frameChanged.connect(self._on_timeline_frame_changed)
        self.timeline_widget.zoomChanged.connect(self._on_timeline_zoom_changed)
        
        # マスク編集ドック（折りたたみ可能）
        self.mask_edit_dock = CollapsibleDockWidget(tr("dock.mask_edit"), self)
        self.mask_edit_dock.setObjectName("MaskEditDock")
        self.mask_edit_panel = MaskEditPanel(self.mask_edit_dock)
        self.mask_edit_dock.setWidget(self.mask_edit_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.mask_edit_dock)
        CompactLayoutConfig.apply_compact_dock_settings(self.mask_edit_dock, "right")
        optimize_widget_for_compact_display(self.mask_edit_panel)
        
        # マスク編集シグナル接続
        self.mask_edit_panel.morphology_requested.connect(self._on_morphology_requested)
        self.mask_edit_panel.morphology_applied.connect(self._on_morphology_applied)
        self.mask_edit_panel.undo_requested.connect(self._on_undo)
        self.mask_edit_panel.redo_requested.connect(self._on_redo)
        
        # マスク表示設定ドック
        self.mask_display_dock = CustomDockWidget(tr("dock.mask_display"), self)
        self.mask_display_dock.setObjectName("MaskDisplayDock")
        self.mask_display_panel = MaskDisplayPanel(self.mask_display_dock)
        self.mask_display_dock.setWidget(self.mask_display_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.mask_display_dock)
        CompactLayoutConfig.apply_compact_dock_settings(self.mask_display_dock, "right")
        optimize_widget_for_compact_display(self.mask_display_panel)
        
        # マスク表示シグナル接続
        self.mask_display_panel.settings_changed.connect(self._on_overlay_settings_changed)
        self.mask_display_panel.mask_visibility_changed.connect(self._on_mask_visibility_changed)
        self.mask_display_panel.mask_color_changed.connect(self._on_mask_color_changed)
        
        # エフェクトドック（折りたたみ可能）
        self.effect_dock = CollapsibleDockWidget(tr("dock.effects"), self)
        self.effect_dock.setObjectName("EffectDock")
        
        # DIコンテナからサービスを取得
        if self.di_container:
            effect_engine = self.di_container.resolve(IEffectEngine)
            preset_manager = self.di_container.resolve(IEffectPresetManager)
            effect_preview = self.di_container.resolve(IEffectPreview)
            self.effect_panel = EffectPanel(effect_engine, preset_manager, effect_preview, self.effect_dock)
        else:
            # DIコンテナがない場合はダミーパネル
            self.effect_panel = QWidget(self.effect_dock)
        
        self.effect_dock.setWidget(self.effect_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.effect_dock)
        CompactLayoutConfig.apply_compact_dock_settings(self.effect_dock, "right")
        optimize_widget_for_compact_display(self.effect_panel)
        
        # エフェクトシグナル接続
        if hasattr(self.effect_panel, 'effect_applied'):
            self.effect_panel.effect_applied.connect(self._on_effect_applied)
            self.effect_panel.preview_requested.connect(self._on_effect_preview_requested)
        
        # ブラシツールドック
        self.brush_dock = CollapsibleDockWidget(tr("dock.brush"), self)
        self.brush_dock.setObjectName("BrushDock")
        
        # ブラシパネルを作成（コンパクト版）
        from ui.compact_panels import CompactBrushPanel
        self.brush_panel = CompactBrushPanel(self.brush_dock)
        
        self.brush_dock.setWidget(self.brush_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.brush_dock)
        CompactLayoutConfig.apply_compact_dock_settings(self.brush_dock, "right")
        optimize_widget_for_compact_display(self.brush_panel)
        
        # ブラシシグナル接続
        if hasattr(self.brush_panel, 'config_changed'):
            self.brush_panel.config_changed.connect(self._on_brush_config_changed)
            self.brush_panel.undo_requested.connect(self._on_brush_undo)
            self.brush_panel.redo_requested.connect(self._on_brush_redo)
            self.brush_panel.clear_requested.connect(self._on_brush_clear)
        
        # 右側のドックをタブ化
        self.tabifyDockWidget(self.mask_edit_dock, self.mask_display_dock)
        self.tabifyDockWidget(self.mask_display_dock, self.effect_dock)
        self.tabifyDockWidget(self.effect_dock, self.brush_dock)
        self.mask_edit_dock.raise_()
        
        # コンパクトレイアウトのため、デフォルトドックサイズを設定
        self.resizeDocks(
            [self.project_dock, self.timeline_dock],
            [CompactLayoutConfig.DOCK_SIZES["left"]["width"],
             CompactLayoutConfig.DOCK_SIZES["bottom"]["height"]],
            Qt.Orientation.Vertical
        )
        
        # プロパティドック（将来実装）
        # アラートドック（将来実装）
    
    def _setup_resource_monitor(self) -> None:
        """リソースモニタリングをセットアップ"""
        # タイマーでリソース使用状況を更新
        self.resource_timer = QTimer(self)
        self.resource_timer.timeout.connect(self._update_resource_status)
        self.resource_timer.start(1000)  # 1秒ごと
    
    def _update_resource_status(self) -> None:
        """リソース使用状況を更新"""
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = int(psutil.cpu_percent(interval=0.1))
            self.cpu_monitor.set_value(cpu_percent)
            
            # メモリ使用量
            memory = psutil.virtual_memory()
            memory_percent = int(memory.percent)
            self.memory_monitor.set_value(memory_percent)
            
            # GPU使用率（簡易実装）
            # 実際のGPU使用率取得は別途実装が必要
            self.gpu_monitor.set_value(0)  # GPU使用率が取得できない場合
            
        except ImportError:
            # psutilがない場合は表示しない
            pass
    
    def _update_ui_state(self) -> None:
        """UI状態を更新"""
        has_project = self.current_project is not None
        has_video = self.video_preview.media_reader is not None
        
        # アクション有効/無効
        self.action_save_project.setEnabled(has_project)
        self.action_save_project_as.setEnabled(has_project)
        self.action_export_video.setEnabled(has_video)
        
        self.action_undo.setEnabled(has_project and self.current_project.can_undo())
        self.action_redo.setEnabled(has_project and self.current_project.can_redo())
        
        self.action_play_pause.setEnabled(has_video)
        self.action_stop.setEnabled(has_video)
        self.action_previous_frame.setEnabled(has_video)
        self.action_next_frame.setEnabled(has_video)
        
        # タイトル更新
        title = "Mask Editor Prototype"
        if self.current_project:
            title = f"{self.current_project.name} - {title}"
            if self.is_modified:
                title = f"*{title}"
        self.setWindowTitle(title)
    
    def _restore_window_state(self) -> None:
        """ウィンドウ状態を復元"""
        # ジオメトリ
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # ウィンドウ状態
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
    
    def _save_window_state(self) -> None:
        """ウィンドウ状態を保存"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
    
    # スロット
    def _on_new_project(self) -> None:
        """新規プロジェクト"""
        if not self._confirm_discard_changes():
            return
        
        self.current_project = Project(name="Untitled Project")
        self.is_modified = False
        self.project_changed.emit(self.current_project)
        self._update_ui_state()
        
        logger.info("New project created")
    
    def _on_open_project(self) -> None:
        """プロジェクトを開く"""
        if not self._confirm_discard_changes():
            return
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            tr("dialog.open_project"),
            "",
            f"{tr('file_dialog.project_files')} (*.mosaicproj);;{tr('file_dialog.all_files')} (*)"
        )
        
        if not filepath:
            return
        
        try:
            self.current_project = Project.load(filepath)
            self.is_modified = False
            self.project_changed.emit(self.current_project)
            self._update_ui_state()
            
            # 動画も読み込み
            if self.current_project.source_video_path:
                if self.video_preview.load_video(self.current_project.source_video_path):
                    # タイムラインを更新
                    frame_count = self.video_preview.get_frame_count()
                    fps = self.video_preview.get_fps()
                    if frame_count > 0 and fps > 0:
                        self.timeline_widget.set_timeline_info(frame_count, fps)
            
            logger.info(f"Project loaded: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("dialog.error"),
                tr("error.load_failed", reason=str(e))
            )
    
    def _on_save_project(self) -> None:
        """プロジェクトを保存"""
        if not self.current_project:
            return
        
        # ファイルパスが設定されていない場合は「名前を付けて保存」
        if not hasattr(self.current_project, '_filepath'):
            self._on_save_project_as()
            return
        
        try:
            self.current_project.save(self.current_project._filepath)
            self.is_modified = False
            self._update_ui_state()
            
            self.status_message.show_message(tr("status.saved"), "success", 3000)
            logger.info(f"Project saved: {self.current_project._filepath}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("dialog.error"),
                tr("error.save_failed", reason=str(e))
            )
    
    def _on_save_project_as(self) -> None:
        """プロジェクトに名前を付けて保存"""
        if not self.current_project:
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            tr("dialog.save_project"),
            f"{self.current_project.name}.mosaicproj",
            f"{tr('file_dialog.project_files')} (*.mosaicproj)"
        )
        
        if not filepath:
            return
        
        try:
            self.current_project.save(filepath)
            self.current_project._filepath = filepath
            self.is_modified = False
            self._update_ui_state()
            
            self.status_message.show_message(tr("status.saved"), "success", 3000)
            logger.info(f"Project saved as: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("dialog.error"),
                tr("error.save_failed", reason=str(e))
            )
    
    def _on_import_video(self) -> None:
        """動画をインポート"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            tr("dialog.import_video"),
            "",
            f"{tr('file_dialog.video_files')} (*.mp4 *.mov *.avi *.mkv);;{tr('file_dialog.all_files')} (*)"
        )
        
        if not filepath:
            return
        
        # 動画を読み込み
        self.status_message.show_message(tr("status.loading"), "info", 0)
        self.processing_indicator.start_processing()
        if self.video_preview.load_video(filepath):
            # プロジェクトがない場合は作成
            if not self.current_project:
                self.current_project = Project(name=Path(filepath).stem)
            
            self.current_project.source_video_path = filepath
            self.is_modified = True
            self._update_ui_state()
            
            # タイムラインを更新
            frame_count = self.video_preview.get_frame_count()
            fps = self.video_preview.get_fps()
            if frame_count > 0 and fps > 0:
                self.timeline_widget.set_timeline_info(frame_count, fps)
            
            # 入力データソースを初期化（プロトタイプ用）
            try:
                # 現在はテスト入力パスを使用
                test_input_path = Path("/home/kenke/segformer/2MLPC/CODEFLOW0409/XxREPO_latest0615xX/MASK_EDITOR_GOD/test_input")
                if test_input_path.exists():
                    self.input_data_source = InputDataSourceFactory.create_local_file_source(test_input_path)
                    logger.info(f"Input data source initialized from: {test_input_path}")
                    
                    # 最初のフレームのマスクを読み込み
                    self._on_frame_changed(0)
                else:
                    logger.warning(f"Test input path not found: {test_input_path}")
            except Exception as e:
                logger.error(f"Failed to initialize input data source: {e}")
            
            self.status_message.show_message(tr("status.ready"), "info", 0)
            self.processing_indicator.stop_processing()
        else:
            QMessageBox.critical(
                self,
                tr("dialog.error"),
                tr("error.load_failed", reason="Failed to load video")
            )
            self.status_message.show_message(tr("status.ready"), "info", 0)
            self.processing_indicator.stop_processing()
    
    def _on_export_video(self) -> None:
        """動画をエクスポート"""
        # 将来実装
        pass
    
    def _on_undo(self) -> None:
        """元に戻す"""
        if self.current_project:
            history = self.current_project.undo()
            if history:
                logger.info(f"Undo: {history.action}")
                self._update_ui_state()
    
    def _on_redo(self) -> None:
        """やり直す"""
        if self.current_project:
            history = self.current_project.redo()
            if history:
                logger.info(f"Redo: {history.action}")
                self._update_ui_state()
    
    def _on_preferences(self) -> None:
        """環境設定"""
        # 将来実装
        pass
    
    def _on_zoom_in(self) -> None:
        """拡大"""
        current_zoom = self.video_preview.zoom_level
        self.video_preview.set_zoom(current_zoom * 1.25)
    
    def _on_zoom_out(self) -> None:
        """縮小"""
        current_zoom = self.video_preview.zoom_level
        self.video_preview.set_zoom(current_zoom / 1.25)
    
    def _on_zoom_fit(self) -> None:
        """画面に合わせる"""
        self.video_preview.fit_to_window_size()
    
    def _on_zoom_100(self) -> None:
        """100%表示"""
        self.video_preview.set_zoom(1.0)
    
    def _on_fullscreen(self, checked: bool) -> None:
        """フルスクリーン切り替え"""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()
    
    def _on_about(self) -> None:
        """About"""
        QMessageBox.about(
            self,
            tr("menu.help.about"),
            "<h2>Mask Editor Prototype</h2>"
            "<p>AI生成マスクの編集・エフェクト適用ツール</p>"
            "<p>Version 1.0.0</p>"
            "<p>© 2024 Mask Editor Prototype Project</p>"
        )
    
    def _on_play_pause(self, checked: bool) -> None:
        """再生/一時停止"""
        if checked:
            self.video_preview.play()
            self.action_play_pause.setText(tr("toolbar.pause"))
        else:
            self.video_preview.pause()
            self.action_play_pause.setText(tr("toolbar.play"))
    
    def _on_stop(self) -> None:
        """停止"""
        self.video_preview.stop()
        self.action_play_pause.setChecked(False)
        self.action_play_pause.setText(tr("toolbar.play"))
    
    def _on_previous_frame(self) -> None:
        """前のフレーム"""
        self.video_preview.previous_frame()
    
    def _on_next_frame(self) -> None:
        """次のフレーム"""
        self.video_preview.next_frame()
    
    def _on_frame_changed(self, frame_index: int) -> None:
        """フレーム変更時"""
        total_frames = self.video_preview.get_frame_count()
        self.frame_counter.set_frame_info(frame_index + 1, self.video_preview.get_frame_count())
        
        # タイムラインを同期
        self.timeline_widget.set_current_frame(frame_index)
        
        # マスクを読み込み
        if self.input_data_source:
            try:
                mask_data = self.input_data_source.get_mask(frame_index)
                if mask_data:
                    # MaskDTOに変換
                    mask_dto = MaskDTO(
                        frame_index=frame_index,
                        data=mask_data["data"],
                        width=mask_data["width"],
                        height=mask_data["height"],
                        object_ids=mask_data.get("object_ids", []),
                        classes=mask_data.get("classes", {}),
                        confidences=mask_data.get("confidences", {})
                    )
                    self.video_preview.set_mask(mask_dto)
                    self.mask_display_panel.set_mask(mask_dto)
                else:
                    # マスクがない場合はクリア
                    self.video_preview.set_mask(None)
                    self.mask_display_panel.set_mask(None)
                    
            except Exception as e:
                logger.error(f"Failed to load mask for frame {frame_index}: {e}")
    
    def _on_playback_started(self) -> None:
        """再生開始時"""
        self.status_message.show_message(tr("status.playing"), "info", 0)
    
    def _on_playback_stopped(self) -> None:
        """再生停止時"""
        self.status_message.show_message(tr("status.ready"), "info", 0)
    
    def _on_zoom_changed(self, zoom_level: float) -> None:
        """ズーム変更時"""
        self.zoom_level_label.setText(
            tr("status.zoom_level", zoom=int(zoom_level * 100))
        )
    
    def _on_timeline_frame_changed(self, frame_index: int) -> None:
        """タイムラインでフレームが変更された時"""
        # ビデオプレビューを同期
        if self.video_preview.media_reader:
            self.video_preview.seek_to_frame(frame_index)
    
    def _on_timeline_zoom_changed(self, zoom_level: float) -> None:
        """タイムラインのズームが変更された時"""
        # 必要に応じて他のUIを更新
        logger.debug(f"Timeline zoom changed: {zoom_level}")
    
    def _on_mask_clicked(self, mask_id: int, pos: QPoint) -> None:
        """マスクがクリックされた時"""
        logger.info(f"Mask {mask_id} clicked at {pos}")
        # マスク選択の処理（将来実装）
    
    def _on_morphology_requested(self, operation: str, kernel_size: int, preview: bool) -> None:
        """モルフォロジー操作がリクエストされた時"""
        logger.info(f"Morphology requested: {operation}, kernel={kernel_size}, preview={preview}")
        # モルフォロジー操作の処理（将来実装）
    
    def _on_morphology_applied(self, operation: str, kernel_size: int) -> None:
        """モルフォロジー操作が適用された時"""
        logger.info(f"Morphology applied: {operation}, kernel={kernel_size}")
        self.is_modified = True
        self._update_ui_state()
        # 実際の適用処理（将来実装）
    
    def _on_overlay_settings_changed(self, settings: MaskOverlaySettingsDTO) -> None:
        """オーバーレイ設定が変更された時"""
        self.video_preview.set_overlay_settings(settings)
    
    def _on_brush_config_changed(self, config: BrushConfigDTO) -> None:
        """ブラシ設定が変更された時"""
        if hasattr(self.video_preview, 'set_brush_config'):
            self.video_preview.set_brush_config(config)
    
    def _on_brush_undo(self) -> None:
        """ブラシのUndoが要求された時"""
        if hasattr(self, '_brush_history') and self._brush_history:
            stroke = self._brush_history.undo()
            if stroke:
                # マスクを再生成（実装は後で）
                logger.info("Brush undo performed")
                self._update_brush_ui_state()
    
    def _on_brush_redo(self) -> None:
        """ブラシのRedoが要求された時"""
        if hasattr(self, '_brush_history') and self._brush_history:
            stroke = self._brush_history.redo()
            if stroke:
                # マスクを再生成（実装は後で）
                logger.info("Brush redo performed")
                self._update_brush_ui_state()
    
    def _on_brush_clear(self) -> None:
        """ブラシのクリアが要求された時"""
        if hasattr(self, '_brush_history') and self._brush_history:
            self._brush_history.clear()
            logger.info("Brush history cleared")
            self._update_brush_ui_state()
    
    def _update_brush_ui_state(self) -> None:
        """ブラシUIの状態を更新"""
        if hasattr(self, '_brush_history') and hasattr(self.brush_panel, 'set_undo_enabled'):
            self.brush_panel.set_undo_enabled(self._brush_history.can_undo())
            self.brush_panel.set_redo_enabled(self._brush_history.can_redo())
    
    def _on_mask_visibility_changed(self, mask_id: int, visible: bool) -> None:
        """マスクの表示/非表示が変更された時"""
        self.video_preview.toggle_mask_visibility(mask_id, visible)
    
    def _on_mask_color_changed(self, mask_id: int, color: str) -> None:
        """マスクの色が変更された時"""
        self.video_preview.set_mask_color(mask_id, color)
    
    def _on_brush_stroke_completed(self, stroke: BrushStrokeDTO) -> None:
        """ブラシストロークが完了した時"""
        if hasattr(self, '_brush_history'):
            self._brush_history.add_stroke(stroke)
            self._update_brush_ui_state()
            self.is_modified = True
            self._update_ui_state()
            logger.info("Brush stroke completed")
    
    def _on_brush_mask_updated(self, mask: MaskDTO) -> None:
        """ブラシによってマスクが更新された時"""
        # マスクを更新
        self.mask_display_panel.set_mask(mask)
        self.is_modified = True
        self._update_ui_state()
        logger.debug("Mask updated by brush")
    
    def _on_effect_applied(self, config: EffectConfigDTO) -> None:
        """エフェクトが適用された時"""
        logger.info(f"Effect applied: {config.effect_type.value}")
        # エフェクト適用処理（将来実装）
        self.is_modified = True
        self._update_ui_state()
    
    def _on_effect_preview_requested(self) -> None:
        """エフェクトプレビューが要求された時"""
        logger.debug("Effect preview requested")
        # プレビュー更新処理（将来実装）
    
    def _on_project_opened(self, project: ProjectDTO) -> None:
        """プロジェクトが開かれた時（プロジェクトパネルから）"""
        # 既存のProjectクラスと互換性を保つための変換
        # TODO: 将来的にProjectDTOを直接使用するように変更
        self.current_project = Project(project.metadata.name)
        self.is_modified = False
        self.project_changed.emit(self.current_project)
        self._update_ui_state()
        
        # 動画も読み込み
        if project.source_video_path:
            self.video_preview.load_video(Path(project.source_video_path))
            # タイムラインを更新
            frame_count = self.video_preview.get_frame_count()
            fps = self.video_preview.get_fps()
            if frame_count > 0 and fps > 0:
                self.timeline_widget.set_timeline_info(frame_count, fps)
                # タイムライン状態を復元
                if project.timeline_state:
                    self.timeline_widget.set_frame_states(project.timeline_state.frame_states)
        
        logger.info(f"Project opened: {project.metadata.name}")
    
    def _on_project_saved(self, path: Path) -> None:
        """プロジェクトが保存された時（プロジェクトパネルから）"""
        self.is_modified = False
        self._update_ui_state()
        self.status_label.setText(tr("status.saved"))
        logger.info(f"Project saved: {path}")
    
    def _on_new_project(self) -> None:
        """新規プロジェクトが要求された時（プロジェクトパネルから）"""
        # 現在のプロジェクトをクリア
        self.current_project = None
        self.is_modified = False
        self.project_changed.emit(None)
        self._update_ui_state()
        
        # ビデオをクリア
        if self.video_preview.media_reader:
            self.video_preview.media_reader.close()
            self.video_preview.media_reader = None
            self.video_preview.update()
        
        # タイムラインをクリア
        self.timeline_widget.clear()
        
        logger.info("New project created")
    
    def _on_save_project(self) -> None:
        """プロジェクトを保存（メニューから）"""
        if not self.current_project:
            return
        
        # プロジェクトDTOを作成
        from domain.dto.project_dto import (
            ProjectDTO, ProjectMetadataDTO, TimelineStateDTO
        )
        import uuid
        
        # メタデータ作成
        metadata = ProjectMetadataDTO(
            name=self.current_project.name,
            id=str(uuid.uuid4()),
            format_version="1.0",
            author="Mask Editor Prototype User"
        )
        
        # タイムライン状態を取得
        timeline_state = None
        if hasattr(self.timeline_widget, 'get_frame_states'):
            frame_states = self.timeline_widget.get_frame_states()
            if frame_states:
                timeline_state = TimelineStateDTO(
                    frame_count=self.timeline_widget.frame_count,
                    current_frame=self.timeline_widget.current_frame,
                    frame_states=frame_states
                )
        
        # プロジェクトDTO作成
        project_dto = ProjectDTO(
            metadata=metadata,
            source_video_path=str(self.video_preview.current_video_path) if self.video_preview.current_video_path else None,
            timeline_state=timeline_state
        )
        
        # プロジェクトパネルに処理を委譲
        if hasattr(self.project_panel, 'set_project'):
            self.project_panel.set_project(project_dto)
            self.project_panel._on_save_as_project()
    
    def _confirm_discard_changes(self) -> bool:
        """変更を破棄することを確認
        
        Returns:
            続行する場合True
        """
        if not self.is_modified:
            return True
        
        reply = QMessageBox.question(
            self,
            tr("dialog.confirm"),
            "プロジェクトに未保存の変更があります。\n変更を破棄してもよろしいですか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """ウィンドウクローズイベント"""
        if not self._confirm_discard_changes():
            event.ignore()
            return
        
        # ウィンドウ状態を保存
        self._save_window_state()
        
        # リソースのクリーンアップ
        if self.video_preview.media_reader:
            self.video_preview.media_reader.close()
        
        event.accept()