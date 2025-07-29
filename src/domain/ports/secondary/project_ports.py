#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プロジェクト管理ポート定義

プロジェクトの保存、読み込み、管理に関するインターフェース。
"""
from typing import Protocol, Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

from domain.dto.project_dto import ProjectDTO


class IProjectMetadata(Protocol):
    """プロジェクトメタデータインターフェース"""
    
    @property
    def name(self) -> str:
        """プロジェクト名"""
        ...
    
    @property
    def version(self) -> str:
        """プロジェクトバージョン"""
        ...
    
    @property
    def created_at(self) -> datetime:
        """作成日時"""
        ...
    
    @property
    def modified_at(self) -> datetime:
        """最終更新日時"""
        ...
    
    @property
    def app_version(self) -> str:
        """アプリケーションバージョン"""
        ...


class IProjectRepository(Protocol):
    """プロジェクトリポジトリインターフェース"""
    
    def save(self, project: ProjectDTO, path: Path) -> None:
        """
        プロジェクトを保存
        
        Args:
            project: プロジェクトDTO
            path: 保存先パス（.mosaicproj）
            
        Raises:
            IOError: 保存エラー
        """
        ...
    
    def load(self, path: Path) -> ProjectDTO:
        """
        プロジェクトを読み込む
        
        Args:
            path: プロジェクトファイルパス
            
        Returns:
            プロジェクトDTO
            
        Raises:
            IOError: 読み込みエラー
            ValueError: 形式エラー
        """
        ...
    
    def exists(self, path: Path) -> bool:
        """
        プロジェクトファイルの存在確認
        
        Args:
            path: プロジェクトファイルパス
            
        Returns:
            存在する場合True
        """
        ...
    
    def get_metadata(self, path: Path) -> IProjectMetadata:
        """
        プロジェクトメタデータを取得（ファイルを完全に読み込まない）
        
        Args:
            path: プロジェクトファイルパス
            
        Returns:
            プロジェクトメタデータ
        """
        ...
    
    def list_recent(self, limit: int = 10) -> List[Tuple[Path, IProjectMetadata]]:
        """
        最近のプロジェクト一覧を取得
        
        Args:
            limit: 取得数上限
            
        Returns:
            (パス, メタデータ)のタプルリスト
        """
        ...
    
    def create_backup(self, path: Path) -> Path:
        """
        プロジェクトのバックアップを作成
        
        Args:
            path: プロジェクトファイルパス
            
        Returns:
            バックアップファイルパス
        """
        ...


class IProjectSerializer(Protocol):
    """プロジェクトシリアライザインターフェース"""
    
    def serialize(self, project: ProjectDTO) -> bytes:
        """
        プロジェクトデータをバイト列にシリアライズ
        
        Args:
            project: プロジェクトDTO
            
        Returns:
            シリアライズされたデータ
        """
        ...
    
    def deserialize(self, data: bytes) -> ProjectDTO:
        """
        バイト列からプロジェクトデータをデシリアライズ
        
        Args:
            data: シリアライズされたデータ
            
        Returns:
            プロジェクトDTO
            
        Raises:
            ValueError: デシリアライズエラー
        """
        ...
    
    def compress(self, data: bytes) -> bytes:
        """
        データを圧縮
        
        Args:
            data: 元データ
            
        Returns:
            圧縮データ
        """
        ...
    
    def decompress(self, data: bytes) -> bytes:
        """
        データを展開
        
        Args:
            data: 圧縮データ
            
        Returns:
            展開データ
        """
        ...
    
    def validate(self, project: ProjectDTO) -> bool:
        """
        プロジェクトデータの妥当性検証
        
        Args:
            project: プロジェクトDTO
            
        Returns:
            妥当な場合True
        """
        ...


class IProjectAutoSaver(Protocol):
    """プロジェクト自動保存インターフェース
    
    定期的な自動保存を管理。
    """
    
    def start(self, project: ProjectDTO, interval_seconds: int = 60) -> None:
        """
        自動保存を開始
        
        Args:
            project: 保存対象のプロジェクト
            interval_seconds: 保存間隔（秒）
        """
        ...
    
    def stop(self) -> None:
        """自動保存を停止"""
        ...
    
    def is_running(self) -> bool:
        """
        自動保存が実行中か確認
        
        Returns:
            実行中の場合True
        """
        ...
    
    def save_now(self) -> None:
        """即座に保存を実行"""
        ...
    
    def get_autosave_path(self) -> Optional[Path]:
        """
        自動保存ファイルのパスを取得
        
        Returns:
            自動保存ファイルのパス（設定されていない場合None）
        """
        ...
    
    def set_autosave_path(self, path: Path) -> None:
        """
        自動保存ファイルのパスを設定
        
        Args:
            path: 自動保存先パス
        """
        ...