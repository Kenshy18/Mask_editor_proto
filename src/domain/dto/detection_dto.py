#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検出情報DTO (Data Transfer Object)

AIモデルからの検出結果を表現する不変オブジェクト。
"""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class DetectionDTO:
    """
    検出情報データ転送オブジェクト
    
    AIモデルの検出結果を表現。
    バウンディングボックスとその属性を保持。
    """
    
    # 基本情報
    frame_index: int          # フレーム番号（0-based）
    track_id: int            # トラッキングID（マスクIDと対応）
    class_id: int            # クラスID
    class_name: str          # クラス名（例："person", "genital"）
    confidence: float        # 信頼度（0.0-1.0）
    
    # バウンディングボックス（x1, y1, x2, y2形式）
    x1: float               # 左上X座標
    y1: float               # 左上Y座標
    x2: float               # 右下X座標
    y2: float               # 右下Y座標
    
    # 追加属性（将来の拡張用）
    attributes: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """値の妥当性検証"""
        # フレームインデックス
        if self.frame_index < 0:
            raise ValueError(f"frame_index must be non-negative, got {self.frame_index}")
        
        # トラッキングID
        if self.track_id < 0:
            raise ValueError(f"track_id must be non-negative, got {self.track_id}")
        
        # 信頼度
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        # バウンディングボックス
        if self.x1 >= self.x2:
            raise ValueError(f"x1 must be less than x2, got x1={self.x1}, x2={self.x2}")
        if self.y1 >= self.y2:
            raise ValueError(f"y1 must be less than y2, got y1={self.y1}, y2={self.y2}")
        
        # 座標の非負チェック
        if self.x1 < 0 or self.y1 < 0:
            raise ValueError(f"Coordinates must be non-negative, got x1={self.x1}, y1={self.y1}")
    
    @property
    def width(self) -> float:
        """バウンディングボックスの幅"""
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        """バウンディングボックスの高さ"""
        return self.y2 - self.y1
    
    @property
    def center_x(self) -> float:
        """中心X座標"""
        return (self.x1 + self.x2) / 2
    
    @property
    def center_y(self) -> float:
        """中心Y座標"""
        return (self.y1 + self.y2) / 2
    
    @property
    def area(self) -> float:
        """面積"""
        return self.width * self.height
    
    def to_xywh(self) -> tuple[float, float, float, float]:
        """(x, y, width, height)形式に変換"""
        return (self.x1, self.y1, self.width, self.height)
    
    def to_cxcywh(self) -> tuple[float, float, float, float]:
        """(center_x, center_y, width, height)形式に変換"""
        return (self.center_x, self.center_y, self.width, self.height)
    
    def to_dict(self) -> Dict[str, any]:
        """辞書形式に変換"""
        return {
            "frame_index": self.frame_index,
            "track_id": self.track_id,
            "class": {
                "id": self.class_id,
                "name": self.class_name
            },
            "confidence": self.confidence,
            "bounding_box": {
                "x1": self.x1,
                "y1": self.y1,
                "x2": self.x2,
                "y2": self.y2
            },
            "attributes": self.attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "DetectionDTO":
        """辞書から生成"""
        bbox = data["bounding_box"]
        class_info = data["class"]
        
        return cls(
            frame_index=data["frame_index"],
            track_id=data["track_id"],
            class_id=class_info["id"],
            class_name=class_info["name"],
            confidence=data["confidence"],
            x1=bbox["x1"],
            y1=bbox["y1"],
            x2=bbox["x2"],
            y2=bbox["y2"],
            attributes=data.get("attributes", {})
        )
    
    def iou(self, other: "DetectionDTO") -> float:
        """
        Intersection over Union (IoU)を計算
        
        Args:
            other: 比較対象の検出情報
            
        Returns:
            IoU値（0.0-1.0）
        """
        # 交差領域の計算
        inter_x1 = max(self.x1, other.x1)
        inter_y1 = max(self.y1, other.y1)
        inter_x2 = min(self.x2, other.x2)
        inter_y2 = min(self.y2, other.y2)
        
        # 交差していない場合
        if inter_x1 >= inter_x2 or inter_y1 >= inter_y2:
            return 0.0
        
        # 交差領域の面積
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        
        # 和集合の面積
        union_area = self.area + other.area - inter_area
        
        # IoU
        return inter_area / union_area if union_area > 0 else 0.0