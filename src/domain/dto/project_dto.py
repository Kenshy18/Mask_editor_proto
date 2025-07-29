#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プロジェクトDTO定義

プロジェクトデータの転送用データクラス。
入力データへの参照のみを保持し、将来の変更に対応。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from domain.dto.timeline_dto import TimelineStateDTO, TimelineMarkerDTO
from domain.dto.mask_dto import MaskOverlaySettingsDTO


@dataclass(frozen=True)
class InputDataReferenceDTO:
    """
    入力データへの参照
    
    実データはコピーせず、参照情報のみを保持。
    将来の入力形式変更に対応可能な設計。
    """
    
    # データソースタイプ（local_file, api, database等）
    source_type: str
    
    # データソース設定（パス、URL、認証情報等）
    source_config: Dict[str, Any]
    
    # データバージョン（形式変更の追跡用）
    data_version: str = "1.0"
    
    # 最終アクセス日時
    last_accessed: Optional[str] = None
    
    # データの有効性（最後の確認時）
    is_valid: bool = True
    
    # エラーメッセージ（データが無効な場合）
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "source_type": self.source_type,
            "source_config": self.source_config,
            "data_version": self.data_version,
            "last_accessed": self.last_accessed,
            "is_valid": self.is_valid,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InputDataReferenceDTO":
        """辞書から生成"""
        return cls(**data)


@dataclass(frozen=True)
class EditHistoryEntryDTO:
    """
    編集履歴エントリ
    
    各編集操作の記録。
    """
    
    # 一意のID
    id: str
    
    # タイムスタンプ
    timestamp: str
    
    # 操作種別（morphology, brush, delete等）
    operation_type: str
    
    # 対象フレーム
    frame_index: int
    
    # 対象マスクID
    mask_id: Optional[int] = None
    
    # 操作パラメータ
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 操作前後のスナップショット（オプション）
    before_snapshot: Optional[Dict[str, Any]] = None
    after_snapshot: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "operation_type": self.operation_type,
            "frame_index": self.frame_index,
            "mask_id": self.mask_id,
            "parameters": self.parameters,
            "before_snapshot": self.before_snapshot,
            "after_snapshot": self.after_snapshot,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EditHistoryEntryDTO":
        """辞書から生成"""
        return cls(**data)


@dataclass(frozen=True)
class ProjectMetadataDTO:
    """
    プロジェクトメタデータ
    
    プロジェクトの基本情報。
    """
    
    # プロジェクト名
    name: str
    
    # プロジェクトID（UUID）
    id: str
    
    # バージョン（フォーマットバージョン）
    format_version: str = "1.0"
    
    # 作成日時
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 最終更新日時
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 作成者
    author: Optional[str] = None
    
    # 説明
    description: Optional[str] = None
    
    # タグ
    tags: List[str] = field(default_factory=list)
    
    # カスタムメタデータ
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "id": self.id,
            "format_version": self.format_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "custom_metadata": self.custom_metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectMetadataDTO":
        """辞書から生成"""
        return cls(**data)


