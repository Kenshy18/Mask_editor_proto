#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プロジェクト管理パネル

プロジェクトの保存、読み込み、管理機能を提供するUIパネル。
"""
from typing import Optional, Callable
from pathlib import Path
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGroupBox, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from domain.dto.project_dto import ProjectDTO
from domain.ports.secondary.project_ports import IProjectRepository, IProjectAutoSaver
from .i18n import tr

logger = logging.getLogger(__name__)


class ProjectManagementPanel(QWidget):
    """プロジェクト管理パネル"""
    
    # シグナル定義
    project_new_requested = pyqtSignal()
    project_opened = pyqtSignal(ProjectDTO)
    project_saved = pyqtSignal(Path)
    
    def __init__(
        self, 
        repository: IProjectRepository,
        auto_saver: IProjectAutoSaver,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.repository = repository
        self.auto_saver = auto_saver
        self.current_project: Optional[ProjectDTO] = None
        self.current_project_path: Optional[Path] = None
        
        self._setup_ui()
        self._setup_auto_save_timer()
    
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        
        # プロジェクト情報
        self.project_info_group = self._create_project_info_group()
        layout.addWidget(self.project_info_group)
        
        # アクションボタン
        self.action_buttons = self._create_action_buttons()
        layout.addLayout(self.action_buttons)
        
        # 最近のプロジェクト
        self.recent_projects_group = self._create_recent_projects_group()
        layout.addWidget(self.recent_projects_group)
        
        # 自動保存状態
        self.auto_save_group = self._create_auto_save_group()
        layout.addWidget(self.auto_save_group)
        
        layout.addStretch()
    
    def _create_project_info_group(self) -> QGroupBox:
        """プロジェクト情報グループを作成"""
        group = QGroupBox(tr("project.info.title"))
        layout = QVBoxLayout(group)
        
        # プロジェクト名
        self.project_name_label = QLabel(tr("project.info.no_project"))
        self.project_name_label.setWordWrap(True)
        layout.addWidget(self.project_name_label)
        
        # ファイルパス
        self.project_path_label = QLabel("")
        self.project_path_label.setWordWrap(True)
        self.project_path_label.setStyleSheet("color: gray;")
        layout.addWidget(self.project_path_label)
        
        # 最終更新
        self.last_modified_label = QLabel("")
        self.last_modified_label.setStyleSheet("color: gray;")
        layout.addWidget(self.last_modified_label)
        
        return group
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """アクションボタンを作成"""
        layout = QHBoxLayout()
        
        # 新規作成
        self.new_button = QPushButton(tr("project.action.new"))
        self.new_button.clicked.connect(self._on_new_project)
        layout.addWidget(self.new_button)
        
        # 開く
        self.open_button = QPushButton(tr("project.action.open"))
        self.open_button.clicked.connect(self._on_open_project)
        layout.addWidget(self.open_button)
        
        # 保存
        self.save_button = QPushButton(tr("project.action.save"))
        self.save_button.clicked.connect(self._on_save_project)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)
        
        # 名前を付けて保存
        self.save_as_button = QPushButton(tr("project.action.save_as"))
        self.save_as_button.clicked.connect(self._on_save_as_project)
        self.save_as_button.setEnabled(False)
        layout.addWidget(self.save_as_button)
        
        return layout
    
    def _create_recent_projects_group(self) -> QGroupBox:
        """最近のプロジェクトグループを作成"""
        group = QGroupBox(tr("project.recent.title"))
        layout = QVBoxLayout(group)
        
        # 最近のプロジェクトリスト
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(150)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_item_clicked)
        layout.addWidget(self.recent_list)
        
        # 更新ボタン
        self.refresh_recent_button = QPushButton(tr("project.recent.refresh"))
        self.refresh_recent_button.clicked.connect(self._refresh_recent_projects)
        layout.addWidget(self.refresh_recent_button)
        
        # 初回読み込み
        self._refresh_recent_projects()
        
        return group
    
    def _create_auto_save_group(self) -> QGroupBox:
        """自動保存グループを作成"""
        group = QGroupBox(tr("project.autosave.title"))
        layout = QVBoxLayout(group)
        
        # 自動保存状態
        self.auto_save_status_label = QLabel(tr("project.autosave.disabled"))
        layout.addWidget(self.auto_save_status_label)
        
        # 次回保存までの時間
        self.auto_save_timer_label = QLabel("")
        layout.addWidget(self.auto_save_timer_label)
        
        # プログレスバー
        self.auto_save_progress = QProgressBar()
        self.auto_save_progress.setTextVisible(False)
        self.auto_save_progress.setMaximum(100)
        layout.addWidget(self.auto_save_progress)
        
        return group
    
    def _setup_auto_save_timer(self) -> None:
        """自動保存タイマーをセットアップ"""
        self.auto_save_update_timer = QTimer(self)
        self.auto_save_update_timer.timeout.connect(self._update_auto_save_status)
        self.auto_save_update_timer.start(1000)  # 1秒ごとに更新
    
    def set_project(self, project: ProjectDTO, path: Optional[Path] = None) -> None:
        """
        現在のプロジェクトを設定
        
        Args:
            project: プロジェクトDTO
            path: プロジェクトファイルのパス
        """
        self.current_project = project
        self.current_project_path = path
        
        # UI更新
        self._update_project_info()
        self.save_button.setEnabled(path is not None)
        self.save_as_button.setEnabled(True)
        
        # 自動保存開始
        if self.auto_saver and path:
            self.auto_saver.set_autosave_path(path.with_suffix('.autosave'))
            self.auto_saver.start(project)
    
    def update_project(self, project: ProjectDTO) -> None:
        """
        プロジェクトデータを更新（自動保存用）
        
        Args:
            project: 更新されたプロジェクトDTO
        """
        self.current_project = project
        
        if self.auto_saver and hasattr(self.auto_saver, 'update_project'):
            self.auto_saver.update_project(project)
    
    def _update_project_info(self) -> None:
        """プロジェクト情報を更新"""
        if self.current_project:
            self.project_name_label.setText(
                f"<b>{self.current_project.metadata.name}</b>"
            )
            
            if self.current_project_path:
                self.project_path_label.setText(str(self.current_project_path))
            else:
                self.project_path_label.setText(tr("project.info.unsaved"))
            
            self.last_modified_label.setText(
                f"{tr('project.info.last_modified')}: "
                f"{self.current_project.metadata.updated_at}"
            )
        else:
            self.project_name_label.setText(tr("project.info.no_project"))
            self.project_path_label.setText("")
            self.last_modified_label.setText("")
    
    def _on_new_project(self) -> None:
        """新規プロジェクト作成"""
        # 保存確認
        if not self._confirm_discard_changes():
            return
        
        # 自動保存停止
        if self.auto_saver.is_running():
            self.auto_saver.stop()
        
        # シグナル発信
        self.project_new_requested.emit()
    
    def _on_open_project(self) -> None:
        """プロジェクトを開く"""
        # 保存確認
        if not self._confirm_discard_changes():
            return
        
        # ファイル選択
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("project.dialog.open_title"),
            "",
            tr("project.dialog.filter")
        )
        
        if not path:
            return
        
        self._open_project_file(Path(path))
    
    def _on_save_project(self) -> None:
        """プロジェクトを保存"""
        if not self.current_project or not self.current_project_path:
            return
        
        try:
            # 保存実行
            self.repository.save(self.current_project, self.current_project_path)
            
            # 成功通知
            self.project_saved.emit(self.current_project_path)
            logger.info(f"プロジェクトを保存しました: {self.current_project_path}")
            
        except Exception as e:
            logger.error(f"プロジェクト保存エラー: {e}")
            QMessageBox.critical(
                self,
                tr("project.error.save_title"),
                tr("project.error.save_message").format(error=str(e))
            )
    
    def _on_save_as_project(self) -> None:
        """名前を付けて保存"""
        if not self.current_project:
            return
        
        # ファイル選択
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("project.dialog.save_title"),
            self.current_project.metadata.name + ".mosaicproj",
            tr("project.dialog.filter")
        )
        
        if not path:
            return
        
        path = Path(path)
        if not path.suffix:
            path = path.with_suffix('.mosaicproj')
        
        try:
            # 保存実行
            self.repository.save(self.current_project, path)
            
            # 現在のパスを更新
            self.current_project_path = path
            self.save_button.setEnabled(True)
            self._update_project_info()
            
            # 自動保存パス更新
            if self.auto_saver.is_running():
                self.auto_saver.set_autosave_path(path.with_suffix('.autosave'))
            
            # 成功通知
            self.project_saved.emit(path)
            logger.info(f"プロジェクトを保存しました: {path}")
            
        except Exception as e:
            logger.error(f"プロジェクト保存エラー: {e}")
            QMessageBox.critical(
                self,
                tr("project.error.save_title"),
                tr("project.error.save_message").format(error=str(e))
            )
    
    def _open_project_file(self, path: Path) -> None:
        """プロジェクトファイルを開く"""
        try:
            # 読み込み実行
            project = self.repository.load(path)
            
            # 自動保存停止
            if self.auto_saver.is_running():
                self.auto_saver.stop()
            
            # プロジェクト設定
            self.set_project(project, path)
            
            # シグナル発信
            self.project_opened.emit(project)
            
            # 最近のプロジェクトリスト更新
            self._refresh_recent_projects()
            
            logger.info(f"プロジェクトを開きました: {path}")
            
        except Exception as e:
            logger.error(f"プロジェクト読み込みエラー: {e}")
            QMessageBox.critical(
                self,
                tr("project.error.open_title"),
                tr("project.error.open_message").format(error=str(e))
            )
    
    def _refresh_recent_projects(self) -> None:
        """最近のプロジェクトリストを更新"""
        self.recent_list.clear()
        
        try:
            recent_projects = self.repository.list_recent(limit=10)
            
            for path, metadata in recent_projects:
                item = QListWidgetItem(f"{metadata.name} - {path.name}")
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setToolTip(str(path))
                self.recent_list.addItem(item)
                
        except Exception as e:
            logger.error(f"最近のプロジェクトリスト取得エラー: {e}")
    
    def _on_recent_item_clicked(self, item: QListWidgetItem) -> None:
        """最近のプロジェクトアイテムがクリックされた"""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            # 保存確認
            if not self._confirm_discard_changes():
                return
            
            self._open_project_file(path)
    
    def _update_auto_save_status(self) -> None:
        """自動保存状態を更新"""
        if not self.auto_saver.is_running():
            self.auto_save_status_label.setText(tr("project.autosave.disabled"))
            self.auto_save_timer_label.setText("")
            self.auto_save_progress.setValue(0)
            return
        
        # 状態更新
        self.auto_save_status_label.setText(tr("project.autosave.enabled"))
        
        # 次回保存までの時間
        time_remaining = self.auto_saver.get_time_until_next_save()
        if time_remaining >= 0:
            minutes = int(time_remaining // 60)
            seconds = int(time_remaining % 60)
            self.auto_save_timer_label.setText(
                tr("project.autosave.next_save").format(
                    minutes=minutes, seconds=seconds
                )
            )
            
            # プログレスバー更新
            if hasattr(self.auto_saver, '_interval_seconds'):
                progress = 100 - int((time_remaining / self.auto_saver._interval_seconds) * 100)
                self.auto_save_progress.setValue(progress)
    
    def _confirm_discard_changes(self) -> bool:
        """変更を破棄する確認"""
        if not self.current_project:
            return True
        
        # 保存されていない変更があるかチェック
        # TODO: 変更検出ロジックの実装
        
        # 確認ダイアログ
        reply = QMessageBox.question(
            self,
            tr("project.confirm.discard_title"),
            tr("project.confirm.discard_message"),
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )
        
        if reply == QMessageBox.StandardButton.Save:
            if self.current_project_path:
                self._on_save_project()
            else:
                self._on_save_as_project()
            return True
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else:
            return False
    
    def closeEvent(self, event) -> None:
        """ウィンドウクローズ時の処理"""
        # 自動保存停止
        if self.auto_saver.is_running():
            self.auto_saver.stop()
        
        super().closeEvent(event)