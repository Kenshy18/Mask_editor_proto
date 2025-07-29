#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON Project Repository Adapter

JSONファイルを使用したプロジェクトリポジトリアダプター実装。
IProjectRepositoryポートの実装を提供。
"""
import json
import shutil
from typing import List, Tuple, Optional
from pathlib import Path
from datetime import datetime
import zipfile
import logging

from domain.dto.project_dto import ProjectDTO
from domain.ports.secondary.project_ports import IProjectRepository, IProjectMetadata, IProjectSerializer

logger = logging.getLogger(__name__)


class JsonProjectMetadata:
    """JSONプロジェクトメタデータ実装"""
    
    def __init__(self, name: str, version: str, created_at: datetime, 
                 modified_at: datetime, app_version: str):
        self._name = name
        self._version = version
        self._created_at = created_at
        self._modified_at = modified_at
        self._app_version = app_version
        
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def created_at(self) -> datetime:
        return self._created_at
    
    @property
    def modified_at(self) -> datetime:
        return self._modified_at
    
    @property
    def app_version(self) -> str:
        return self._app_version


class JsonProjectSerializer:
    """JSONプロジェクトシリアライザ"""
    
    def __init__(self):
        self.compress_threshold = 1024 * 1024  # 1MB以上で圧縮
    
    def serialize(self, project: ProjectDTO) -> bytes:
        """プロジェクトをJSON形式でシリアライズ"""
        data = project.to_dict()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        return json_str.encode('utf-8')
    
    def deserialize(self, data: bytes) -> ProjectDTO:
        """JSONからプロジェクトをデシリアライズ"""
        json_str = data.decode('utf-8')
        data_dict = json.loads(json_str)
        return ProjectDTO.from_dict(data_dict)
    
    def compress(self, data: bytes) -> bytes:
        """データを圧縮（ZIP形式）"""
        import io
        import gzip
        
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
            gz.write(data)
        return buffer.getvalue()
    
    def decompress(self, data: bytes) -> bytes:
        """データを展開"""
        import io
        import gzip
        
        buffer = io.BytesIO(data)
        with gzip.GzipFile(fileobj=buffer, mode='rb') as gz:
            return gz.read()
    
    def validate(self, project: ProjectDTO) -> bool:
        """プロジェクトデータの妥当性検証"""
        try:
            # フォーマットバージョンチェック
            if project.metadata.format_version not in ["1.0", "1.1"]:
                return False
            
            # 必須フィールドの存在確認
            if not project.metadata.name or not project.metadata.id:
                return False
            
            # 日時フォーマットの検証
            datetime.fromisoformat(project.metadata.created_at)
            datetime.fromisoformat(project.metadata.updated_at)
            
            return True
        except Exception as e:
            logger.error(f"プロジェクト検証エラー: {e}")
            return False


class JsonProjectRepositoryAdapter:
    """
    JSONファイルを使用したプロジェクトリポジトリアダプター
    
    IProjectRepositoryインターフェースの実装。
    .mosaicprojファイル（JSON/ZIP）の読み書きを管理。
    """
    
    def __init__(self, serializer: Optional[IProjectSerializer] = None,
                 config_dir: Optional[Path] = None):
        """
        Args:
            serializer: プロジェクトシリアライザ
            config_dir: 設定ディレクトリ（最近のプロジェクト一覧保存用）
        """
        self.serializer = serializer or JsonProjectSerializer()
        self._config_dir = config_dir or Path.home() / ".config" / "mask_editor_god"
        self._recent_projects_file = self._config_dir / "recent_projects.json"
        self.backup_dir = self._config_dir / "backups"
        self._ensure_config_dir()
        
    def _ensure_config_dir(self) -> None:
        """設定ディレクトリを確保"""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, project: ProjectDTO, path: Path) -> None:
        """プロジェクトを保存"""
        # 検証
        if not self.serializer.validate(project):
            raise ValueError("プロジェクトデータが無効です")
        
        # シリアライズ
        data = self.serializer.serialize(project)
        
        # 圧縮判定
        if len(data) > self.serializer.compress_threshold:
            # ZIP形式で保存
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("project.json", data)
                # 追加ファイルがあれば含める（将来拡張）
        else:
            # 通常のJSONファイルとして保存
            path.write_bytes(data)
        
        # 最近のプロジェクトリストを更新
        self._update_recent_projects(path, project.metadata)
        
        logger.info(f"プロジェクトを保存しました: {path}")
    
    def load(self, path: Path) -> ProjectDTO:
        """プロジェクトを読み込む"""
        if not path.exists():
            raise FileNotFoundError(f"プロジェクトファイルが見つかりません: {path}")
        
        try:
            # ZIP形式かチェック
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, 'r') as zf:
                    data = zf.read("project.json")
            else:
                # 通常のJSONファイル
                data = path.read_bytes()
            
            # デシリアライズ
            project = self.serializer.deserialize(data)
            
            # 検証
            if not self.serializer.validate(project):
                raise ValueError("プロジェクトデータが無効です")
            
            # 最近のプロジェクトリストを更新
            self._update_recent_projects(path, project.metadata)
            
            logger.info(f"プロジェクトを読み込みました: {path}")
            return project
            
        except Exception as e:
            logger.error(f"プロジェクト読み込みエラー: {e}")
            raise
    
    def exists(self, path: Path) -> bool:
        """プロジェクトファイルの存在確認"""
        return path.exists() and path.is_file()
    
    def get_metadata(self, path: Path) -> IProjectMetadata:
        """プロジェクトメタデータを取得（軽量読み込み）"""
        if not path.exists():
            raise FileNotFoundError(f"プロジェクトファイルが見つかりません: {path}")
        
        try:
            # メタデータのみ抽出
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, 'r') as zf:
                    data = zf.read("project.json")
            else:
                data = path.read_bytes()
            
            # JSONパース（メタデータ部分のみ）
            json_data = json.loads(data.decode('utf-8'))
            metadata_dict = json_data.get("metadata", {})
            
            return JsonProjectMetadata(
                name=metadata_dict.get("name", "Unknown"),
                version=metadata_dict.get("format_version", "1.0"),
                created_at=datetime.fromisoformat(metadata_dict.get("created_at", datetime.now().isoformat())),
                modified_at=datetime.fromisoformat(metadata_dict.get("updated_at", datetime.now().isoformat())),
                app_version=metadata_dict.get("app_version", "1.0.0")
            )
            
        except Exception as e:
            logger.error(f"メタデータ読み込みエラー: {e}")
            raise
    
    def list_recent(self, limit: int = 10) -> List[Tuple[Path, IProjectMetadata]]:
        """最近のプロジェクト一覧を取得"""
        if not self._recent_projects_file.exists():
            return []
        
        try:
            recent_data = json.loads(self._recent_projects_file.read_text())
            projects = recent_data.get("projects", [])
            
            # 存在するプロジェクトのみフィルタリング
            valid_projects = []
            for proj in projects[:limit]:
                path = Path(proj["path"])
                if path.exists():
                    try:
                        metadata = self.get_metadata(path)
                        valid_projects.append((path, metadata))
                    except Exception:
                        # メタデータ読み込みに失敗したプロジェクトはスキップ
                        continue
            
            return valid_projects
            
        except Exception as e:
            logger.error(f"最近のプロジェクトリスト読み込みエラー: {e}")
            return []
    
    def create_backup(self, path: Path) -> Path:
        """プロジェクトのバックアップを作成"""
        if not path.exists():
            raise FileNotFoundError(f"プロジェクトファイルが見つかりません: {path}")
        
        # バックアップファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_backup_{timestamp}{path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        # コピー作成
        shutil.copy2(path, backup_path)
        
        logger.info(f"バックアップを作成しました: {backup_path}")
        return backup_path
    
    def _update_recent_projects(self, path: Path, metadata) -> None:
        """最近のプロジェクトリストを更新"""
        try:
            # 既存のリストを読み込み
            if self._recent_projects_file.exists():
                recent_data = json.loads(self._recent_projects_file.read_text())
            else:
                recent_data = {"projects": []}
            
            projects = recent_data["projects"]
            
            # 新しいエントリ
            new_entry = {
                "path": str(path),
                "name": metadata.name,
                "updated_at": metadata.updated_at,
                "id": metadata.id
            }
            
            # 既存のエントリを削除（同じパスまたはID）
            projects = [
                p for p in projects 
                if p["path"] != str(path) and p.get("id") != metadata.id
            ]
            
            # 先頭に追加
            projects.insert(0, new_entry)
            
            # 最大50件まで保持
            projects = projects[:50]
            
            # 保存
            recent_data["projects"] = projects
            self._recent_projects_file.write_text(
                json.dumps(recent_data, ensure_ascii=False, indent=2)
            )
            
        except Exception as e:
            logger.error(f"最近のプロジェクトリスト更新エラー: {e}")