@dataclass(frozen=True)
class ProjectDTO:
    """
    プロジェクトデータ転送オブジェクト
    
    プロジェクト全体の状態を表現。
    入力データは参照のみを保持。
    """
    
    # メタデータ
    metadata: ProjectMetadataDTO
    
    # 入力データ参照
    input_data_reference: Optional[InputDataReferenceDTO] = None
    
    # ソースビデオパス（互換性のため残す）
    source_video_path: Optional[str] = None
    
    # タイムライン状態
    timeline_state: Optional[TimelineStateDTO] = None
    
    # タイムラインマーカー
    timeline_markers: List[TimelineMarkerDTO] = field(default_factory=list)
    
    # マスクオーバーレイ設定
    mask_overlay_settings: MaskOverlaySettingsDTO = field(
        default_factory=MaskOverlaySettingsDTO
    )
    
    # 編集履歴
    edit_history: List[EditHistoryEntryDTO] = field(default_factory=list)
    
    # 現在の編集インデックス（Undo/Redo用）
    current_edit_index: int = -1
    
    # エフェクト設定
    effect_settings: Dict[str, Any] = field(default_factory=dict)
    
    # エクスポート設定
    export_settings: Dict[str, Any] = field(default_factory=dict)
    
    # アプリケーション設定（ウィンドウ状態等）
    app_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """検証"""
        # フォーマットバージョンの確認
        if self.metadata.format_version not in ["1.0", "1.1"]:
            raise ValueError(f"Unsupported format version: {self.metadata.format_version}")
    
    def to_dict(self) -> dict:
        """辞書形式に変換（JSONシリアライズ用）"""
        return {
            "metadata": self.metadata.to_dict(),
            "input_data_reference": (
                self.input_data_reference.to_dict() 
                if self.input_data_reference else None
            ),
            "source_video_path": self.source_video_path,
            "timeline_state": (
                self.timeline_state.to_dict() 
                if self.timeline_state else None
            ),
            "timeline_markers": [
                marker.to_dict() for marker in self.timeline_markers
            ],
            "mask_overlay_settings": self.mask_overlay_settings.to_dict(),
            "edit_history": [
                entry.to_dict() for entry in self.edit_history
            ],
            "current_edit_index": self.current_edit_index,
            "effect_settings": self.effect_settings,
            "export_settings": self.export_settings,
            "app_settings": self.app_settings,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectDTO":
        """辞書から生成"""
        # メタデータ
        metadata = ProjectMetadataDTO.from_dict(data["metadata"])
        
        # 入力データ参照
        input_data_reference = None
        if data.get("input_data_reference"):
            input_data_reference = InputDataReferenceDTO.from_dict(
                data["input_data_reference"]
            )
        
        # タイムライン状態
        timeline_state = None
        if data.get("timeline_state"):
            timeline_state = TimelineStateDTO.from_dict(data["timeline_state"])
        
        # タイムラインマーカー
        timeline_markers = [
            TimelineMarkerDTO.from_dict(marker)
            for marker in data.get("timeline_markers", [])
        ]
        
        # マスクオーバーレイ設定
        mask_overlay_settings = MaskOverlaySettingsDTO.from_dict(
            data.get("mask_overlay_settings", {})
        )
        
        # 編集履歴
        edit_history = [
            EditHistoryEntryDTO.from_dict(entry)
            for entry in data.get("edit_history", [])
        ]
        
        return cls(
            metadata=metadata,
            input_data_reference=input_data_reference,
            source_video_path=data.get("source_video_path"),
            timeline_state=timeline_state,
            timeline_markers=timeline_markers,
            mask_overlay_settings=mask_overlay_settings,
            edit_history=edit_history,
            current_edit_index=data.get("current_edit_index", -1),
            effect_settings=data.get("effect_settings", {}),
            export_settings=data.get("export_settings", {}),
            app_settings=data.get("app_settings", {}),
        )
    
    def with_updated_metadata(self, **kwargs) -> "ProjectDTO":
        """メタデータを更新した新しいインスタンスを生成"""
        current_dict = self.metadata.to_dict()
        current_dict.update(kwargs)
        current_dict["updated_at"] = datetime.now().isoformat()
        
        new_metadata = ProjectMetadataDTO.from_dict(current_dict)
        
        return ProjectDTO(
            metadata=new_metadata,
            input_data_reference=self.input_data_reference,
            source_video_path=self.source_video_path,
            timeline_state=self.timeline_state,
            timeline_markers=self.timeline_markers,
            mask_overlay_settings=self.mask_overlay_settings,
            edit_history=self.edit_history,
            current_edit_index=self.current_edit_index,
            effect_settings=self.effect_settings,
            export_settings=self.export_settings,
            app_settings=self.app_settings,
        )