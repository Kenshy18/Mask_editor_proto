#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バウンディングボックスDTO定義

オブジェクトの境界ボックス転送用データクラス。
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class BoundingBoxDTO:
    """
    バウンディングボックス転送オブジェクト
    
    xywh形式（左上座標と幅高さ）で統一。
    """
    
    # 位置とサイズ（xywh形式）
    x: int  # 左上X座標
    y: int  # 左上Y座標
    width: int  # 幅
    height: int  # 高さ
    
    # 識別情報
    object_id: int  # オブジェクトID
    frame_index: int  # フレームインデックス
    
    # 属性
    class_name: Optional[str] = None  # クラス名
    confidence: Optional[float] = None  # 検出信頼度
    
    def __post_init__(self):
        """検証とデータ整合性チェック"""
        # 座標の検証
        if self.x < 0:
            raise ValueError(f"X coordinate must be non-negative, got {self.x}")
        
        if self.y < 0:
            raise ValueError(f"Y coordinate must be non-negative, got {self.y}")
        
        # サイズの検証
        if self.width <= 0:
            raise ValueError(f"Width must be positive, got {self.width}")
        
        if self.height <= 0:
            raise ValueError(f"Height must be positive, got {self.height}")
        
        # IDの検証
        if self.object_id < 0:
            raise ValueError(f"Object ID must be non-negative, got {self.object_id}")
        
        if self.frame_index < 0:
            raise ValueError(f"Frame index must be non-negative, got {self.frame_index}")
        
        # 信頼度の検証
        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
    
    def to_dict(self) -> dict:
        """辞書形式に変換（シリアライズ用）"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "object_id": self.object_id,
            "frame_index": self.frame_index,
            "class_name": self.class_name,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BoundingBoxDTO":
        """辞書から生成"""
        return cls(**data)
    
    @property
    def x1(self) -> int:
        """左上X座標"""
        return self.x
    
    @property
    def y1(self) -> int:
        """左上Y座標"""
        return self.y
    
    @property
    def x2(self) -> int:
        """右下X座標"""
        return self.x + self.width
    
    @property
    def y2(self) -> int:
        """右下Y座標"""
        return self.y + self.height
    
    @property
    def center_x(self) -> float:
        """中心X座標"""
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        """中心Y座標"""
        return self.y + self.height / 2
    
    @property
    def area(self) -> int:
        """面積"""
        return self.width * self.height
    
    def to_xyxy(self) -> Tuple[int, int, int, int]:
        """xyxy形式（左上と右下の座標）に変換"""
        return (self.x1, self.y1, self.x2, self.y2)
    
    def to_cxcywh(self) -> Tuple[float, float, int, int]:
        """cxcywh形式（中心座標と幅高さ）に変換"""
        return (self.center_x, self.center_y, self.width, self.height)
    
    def contains_point(self, x: int, y: int) -> bool:
        """指定座標が境界ボックス内にあるか判定"""
        return self.x1 <= x < self.x2 and self.y1 <= y < self.y2
    
    def intersection(self, other: "BoundingBoxDTO") -> Optional["BoundingBoxDTO"]:
        """他のボックスとの交差領域を計算"""
        x1 = max(self.x1, other.x1)
        y1 = max(self.y1, other.y1)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)
        
        if x1 < x2 and y1 < y2:
            return BoundingBoxDTO(
                x=x1,
                y=y1,
                width=x2 - x1,
                height=y2 - y1,
                object_id=self.object_id,
                frame_index=self.frame_index,
                class_name=self.class_name,
                confidence=min(self.confidence, other.confidence) if self.confidence and other.confidence else None
            )
        return None
    
    def iou(self, other: "BoundingBoxDTO") -> float:
        """IoU（Intersection over Union）を計算"""
        intersection = self.intersection(other)
        if intersection is None:
            return 0.0
        
        intersection_area = intersection.area
        union_area = self.area + other.area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0