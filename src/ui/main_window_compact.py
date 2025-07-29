#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コンパクトメインウィンドウ

画面に収まるように最適化されたメインウィンドウ
"""
from __future__ import annotations

import logging
from typing import Optional
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QSplitter, QTabWidget, QPushButton,
    QToolBar, QStatusBar
)
from PyQt6.QtGui import QAction, QKeySequence

from .main_window import MainWindow
from .compact_layout_config import CompactLayoutConfig
from .compact_panels import CompactBrushPanel
from .i18n import tr
from .icon_manager import get_icon_manager

logger = logging.getLogger(__name__)


class CompactMainWindow(MainWindow):
    """コンパクトメインウィンドウ
    
    よりコンパクトなレイアウトを実現するための拡張メインウィンドウ
    """
    
    def _setup_ui(self) -> None:
        """UIをセットアップ（コンパクト版）"""
        # メインスプリッター
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)
        
        # 左側：プロジェクト＋タイムライン（タブ化）
        left_tab_widget = QTabWidget()
        left_tab_widget.setMaximumWidth(250)
        left_tab_widget.setDocumentMode(True)
        
        # プロジェクトパネル
        if self.di_container:
            from domain.ports.secondary.project_ports import IProjectRepository, IProjectAutoSaver
            repository = self.di_container.resolve(IProjectRepository)
            auto_saver = self.di_container.resolve(IProjectAutoSaver)
            from .project_panel import ProjectManagementPanel
            self.project_panel = ProjectManagementPanel(repository, auto_saver)
        else:
            self.project_panel = QWidget()
        
        # タイムラインウィジェット
        from .timeline_widget import TimelineWidget
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setMaximumWidth(250)
        
        left_tab_widget.addTab(self.project_panel, tr("dock.project"))
        left_tab_widget.addTab(self.timeline_widget, tr("dock.timeline"))
        
        self.main_splitter.addWidget(left_tab_widget)
        
        # 中央：ビデオプレビュー
        # ブラシエンジンの初期化（親クラスから）
        if self.di_container:
            try:
                from domain.ports.secondary.brush_ports import IBrushEngine, IBrushPreview, IBrushHistory
                self._brush_engine = self.di_container.resolve(IBrushEngine)
                self._brush_preview = self.di_container.resolve(IBrushPreview)
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
        else:
            from .video_with_mask_widget import VideoWithMaskWidget
            self.video_preview = VideoWithMaskWidget(self)
        
        self.main_splitter.addWidget(self.video_preview)
        
        # 右側：編集ツール（タブ化）
        right_tab_widget = QTabWidget()
        right_tab_widget.setMaximumWidth(300)
        right_tab_widget.setDocumentMode(True)
        
        # マスク編集パネル
        from .mask_edit_panel import MaskEditPanel
        self.mask_edit_panel = MaskEditPanel()
        
        # マスク表示パネル
        from .mask_display_panel import MaskDisplayPanel
        self.mask_display_panel = MaskDisplayPanel()
        
        # エフェクトパネル
        if self.di_container:
            from domain.ports.secondary.effect_ports import IEffectEngine, IEffectPresetManager, IEffectPreview
            effect_engine = self.di_container.resolve(IEffectEngine)
            preset_manager = self.di_container.resolve(IEffectPresetManager)
            effect_preview = self.di_container.resolve(IEffectPreview)
            from .effect_panel import EffectPanel
            self.effect_panel = EffectPanel(effect_engine, preset_manager, effect_preview)
        else:
            self.effect_panel = QWidget()
        
        # ブラシパネル（コンパクト版）
        self.brush_panel = CompactBrushPanel()
        
        # タブに追加
        right_tab_widget.addTab(self.mask_edit_panel, tr("dock.mask_edit"))
        right_tab_widget.addTab(self.mask_display_panel, tr("dock.mask_display"))
        right_tab_widget.addTab(self.effect_panel, tr("dock.effects"))
        right_tab_widget.addTab(self.brush_panel, tr("dock.brush"))
        
        self.main_splitter.addWidget(right_tab_widget)
        
        # スプリッターのサイズ設定
        self.main_splitter.setSizes([250, 500, 300])
        
        # コンパクトレイアウト設定を適用
        CompactLayoutConfig.apply_compact_window_settings(self)
        
        # シグナル接続
        self._connect_signals()
        
    def _setup_docks(self) -> None:
        """ドックウィジェットをセットアップしない（タブ化のため）"""
        pass
        
    def _setup_toolbars(self) -> None:
        """ツールバーをセットアップ（コンパクト版）"""
        # メインツールバー（アイコンのみ）
        main_toolbar = self.addToolBar(tr("toolbar.main"))
        main_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        main_toolbar.setIconSize(QSize(20, 20))
        main_toolbar.setMovable(False)
        
        # 基本的なアクションのみ追加
        icon_manager = get_icon_manager()
        
        # ファイル操作
        action_new = main_toolbar.addAction(icon_manager.get_icon("document-new"), "")
        action_new.setToolTip(tr("menu.file.new_project"))
        action_new.triggered.connect(self._on_new_project)
        
        action_open = main_toolbar.addAction(icon_manager.get_icon("document-open"), "")
        action_open.setToolTip(tr("menu.file.open_project"))
        action_open.triggered.connect(self._on_open_project)
        
        action_save = main_toolbar.addAction(icon_manager.get_icon("document-save"), "")
        action_save.setToolTip(tr("menu.file.save_project"))
        action_save.triggered.connect(self._on_save_project)
        
        main_toolbar.addSeparator()
        
        # 編集操作（既存のアクションを使用）
        if hasattr(self, 'action_undo'):
            self.action_undo.setIcon(icon_manager.get_icon("edit-undo", size=QSize(20, 20)))
            main_toolbar.addAction(self.action_undo)
        else:
            self.action_undo = main_toolbar.addAction(icon_manager.get_icon("edit-undo", size=QSize(20, 20)), "")
            self.action_undo.setToolTip(tr("menu.edit.undo"))
            self.action_undo.triggered.connect(self._on_undo)
        
        if hasattr(self, 'action_redo'):
            self.action_redo.setIcon(icon_manager.get_icon("edit-redo", size=QSize(20, 20)))
            main_toolbar.addAction(self.action_redo)
        else:
            self.action_redo = main_toolbar.addAction(icon_manager.get_icon("edit-redo", size=QSize(20, 20)), "")
            self.action_redo.setToolTip(tr("menu.edit.redo"))
            self.action_redo.triggered.connect(self._on_redo)
        
        main_toolbar.addSeparator()
        
        # 再生制御アクション（親クラスとの互換性のため必要）
        self.action_play_pause = QAction(tr("toolbar.play"), self)
        self.action_play_pause.setIcon(icon_manager.get_icon("media-playback-start", size=QSize(20, 20)))
        self.action_play_pause.setShortcut(QKeySequence("Space"))
        self.action_play_pause.setCheckable(True)
        self.action_play_pause.triggered.connect(self._on_play_pause)
        main_toolbar.addAction(self.action_play_pause)
        
        self.action_stop = main_toolbar.addAction(icon_manager.get_icon("media-playback-stop", size=QSize(20, 20)), "")
        self.action_stop.setToolTip(tr("toolbar.stop"))
        self.action_stop.triggered.connect(self._on_stop)
        
        self.action_previous_frame = main_toolbar.addAction(icon_manager.get_icon("media-skip-backward", size=QSize(20, 20)), "")
        self.action_previous_frame.setToolTip(tr("toolbar.previous_frame"))
        self.action_previous_frame.triggered.connect(self._on_previous_frame)
        
        self.action_next_frame = main_toolbar.addAction(icon_manager.get_icon("media-skip-forward", size=QSize(20, 20)), "")
        self.action_next_frame.setToolTip(tr("toolbar.next_frame"))
        self.action_next_frame.triggered.connect(self._on_next_frame)
        
    def _setup_statusbar(self) -> None:
        """ステータスバーをセットアップ（コンパクト版）"""
        statusbar = self.statusBar()
        statusbar.setMaximumHeight(22)
        statusbar.setContentsMargins(2, 0, 2, 0)
        
        # 簡易ステータス表示のみ
        from PyQt6.QtWidgets import QLabel
        self.status_label = QLabel(tr("status.ready"))
        statusbar.addWidget(self.status_label)
        
        # フレーム情報
        self.frame_label = QLabel()
        statusbar.addPermanentWidget(self.frame_label)
        
    def _connect_signals(self) -> None:
        """シグナルを接続"""
        # タイムライン
        if hasattr(self, 'timeline_widget'):
            self.timeline_widget.frameChanged.connect(self._on_timeline_frame_changed)
            
        # マスク編集
        if hasattr(self, 'mask_edit_panel'):
            self.mask_edit_panel.morphology_requested.connect(self._on_morphology_requested)
            self.mask_edit_panel.undo_requested.connect(self._on_undo)
            self.mask_edit_panel.redo_requested.connect(self._on_redo)
            
        # マスク表示
        if hasattr(self, 'mask_display_panel'):
            self.mask_display_panel.settings_changed.connect(self._on_overlay_settings_changed)
            self.mask_display_panel.mask_visibility_changed.connect(self._on_mask_visibility_changed)
            
        # エフェクト
        if hasattr(self.effect_panel, 'effect_applied'):
            self.effect_panel.effect_applied.connect(self._on_effect_applied)
            
        # ブラシ
        if hasattr(self, 'brush_panel'):
            self.brush_panel.config_changed.connect(self._on_brush_config_changed)
            self.brush_panel.undo_requested.connect(self._on_brush_undo)
            self.brush_panel.redo_requested.connect(self._on_brush_redo)
    
    def _update_resource_status(self) -> None:
        """リソース状態を更新（コンパクト版では無効）"""
        pass
    
    def _setup_resource_monitor(self) -> None:
        """リソースモニターをセットアップ（コンパクト版では無効）"""
        pass