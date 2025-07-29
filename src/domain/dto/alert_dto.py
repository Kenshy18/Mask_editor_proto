#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アラートDTO定義

アラート情報の転送用データクラス。
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AlertLevel(Enum):
    """アラートレベル（FR-19準拠）"""
    PERFECT = "perfect"  # ほぼ完璧
    NORMAL = "normal"  # 通常再生で確認
    DETAILED = "detailed"  # 詳細確認推奨
    CRITICAL = "critical"  # 修正必要


class AlertType(Enum):
    """アラートタイプ"""
    AI_OUTPUT = "ai_output"  # AI出力品質
    HAZARD_DETECTION = "hazard_detection"  # 危険物検出
    TRACKING_ERROR = "tracking_error"  # トラッキングエラー
    MASK_QUALITY = "mask_quality"  # マスク品質
    CUSTOM = "custom"  # カスタムアラート


@dataclass(frozen=True)
class AlertDTO:
    """
    アラート転送オブジェクト
    
    マスク編集の品質問題や危険物検出などのアラート情報。
    """
    
    # 識別情報
    alert_id: str  # 一意のアラートID
    alert_type: AlertType  # アラートタイプ
    alert_level: AlertLevel  # アラートレベル
    
    # 位置情報
    frame_start: int  # 開始フレーム
    frame_end: int  # 終了フレーム
    object_ids: Optional[List[int]] = None  # 関連オブジェクトID
    
    # アラート詳細
    title: str = ""  # アラートタイトル
    description: str = ""  # 詳細説明
    reason: Optional[str] = None  # アラートの理由
    
    # メタデータ
    created_at: Optional[datetime] = None  # 作成日時
    confidence: Optional[float] = None  # アラートの信頼度
    metadata: Optional[Dict[str, Any]] = None  # 追加メタデータ
    
    def __post_init__(self):
        """検証とデータ整合性チェック"""
        # フレーム範囲の検証
        if self.frame_start < 0:
            raise ValueError(f"Frame start must be non-negative, got {self.frame_start}")
        
        if self.frame_end < self.frame_start:
            raise ValueError(f"Frame end must be >= frame start, got {self.frame_end} < {self.frame_start}")
        
        # 信頼度の検証
        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
    
    def to_dict(self) -> dict:
        """辞書形式に変換（シリアライズ用）"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "alert_level": self.alert_level.value,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "object_ids": self.object_ids,
            "title": self.title,
            "description": self.description,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AlertDTO":
        """辞書から生成"""
        return cls(
            alert_id=data["alert_id"],
            alert_type=AlertType(data["alert_type"]),
            alert_level=AlertLevel(data["alert_level"]),
            frame_start=data["frame_start"],
            frame_end=data["frame_end"],
            object_ids=data.get("object_ids"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            reason=data.get("reason"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            confidence=data.get("confidence"),
            metadata=data.get("metadata"),
        )
    
    @property
    def frame_count(self) -> int:
        """影響フレーム数"""
        return self.frame_end - self.frame_start + 1
    
    @property
    def severity_score(self) -> float:
        """深刻度スコア（0-1）"""
        level_scores = {
            AlertLevel.PERFECT: 0.0,
            AlertLevel.NORMAL: 0.33,
            AlertLevel.DETAILED: 0.67,
            AlertLevel.CRITICAL: 1.0,
        }
        return level_scores[self.alert_level]
    
    def is_in_frame_range(self, frame_index: int) -> bool:
        """指定フレームがアラート範囲内か判定"""
        return self.frame_start <= frame_index <= self.frame_end
    
    def overlaps_with(self, other: "AlertDTO") -> bool:
        """他のアラートと時間的に重複するか判定"""
        return not (self.frame_end < other.frame_start or self.frame_start > other.frame_end)