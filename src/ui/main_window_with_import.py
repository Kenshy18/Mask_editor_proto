#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
インポート機能を追加したメインウィンドウ

ディレクトリ一括読み込みと個別インポート機能を実装
"""
from pathlib import Path
from PyQt6.QtWidgets import QMenu, QFileDialog, QMessageBox
from PyQt6.QtGui import QKeySequence, QAction
from PyQt6.QtCore import pyqtSignal
import logging

from .improved_main_window import ImprovedMainWindow as MainWindow
from .i18n import tr
from domain.ports.secondary.input_data_ports import IInputDataSource
from infrastructure.adapters.input_data_source_factory import InputDataSourceFactory

logger = logging.getLogger(__name__)


class MainWindowWithImport(MainWindow):
    """インポート機能を追加したメインウィンドウ
    
    ディレクトリからの一括読み込みと個別ファイルインポートをサポート
    """
    
    # シグナル
    directory_loaded = pyqtSignal(str)  # ディレクトリパス
    json_imported = pyqtSignal(str)     # JSONファイルパス  
    masks_imported = pyqtSignal(str)    # マスクディレクトリパス
    
    def __init__(self, di_container=None):
        """初期化"""
        # 現在のデータソース情報
        self.current_directory = None
        self.current_video_path = None
        self.current_json_path = None
        self.current_mask_dir = None
        
        super().__init__(di_container)
    
    def _setup_menus(self) -> None:
        """メニューバーをセットアップ（拡張版）"""
        super()._setup_menus()
        
        # ファイルメニューを取得
        menubar = self.menuBar()
        file_menu = None
        for action in menubar.actions():
            if action.menu() and action.text() == tr("menu.file"):
                file_menu = action.menu()
                break
        
        if not file_menu:
            return
        
        # 「動画をインポート」の後に新しいメニュー項目を追加
        import_video_action = None
        for action in file_menu.actions():
            if action.text() == tr("menu.file.import_video"):
                import_video_action = action
                break
        
        if import_video_action:
            # ディレクトリから一括読み込み
            self.action_load_directory = QAction(tr("menu.file.load_directory"), self)
            self.action_load_directory.setShortcut(QKeySequence("Ctrl+D"))
            self.action_load_directory.triggered.connect(self._on_load_directory)
            file_menu.insertAction(import_video_action, self.action_load_directory)
            
            file_menu.insertSeparator(import_video_action)
            
            # インポートサブメニューを作成
            import_menu = QMenu(tr("menu.file.import"), self)
            
            # 検出結果（JSON）をインポート
            self.action_import_json = QAction(tr("menu.file.import_json"), self)
            self.action_import_json.triggered.connect(self._on_import_json)
            import_menu.addAction(self.action_import_json)
            
            # マスクディレクトリをインポート
            self.action_import_masks = QAction(tr("menu.file.import_masks"), self)
            self.action_import_masks.triggered.connect(self._on_import_masks) 
            import_menu.addAction(self.action_import_masks)
            
            # インポートメニューを追加
            file_menu.insertMenu(import_video_action, import_menu)
            file_menu.insertSeparator(import_video_action)
    
    def _setup_dock_widgets(self) -> None:
        """ドックウィジェットをセットアップ（拡張版）"""
        super()._setup_dock_widgets()
        
        # ブラシドックの表示/非表示でブラシモードを切り替え
        if hasattr(self, 'brush_dock'):
            self.brush_dock.visibilityChanged.connect(self._on_brush_dock_visibility_changed)
    
    def _on_brush_dock_visibility_changed(self, visible: bool) -> None:
        """ブラシドックの表示状態が変更された時"""
        if hasattr(self.video_preview, 'set_brush_enabled'):
            self.video_preview.set_brush_enabled(visible)
            if visible:
                logger.info("Brush mode enabled")
            else:
                logger.info("Brush mode disabled")
    
    def _on_load_directory(self) -> None:
        """ディレクトリから一括読み込み"""
        # ディレクトリ選択ダイアログ
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("dialog.select_directory"),
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not directory:
            return
        
        directory_path = Path(directory)
        
        try:
            # ディレクトリ内のファイルを検索
            video_files = list(directory_path.glob("*.mp4")) + \
                         list(directory_path.glob("*.avi")) + \
                         list(directory_path.glob("*.mov"))
            json_files = list(directory_path.glob("*.json"))
            
            # マスクディレクトリを検索（一般的な名前）
            mask_dirs = []
            for name in ["filtered", "masks", "mask", "segmentation"]:
                mask_dir = directory_path / name
                if mask_dir.exists() and mask_dir.is_dir():
                    mask_dirs.append(mask_dir)
            
            # ファイルが見つからない場合
            if not video_files:
                QMessageBox.warning(
                    self,
                    tr("dialog.warning"),
                    tr("error.no_video_found")
                )
                return
            
            if not json_files:
                QMessageBox.warning(
                    self,
                    tr("dialog.warning"), 
                    tr("error.no_json_found")
                )
                return
            
            if not mask_dirs:
                QMessageBox.warning(
                    self,
                    tr("dialog.warning"),
                    tr("error.no_mask_dir_found")
                )
                return
            
            # 複数ファイルがある場合は選択
            video_file = video_files[0]
            if len(video_files) > 1:
                # TODO: 選択ダイアログを表示
                pass
            
            json_file = json_files[0]
            if len(json_files) > 1:
                # 'genitile'を含むファイルを優先
                for f in json_files:
                    if 'genitile' in f.name.lower():
                        json_file = f
                        break
            
            mask_dir = mask_dirs[0]
            
            # データソースを作成
            self._load_data_source(
                base_path=directory_path,
                video_file=video_file.name,
                json_file=json_file.name,
                mask_dir=mask_dir.name
            )
            
            # 成功メッセージ
            QMessageBox.information(
                self,
                tr("dialog.success"),
                tr("status.directory_loaded", directory=directory)
            )
            
            # 状態を保存
            self.current_directory = directory_path
            self.current_video_path = video_file
            self.current_json_path = json_file
            self.current_mask_dir = mask_dir
            
            # シグナルを発行
            self.directory_loaded.emit(str(directory_path))
            
        except Exception as e:
            logger.error(f"Failed to load directory: {e}")
            QMessageBox.critical(
                self,
                tr("dialog.error"),
                tr("error.load_directory_failed", reason=str(e))
            )
    
    def _on_import_json(self) -> None:
        """検出結果（JSON）をインポート"""
        if not self.current_video_path:
            QMessageBox.warning(
                self,
                tr("dialog.warning"),
                tr("error.load_video_first")
            )
            return
        
        # ファイル選択ダイアログ
        json_file, _ = QFileDialog.getOpenFileName(
            self,
            tr("dialog.select_json"),
            str(Path.home()),
            "JSON Files (*.json)"
        )
        
        if not json_file:
            return
        
        try:
            json_path = Path(json_file)
            
            # 現在のデータソースを更新
            if self.current_directory and self.current_mask_dir:
                self._load_data_source(
                    base_path=self.current_directory,
                    video_file=self.current_video_path.name,
                    json_file=json_path.name if json_path.parent == self.current_directory else str(json_path),
                    mask_dir=self.current_mask_dir.name
                )
                
                self.current_json_path = json_path
                
                # シグナルを発行
                self.json_imported.emit(str(json_path))
                
                QMessageBox.information(
                    self,
                    tr("dialog.success"),
                    tr("status.json_imported", file=json_path.name)
                )
            
        except Exception as e:
            logger.error(f"Failed to import JSON: {e}")
            QMessageBox.critical(
                self,
                tr("dialog.error"),
                tr("error.import_json_failed", reason=str(e))
            )
    
    def _on_import_masks(self) -> None:
        """マスクディレクトリをインポート"""
        if not self.current_video_path:
            QMessageBox.warning(
                self,
                tr("dialog.warning"),
                tr("error.load_video_first")
            )
            return
        
        # ディレクトリ選択ダイアログ
        mask_dir = QFileDialog.getExistingDirectory(
            self,
            tr("dialog.select_mask_dir"),
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not mask_dir:
            return
        
        try:
            mask_path = Path(mask_dir)
            
            # マスクファイルの存在確認
            mask_files = list(mask_path.glob("*.png")) + list(mask_path.glob("*.npy"))
            if not mask_files:
                QMessageBox.warning(
                    self,
                    tr("dialog.warning"),
                    tr("error.no_mask_files")
                )
                return
            
            # 現在のデータソースを更新
            if self.current_directory and self.current_json_path:
                self._load_data_source(
                    base_path=self.current_directory,
                    video_file=self.current_video_path.name,
                    json_file=self.current_json_path.name if self.current_json_path.parent == self.current_directory else str(self.current_json_path),
                    mask_dir=mask_path.name if mask_path.parent == self.current_directory else str(mask_path)
                )
                
                self.current_mask_dir = mask_path
                
                # シグナルを発行
                self.masks_imported.emit(str(mask_path))
                
                QMessageBox.information(
                    self,
                    tr("dialog.success"),
                    tr("status.masks_imported", directory=mask_path.name)
                )
            
        except Exception as e:
            logger.error(f"Failed to import masks: {e}")
            QMessageBox.critical(
                self,
                tr("dialog.error"),
                tr("error.import_masks_failed", reason=str(e))
            )
    
    def _load_data_source(self, base_path: Path, video_file: str, json_file: str, mask_dir: str) -> None:
        """データソースを読み込み"""
        try:
            # 新しいデータソースを作成
            config = {
                "base_path": str(base_path),
                "video_file": video_file,
                "detections_file": json_file,
                "mask_directory": mask_dir
            }
            
            # LocalFileInputAdapterを直接作成
            from adapters.secondary.local_file_input_adapter import LocalFileInputAdapter
            adapter = LocalFileInputAdapter()
            adapter.initialize(config)
            self.input_data_source = adapter
            
            # ブラシモードを無効化（存在する場合）
            if hasattr(self.video_preview, 'set_brush_enabled'):
                self.video_preview.set_brush_enabled(False)
                logger.debug("Brush mode disabled")
            
            # 動画を読み込み
            video_path = Path(base_path) / video_file
            if hasattr(self, 'video_preview') and self.video_preview:
                success = self.video_preview.load_video(str(video_path))
                if success:
                    logger.info(f"Video loaded successfully: {video_path}")
                    
                    # タイムラインを更新
                    frame_count = self.video_preview.get_frame_count()
                    fps = self.video_preview.get_fps()
                    if frame_count > 0 and fps > 0 and hasattr(self, 'timeline_widget'):
                        self.timeline_widget.set_timeline_info(frame_count, fps)
                        logger.info(f"Timeline updated: {frame_count} frames at {fps} fps")
                else:
                    logger.error(f"Failed to load video: {video_path}")
            
            # 最初のフレームを表示してマスクを読み込み
            if self.input_data_source and hasattr(self, 'video_preview'):
                # フレーム0を表示
                self.video_preview.seek_to_frame(0)
                # マスクを読み込み
                self._on_frame_changed(0)
                logger.info("Initial frame and mask loaded")
            
            logger.info(f"Data source loaded successfully: {base_path}")
            
        except Exception as e:
            logger.error(f"Failed to load data source: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _on_import_video(self) -> None:
        """動画をインポート（オーバーライド）"""
        # ファイル選択ダイアログ
        video_file, _ = QFileDialog.getOpenFileName(
            self,
            tr("dialog.select_video"),
            str(Path.home()),
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if not video_file:
            return
        
        video_path = Path(video_file)
        
        # 現在の状態をリセット
        self.current_directory = video_path.parent
        self.current_video_path = video_path
        self.current_json_path = None
        self.current_mask_dir = None
        self.input_data_source = None
        
        # 動画を読み込み
        if hasattr(self, 'video_preview') and self.video_preview:
            self.video_preview.load_video(str(video_path))
            # タイムラインを更新
            frame_count = self.video_preview.get_frame_count()
            fps = self.video_preview.get_fps()
            if frame_count > 0 and fps > 0 and hasattr(self, 'timeline_widget'):
                self.timeline_widget.set_timeline_info(frame_count, fps)
        
        # 同じディレクトリ内でJSONとマスクを探す
        self._auto_detect_files(video_path.parent)
    
    def _auto_detect_files(self, directory: Path) -> None:
        """ディレクトリ内でJSONとマスクディレクトリを自動検出"""
        try:
            # JSONファイルを検索
            json_files = list(directory.glob("*.json"))
            if json_files:
                # genitileを含むファイルを優先
                json_file = None
                for f in json_files:
                    if 'genitile' in f.name.lower() or 'genital' in f.name.lower():
                        json_file = f
                        break
                if not json_file:
                    json_file = json_files[0]
                
                self.current_json_path = json_file
                logger.info(f"Auto-detected JSON: {json_file.name}")
            
            # マスクディレクトリを検索
            for name in ["filtered", "masks", "mask", "segmentation"]:
                mask_dir = directory / name
                if mask_dir.exists() and mask_dir.is_dir():
                    # マスクファイルがあるか確認
                    mask_files = list(mask_dir.glob("*.png")) + list(mask_dir.glob("*.npy"))
                    if mask_files:
                        self.current_mask_dir = mask_dir
                        logger.info(f"Auto-detected mask directory: {mask_dir.name}")
                        break
            
            # 両方見つかった場合は自動的に読み込み
            if self.current_json_path and self.current_mask_dir:
                self._load_data_source(
                    base_path=directory,
                    video_file=self.current_video_path.name,
                    json_file=self.current_json_path.name,
                    mask_dir=self.current_mask_dir.name
                )
                
                # 通知
                QMessageBox.information(
                    self,
                    tr("dialog.info"),
                    tr("status.auto_detected_files")
                )
        except Exception as e:
            logger.warning(f"Auto-detection failed: {e}")