#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改善されたメインウィンドウ

UIの重なりと操作性の問題を解決
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QDockWidget, QTabWidget, QWidget

from .main_window import MainWindow
from .i18n import tr
from .compact_panels import CompactBrushPanel
from .timeline_widget import TimelineWidget
from .mask_edit_panel import MaskEditPanel
from .mask_display_panel import MaskDisplayPanel
from .project_panel import ProjectManagementPanel
from .effect_panel import EffectPanel
from .compact_layout_config import CompactLayoutConfig, optimize_widget_for_compact_display
from domain.ports.secondary.project_ports import IProjectRepository, IProjectAutoSaver
from domain.ports.secondary.effect_ports import IEffectEngine, IEffectPresetManager, IEffectPreview


class ImprovedMainWindow(MainWindow):
    """改善されたメインウィンドウ
    
    UIレイアウトの問題を解決：
    - ドックウィジェットの重なりを解消
    - 適切なサイズ設定
    - タブ化による省スペース化
    """
    
    def __init__(self, di_container=None):
        """初期化
        
        Args:
            di_container: DIコンテナ
        """
        # パフォーマンスサービスを取得
        self.frame_throttle = None
        self.ui_optimizer = None
        
        if di_container:
            from domain.ports.secondary.performance_ports import IFrameThrottleService, IUIUpdateOptimizer
            try:
                self.frame_throttle = di_container.resolve(IFrameThrottleService)
                self.ui_optimizer = di_container.resolve(IUIUpdateOptimizer)
            except Exception as e:
                import logging
                logging.warning(f"Performance services not available: {e}")
        
        super().__init__(di_container)
    
    def _setup_docks(self) -> None:
        """ドックウィジェットをセットアップ（改善版）"""
        # カスタムドックウィジェットの代わりに標準のQDockWidgetを使用
        # （カスタムドックウィジェットが問題の原因の可能性があるため）
        
        # ============ 左側ドック ============
        # プロジェクトパネル
        self.project_dock = QDockWidget(tr("dock.project"), self)
        self.project_dock.setObjectName("ProjectDock")
        
        # プロジェクトパネルを作成
        if self.di_container:
            repository = self.di_container.resolve(IProjectRepository)
            auto_saver = self.di_container.resolve(IProjectAutoSaver)
            self.project_panel = ProjectManagementPanel(repository, auto_saver, parent=self.project_dock)
        else:
            # DIコンテナがない場合はダミーパネル
            self.project_panel = QWidget(self.project_dock)
        
        self.project_dock.setWidget(self.project_panel)
        self.project_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.project_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        
        # 適切なサイズ設定
        self.project_dock.setMinimumWidth(200)
        self.project_dock.setMaximumWidth(350)
        self.project_panel.setMinimumSize(200, 300)
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)
        
        # プロジェクトシグナル接続
        if hasattr(self.project_panel, 'project_new_requested'):
            self.project_panel.project_new_requested.connect(self._on_new_project)
            self.project_panel.project_opened.connect(self._on_project_opened)
            self.project_panel.project_saved.connect(self._on_project_saved)
        
        # ============ 右側ドック（タブ化） ============
        # まず各パネルを作成
        # マスク編集パネル
        self.mask_edit_panel = MaskEditPanel(self)
        
        # マスク表示パネル
        self.mask_display_panel = MaskDisplayPanel(self)
        
        # エフェクトパネル
        if self.di_container:
            effect_engine = self.di_container.resolve(IEffectEngine)
            preset_manager = self.di_container.resolve(IEffectPresetManager)
            effect_preview = self.di_container.resolve(IEffectPreview)
            self.effect_panel = EffectPanel(effect_engine, preset_manager, effect_preview, self)
        else:
            self.effect_panel = QWidget(self)
        
        # ブラシパネル（コンパクト版）
        self.brush_panel = CompactBrushPanel(self)
        
        # ID管理パネル
        if self.di_container:
            from domain.ports.secondary.id_management_ports import IIDManager, IThresholdManager, IIDPreview
            from ui.id_management_panel import IDManagementPanel
            id_manager = self.di_container.resolve(IIDManager)
            threshold_manager = self.di_container.resolve(IThresholdManager)
            id_preview = self.di_container.resolve(IIDPreview)
            self.id_management_panel = IDManagementPanel(id_manager, threshold_manager, id_preview, self)
        else:
            self.id_management_panel = QWidget(self)
        
        # タブウィジェットを作成して右側パネルをまとめる
        self.right_tab_widget = QTabWidget()
        self.right_tab_widget.setDocumentMode(True)
        self.right_tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        
        # 各パネルをタブに追加
        self.right_tab_widget.addTab(self.mask_edit_panel, tr("dock.mask_edit"))
        self.right_tab_widget.addTab(self.mask_display_panel, tr("dock.mask_display"))
        self.right_tab_widget.addTab(self.effect_panel, tr("dock.effects"))
        self.right_tab_widget.addTab(self.brush_panel, tr("dock.brush"))
        self.right_tab_widget.addTab(self.id_management_panel, tr("dock.id_management"))
        
        # 右側ドックコンテナ
        self.right_dock = QDockWidget(tr("dock.tools"), self)
        self.right_dock.setObjectName("RightDock")
        self.right_dock.setWidget(self.right_tab_widget)
        self.right_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.right_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        
        # 適切なサイズ設定
        self.right_dock.setMinimumWidth(300)
        self.right_dock.setMaximumWidth(450)
        self.right_tab_widget.setMinimumSize(300, 400)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)
        
        # パネルシグナル接続
        self._connect_panel_signals()
        
        # ============ 下部ドック ============
        # タイムライン
        self.timeline_dock = QDockWidget(tr("dock.timeline"), self)
        self.timeline_dock.setObjectName("TimelineDock")
        self.timeline_widget = TimelineWidget(self)
        self.timeline_dock.setWidget(self.timeline_widget)
        self.timeline_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.timeline_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        
        # 適切なサイズ設定
        self.timeline_dock.setMinimumHeight(100)
        self.timeline_dock.setMaximumHeight(200)
        self.timeline_widget.setMinimumHeight(100)
        
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.timeline_dock)
        
        # タイムラインシグナル接続
        self.timeline_widget.frameChanged.connect(self._on_timeline_frame_changed)
        self.timeline_widget.zoomChanged.connect(self._on_timeline_zoom_changed)
        
        # 初期のドックサイズ比率を設定
        self.resizeDocks(
            [self.project_dock, self.right_dock, self.timeline_dock],
            [250, 350, 150],
            Qt.Orientation.Horizontal
        )
    
    def _setup_ui(self) -> None:
        """UIをセットアップ（改善版）"""
        # 親クラスのsetup_uiを呼び出す前に、ウィンドウの初期サイズを設定
        self.resize(1200, 800)  # より適切なデフォルトサイズ
        self.setMinimumSize(1000, 600)  # 最小サイズを設定
        
        # 親クラスのUI設定を呼び出す
        super()._setup_ui()
    
    def _connect_dock_signals(self) -> None:
        """ドックシグナルの接続（タブ化対応）"""
        # タブが変更された時の処理
        if hasattr(self, 'right_tab_widget'):
            self.right_tab_widget.currentChanged.connect(self._on_right_tab_changed)
    
    def _on_right_tab_changed(self, index: int) -> None:
        """右側タブが変更された時"""
        # 必要に応じてタブ変更時の処理を追加
        pass
    
    def show_mask_edit_panel(self) -> None:
        """マスク編集パネルを表示"""
        if hasattr(self, 'right_tab_widget'):
            self.right_tab_widget.setCurrentWidget(self.mask_edit_panel)
            self.right_dock.raise_()
    
    def show_effect_panel(self) -> None:
        """エフェクトパネルを表示"""
        if hasattr(self, 'right_tab_widget'):
            self.right_tab_widget.setCurrentWidget(self.effect_panel)
            self.right_dock.raise_()
    
    def show_brush_panel(self) -> None:
        """ブラシパネルを表示"""
        if hasattr(self, 'right_tab_widget'):
            self.right_tab_widget.setCurrentWidget(self.brush_panel)
            self.right_dock.raise_()
    
    def show_id_management_panel(self) -> None:
        """ID管理パネルを表示"""
        if hasattr(self, 'right_tab_widget'):
            self.right_tab_widget.setCurrentWidget(self.id_management_panel)
            self.right_dock.raise_()
    
    def _connect_panel_signals(self) -> None:
        """パネルのシグナルを接続"""
        # マスク編集シグナル接続
        self.mask_edit_panel.morphology_requested.connect(self._on_morphology_requested)
        self.mask_edit_panel.morphology_applied.connect(self._on_morphology_applied)
        self.mask_edit_panel.undo_requested.connect(self._on_undo)
        self.mask_edit_panel.redo_requested.connect(self._on_redo)
        
        # マスク表示シグナル接続
        self.mask_display_panel.settings_changed.connect(self._on_overlay_settings_changed)
        self.mask_display_panel.mask_visibility_changed.connect(self._on_mask_visibility_changed)
        self.mask_display_panel.mask_color_changed.connect(self._on_mask_color_changed)
        
        # エフェクトシグナル接続
        if hasattr(self.effect_panel, 'effect_applied'):
            self.effect_panel.effect_applied.connect(self._on_effect_applied)
            self.effect_panel.preview_requested.connect(self._on_effect_preview_requested)
        
        # ブラシシグナル接続
        if hasattr(self.brush_panel, 'config_changed'):
            self.brush_panel.config_changed.connect(self._on_brush_config_changed)
            self.brush_panel.undo_requested.connect(self._on_brush_undo)
            self.brush_panel.redo_requested.connect(self._on_brush_redo)
            self.brush_panel.clear_requested.connect(self._on_brush_clear)
        
        # ID管理シグナル接続
        if hasattr(self.id_management_panel, 'ids_deleted'):
            self.id_management_panel.ids_deleted.connect(self._on_ids_deleted)
            self.id_management_panel.ids_merged.connect(self._on_ids_merged)
            self.id_management_panel.threshold_changed.connect(self._on_threshold_changed)
            self.id_management_panel.preview_requested.connect(self._on_id_preview_requested)
    
    def _on_ids_deleted(self, ids: list) -> None:
        """IDが削除された時の処理"""
        if hasattr(self.video_preview, 'current_mask_dto') and self.video_preview.current_mask_dto:
            # ID削除処理の実行
            from domain.ports.secondary.id_management_ports import IIDManager
            if self.di_container:
                id_manager = self.di_container.resolve(IIDManager)
                mask_dict = self.video_preview.current_mask_dto.to_dict()
                updated_mask_dict = id_manager.delete_ids(mask_dict, ids)
                
                # 更新されたマスクをDTOに変換
                from domain.dto.mask_dto import MaskDTO
                updated_mask_dto = MaskDTO.from_dict(updated_mask_dict)
                
                # ビデオプレビューを更新
                self.video_preview.set_mask(updated_mask_dto)
                
                # ID管理パネルを更新
                self.id_management_panel.set_mask(updated_mask_dto)
                
                # 変更フラグを設定
                self.is_modified = True
                self._update_ui_state()
    
    def _on_ids_merged(self, source_ids: list, target_id: int) -> None:
        """IDがマージされた時の処理"""
        if hasattr(self.video_preview, 'current_mask_dto') and self.video_preview.current_mask_dto:
            from domain.ports.secondary.id_management_ports import IIDManager
            if self.di_container:
                id_manager = self.di_container.resolve(IIDManager)
                mask_dict = self.video_preview.current_mask_dto.to_dict()
                updated_mask_dict = id_manager.merge_ids(mask_dict, source_ids, target_id)
                
                # 更新されたマスクをDTOに変換
                from domain.dto.mask_dto import MaskDTO
                updated_mask_dto = MaskDTO.from_dict(updated_mask_dict)
                
                # ビデオプレビューを更新
                self.video_preview.set_mask(updated_mask_dto)
                
                # ID管理パネルを更新
                self.id_management_panel.set_mask(updated_mask_dto)
                
                # 変更フラグを設定
                self.is_modified = True
                self._update_ui_state()
    
    def _on_threshold_changed(self, threshold_type: str, value: float) -> None:
        """閾値が変更された時の処理"""
        from domain.ports.secondary.id_management_ports import IThresholdManager
        if self.di_container:
            threshold_manager = self.di_container.resolve(IThresholdManager)
            
            if threshold_type == "detection":
                threshold_manager.set_detection_threshold(value)
            elif threshold_type == "merge":
                threshold_manager.set_merge_threshold(value)
            
            # プレビューを更新（必要に応じて）
            if self.id_management_panel.preview_check.isChecked():
                self._on_id_preview_requested()
    
    def _on_id_preview_requested(self) -> None:
        """IDプレビューが要求された時の処理"""
        # プレビュー更新処理（将来実装）
        pass
    
    # ========== パフォーマンス最適化 ==========
    
    def _on_frame_changed(self, frame_index: int) -> None:
        """フレーム変更時（パフォーマンス最適化版）
        
        Args:
            frame_index: フレーム番号
        """
        # 再生状態を取得
        is_playing = self.video_preview.is_playing() if hasattr(self.video_preview, 'is_playing') else False
        
        # フレームスロットリングを適用
        if self.frame_throttle:
            if not self.frame_throttle.should_update(frame_index, is_playing):
                # 更新をスキップ
                return
        
        # 親クラスの処理を実行
        super()._on_frame_changed(frame_index)
        
        # UI更新の最適化
        if self.ui_optimizer and is_playing:
            # 各コンポーネントの更新を制御
            if self.ui_optimizer.should_update_component("timeline", frame_index):
                self.timeline_widget.set_current_frame(frame_index)
            
            if self.ui_optimizer.should_update_component("id_management", frame_index):
                if hasattr(self, 'id_management_panel') and self.video_preview.current_mask_dto:
                    self.id_management_panel.set_mask(self.video_preview.current_mask_dto)
            
            if self.ui_optimizer.should_update_component("effect_panel", frame_index):
                if hasattr(self, 'effect_panel'):
                    # エフェクトパネルの更新（必要に応じて）
                    pass
    
    def _on_playback_started(self) -> None:
        """再生開始時の処理（最適化版）"""
        # UI最適化サービスに再生状態を通知
        if self.ui_optimizer:
            self.ui_optimizer.set_playing_state(True)
        
        # 親クラスの処理を実行
        super()._on_playback_started()
    
    def _on_playback_stopped(self) -> None:
        """再生停止時の処理（最適化版）"""
        # UI最適化サービスに再生状態を通知
        if self.ui_optimizer:
            self.ui_optimizer.set_playing_state(False)
            
            # 停止時は保留中のフレームを確実に更新
            if self.frame_throttle:
                pending_frame = self.frame_throttle.get_pending_frame()
                if pending_frame is not None:
                    super()._on_frame_changed(pending_frame)
        
        # 親クラスの処理を実行
        super()._on_playback_stopped()
    
    def show_performance_stats(self) -> None:
        """パフォーマンス統計を表示（デバッグ用）"""
        if not self.frame_throttle:
            return
        
        stats = self.frame_throttle.get_performance_stats()
        
        from PyQt6.QtWidgets import QMessageBox
        message = f"""
フレーム更新パフォーマンス統計:
- FPS制限: {stats['fps_limit']}
- 平均間隔: {stats['avg_interval_ms']:.1f}ms
- 実効FPS: {stats.get('effective_fps', 0):.1f}
- ドロップフレーム: {stats['dropped_frames']}
- ドロップ率: {stats['drop_rate']*100:.1f}%
"""
        QMessageBox.information(self, "パフォーマンス統計", message)