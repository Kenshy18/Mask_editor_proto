#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プロジェクト自動保存アダプター

定期的な自動保存機能を提供。
"""
import threading
import time
from pathlib import Path
from typing import Optional
import logging

from domain.dto.project_dto import ProjectDTO
from domain.ports.secondary.project_ports import IProjectAutoSaver, IProjectRepository

logger = logging.getLogger(__name__)


class ProjectAutoSaverAdapter:
    """プロジェクト自動保存アダプター実装"""
    
    def __init__(self, repository: IProjectRepository):
        """
        Args:
            repository: プロジェクトリポジトリ
        """
        self.repository = repository
        self._project: Optional[ProjectDTO] = None
        self._autosave_path: Optional[Path] = None
        self._interval_seconds = 60
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        self._last_save_time = 0
    
    def start(self, project: ProjectDTO, interval_seconds: int = 60) -> None:
        """
        自動保存を開始
        
        Args:
            project: 保存対象のプロジェクト
            interval_seconds: 保存間隔（秒）
        """
        if self._is_running:
            self.stop()
        
        self._project = project
        self._interval_seconds = max(30, interval_seconds)  # 最小30秒
        
        # 自動保存パスの設定
        if not self._autosave_path:
            # デフォルトパスを生成
            config_dir = Path.home() / ".config" / "mask_editor_god" / "autosave"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._autosave_path = config_dir / f"{project.metadata.id}_autosave.mosaicproj"
        
        # 自動保存スレッドを開始
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._autosave_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"自動保存を開始しました（間隔: {self._interval_seconds}秒）")
    
    def stop(self) -> None:
        """自動保存を停止"""
        if not self._is_running:
            return
        
        self._is_running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self._thread = None
        logger.info("自動保存を停止しました")
    
    def is_running(self) -> bool:
        """
        自動保存が実行中か確認
        
        Returns:
            実行中の場合True
        """
        return self._is_running
    
    def save_now(self) -> None:
        """即座に保存を実行"""
        if not self._project or not self._autosave_path:
            logger.warning("プロジェクトまたは保存パスが設定されていません")
            return
        
        try:
            # バックアップを作成
            if self._autosave_path.exists():
                backup_path = self._autosave_path.with_suffix(".bak")
                self._autosave_path.rename(backup_path)
            
            # 保存実行
            self.repository.save(self._project, self._autosave_path)
            self._last_save_time = time.time()
            
            # バックアップを削除
            if backup_path.exists():
                backup_path.unlink()
            
            logger.debug("自動保存を実行しました")
            
        except Exception as e:
            logger.error(f"自動保存エラー: {e}")
            # バックアップを復元
            if backup_path.exists():
                backup_path.rename(self._autosave_path)
    
    def get_autosave_path(self) -> Optional[Path]:
        """
        自動保存ファイルのパスを取得
        
        Returns:
            自動保存ファイルのパス（設定されていない場合None）
        """
        return self._autosave_path
    
    def set_autosave_path(self, path: Path) -> None:
        """
        自動保存ファイルのパスを設定
        
        Args:
            path: 自動保存先パス
        """
        self._autosave_path = path
        logger.info(f"自動保存パスを設定しました: {path}")
    
    def update_project(self, project: ProjectDTO) -> None:
        """
        保存対象のプロジェクトを更新
        
        Args:
            project: 新しいプロジェクトデータ
        """
        self._project = project
    
    def get_time_until_next_save(self) -> float:
        """
        次の自動保存までの時間を取得
        
        Returns:
            秒数（自動保存が無効の場合は-1）
        """
        if not self._is_running:
            return -1
        
        elapsed = time.time() - self._last_save_time
        remaining = self._interval_seconds - elapsed
        return max(0, remaining)
    
    def _autosave_loop(self) -> None:
        """自動保存ループ（別スレッドで実行）"""
        logger.debug("自動保存ループを開始")
        
        while not self._stop_event.is_set():
            try:
                # 指定間隔まで待機
                if self._stop_event.wait(self._interval_seconds):
                    break  # 停止要求があれば終了
                
                # 自動保存実行
                if self._project and self._autosave_path:
                    self.save_now()
                
            except Exception as e:
                logger.error(f"自動保存ループエラー: {e}")
                # エラーが発生しても継続
        
        logger.debug("自動保存ループを終了")
    
    def recover_from_autosave(self, autosave_path: Optional[Path] = None) -> Optional[ProjectDTO]:
        """
        自動保存ファイルからプロジェクトを復元
        
        Args:
            autosave_path: 自動保存ファイルのパス（省略時はデフォルトパス）
            
        Returns:
            復元されたプロジェクト（復元できない場合はNone）
        """
        path = autosave_path or self._autosave_path
        
        if not path or not path.exists():
            return None
        
        try:
            project = self.repository.load(path)
            logger.info(f"自動保存ファイルからプロジェクトを復元しました: {path}")
            return project
        except Exception as e:
            logger.error(f"自動保存ファイルの復元エラー: {e}")
            return None
    
    def cleanup_autosave(self) -> None:
        """自動保存ファイルをクリーンアップ"""
        if self._autosave_path and self._autosave_path.exists():
            try:
                self._autosave_path.unlink()
                logger.info("自動保存ファイルを削除しました")
                
                # バックアップファイルも削除
                backup_path = self._autosave_path.with_suffix(".bak")
                if backup_path.exists():
                    backup_path.unlink()
                    
            except Exception as e:
                logger.error(f"自動保存ファイルの削除エラー: {e}")