#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラシツールDTO定義

ブラシツールのデータ転送オブジェクト。
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from datetime import datetime
from enum import Enum


class BrushModeDTO(str, Enum):
    """ブラシモード"""
    ADD_NEW_ID = "add_new_id"          # 新規ID追加モード
    ADD_TO_EXISTING = "add_to_existing"  # 既存ID加筆モード
    ERASE = "erase"                    # 消去モード


class BrushShapeDTO(str, Enum):
    """ブラシ形状"""
    CIRCLE = "circle"      # 円形
    SQUARE = "square"      # 四角形
    CUSTOM = "custom"      # カスタム形状


@dataclass(frozen=True)
class BrushConfigDTO:
    """
    ブラシ設定DTO
    
    ブラシツールの設定情報を保持。
    """
    # 基本設定
    mode: BrushModeDTO = BrushModeDTO.ADD_NEW_ID
    size: int = 10                    # ブラシサイズ（ピクセル）
    hardness: float = 0.8             # ブラシ硬さ（0.0-1.0）
    opacity: float = 1.0              # 不透明度（0.0-1.0）
    shape: BrushShapeDTO = BrushShapeDTO.CIRCLE
    
    # ID管理
    target_id: Optional[int] = None   # 対象ID（既存ID加筆モード時）
    new_id: Optional[int] = None      # 新規ID（新規ID追加モード時）
    
    # 描画オプション
    spacing: float = 0.1              # ストローク間隔（サイズに対する比率）
    smoothing: float = 0.5            # スムージング強度（0.0-1.0）
    pressure_sensitivity: bool = True  # 筆圧感度
    
    def __post_init__(self):
        """検証"""
        if not 1 <= self.size <= 500:
            raise ValueError(f"Brush size must be between 1 and 500, got {self.size}")
        
        if not 0.0 <= self.hardness <= 1.0:
            raise ValueError(f"Hardness must be between 0.0 and 1.0, got {self.hardness}")
        
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError(f"Opacity must be between 0.0 and 1.0, got {self.opacity}")
        
        if not 0.0 <= self.spacing <= 2.0:
            raise ValueError(f"Spacing must be between 0.0 and 2.0, got {self.spacing}")
        
        if not 0.0 <= self.smoothing <= 1.0:
            raise ValueError(f"Smoothing must be between 0.0 and 1.0, got {self.smoothing}")
        
        # モード別検証
        if self.mode == BrushModeDTO.ADD_TO_EXISTING and self.target_id is None:
            raise ValueError("Target ID is required for ADD_TO_EXISTING mode")
        
        if self.mode == BrushModeDTO.ADD_NEW_ID and self.new_id is None:
            raise ValueError("New ID is required for ADD_NEW_ID mode")


@dataclass(frozen=True)
class BrushPointDTO:
    """
    ブラシポイントDTO
    
    ストローク中の一点を表現。
    """
    x: int
    y: int
    pressure: float = 1.0
    timestamp: float = 0.0
    
    def __post_init__(self):
        """検証"""
        if not 0.0 <= self.pressure <= 1.0:
            raise ValueError(f"Pressure must be between 0.0 and 1.0, got {self.pressure}")


@dataclass(frozen=True)
class BrushStrokeDTO:
    """
    ブラシストロークDTO
    
    一連のブラシストロークを表現。
    """
    # ストローク情報
    points: List[BrushPointDTO]
    config: BrushConfigDTO
    
    # メタデータ
    stroke_id: str = field(default_factory=lambda: datetime.now().isoformat())
    frame_index: int = 0
    
    # 境界ボックス（キャッシュ用）
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    
    def __post_init__(self):
        """検証とbbox計算"""
        if not self.points:
            raise ValueError("Stroke must have at least one point")
        
        # bboxが未設定の場合は計算
        if self.bbox is None:
            xs = [p.x for p in self.points]
            ys = [p.y for p in self.points]
            margin = self.config.size // 2 + 2
            
            min_x = min(xs) - margin
            min_y = min(ys) - margin
            max_x = max(xs) + margin
            max_y = max(ys) + margin
            
            # frozen=Trueなので、object.__setattr__を使用
            object.__setattr__(self, 'bbox', (min_x, min_y, max_x - min_x, max_y - min_y))
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """境界ボックスを(x1, y1, x2, y2)形式で取得"""
        if self.bbox:
            x, y, w, h = self.bbox
            return (x, y, x + w, y + h)
        return (0, 0, 0, 0)
    
    def get_affected_area(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """
        影響範囲を取得（画像境界でクリップ）
        
        Args:
            width: 画像幅
            height: 画像高さ
            
        Returns:
            (x1, y1, x2, y2) クリップされた境界
        """
        x1, y1, x2, y2 = self.bounds
        return (
            max(0, x1),
            max(0, y1),
            min(width, x2),
            min(height, y2)
        )


@dataclass(frozen=True)
class BrushPresetDTO:
    """
    ブラシプリセットDTO
    
    保存可能なブラシ設定。
    """
    name: str
    config: BrushConfigDTO
    icon: Optional[str] = None  # Base64エンコードされたアイコン
    category: str = "custom"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "config": {
                "mode": self.config.mode.value,
                "size": self.config.size,
                "hardness": self.config.hardness,
                "opacity": self.config.opacity,
                "shape": self.config.shape.value,
                "target_id": self.config.target_id,
                "new_id": self.config.new_id,
                "spacing": self.config.spacing,
                "smoothing": self.config.smoothing,
                "pressure_sensitivity": self.config.pressure_sensitivity,
            },
            "icon": self.icon,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BrushPresetDTO":
        """辞書から生成"""
        config_data = data["config"]
        config = BrushConfigDTO(
            mode=BrushModeDTO(config_data["mode"]),
            size=config_data["size"],
            hardness=config_data["hardness"],
            opacity=config_data["opacity"],
            shape=BrushShapeDTO(config_data["shape"]),
            target_id=config_data.get("target_id"),
            new_id=config_data.get("new_id"),
            spacing=config_data["spacing"],
            smoothing=config_data["smoothing"],
            pressure_sensitivity=config_data["pressure_sensitivity"],
        )
        
        return cls(
            name=data["name"],
            config=config,
            icon=data.get("icon"),
            category=data.get("category", "custom"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )