#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスクDTO定義

マスクデータの転送用データクラス。
0-255のuint8形式に統一。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass(frozen=True)
class MaskDTO:
    """
    マスクデータ転送オブジェクト
    
    マスクデータは0-255のuint8形式に統一。
    各ピクセル値がオブジェクトIDを表す。
    """
    
    # フレーム情報
    frame_index: int  # 対応するフレームインデックス
    
    # マスクデータ（0-255 uint8、shape: (height, width)）
    data: np.ndarray
    
    # マスクサイズ
    width: int
    height: int
    
    # オブジェクト情報
    object_ids: List[int]  # 含まれるオブジェクトIDのリスト
    classes: Dict[int, str]  # ID -> クラス名のマッピング
    confidences: Dict[int, float]  # ID -> 信頼度のマッピング
    
    def __post_init__(self):
        """検証とデータ整合性チェック"""
        # フレームインデックスの検証
        if self.frame_index < 0:
            raise ValueError(f"Frame index must be non-negative, got {self.frame_index}")
        
        # データ形状の検証
        if self.data.ndim != 2:
            raise ValueError(f"Mask data must be 2D array, got {self.data.ndim}D")
        
        # データ型の検証
        if self.data.dtype != np.uint8:
            raise ValueError(f"Mask data must be uint8, got {self.data.dtype}")
        
        # サイズの整合性チェック
        if self.data.shape[0] != self.height:
            raise ValueError(f"Height mismatch: data shape {self.data.shape[0]} != {self.height}")
        
        if self.data.shape[1] != self.width:
            raise ValueError(f"Width mismatch: data shape {self.data.shape[1]} != {self.width}")
        
        # オブジェクトIDの検証
        unique_ids = np.unique(self.data)
        unique_ids = unique_ids[unique_ids > 0]  # 0（背景）を除外
        
        for obj_id in self.object_ids:
            if obj_id not in unique_ids:
                raise ValueError(f"Object ID {obj_id} not found in mask data")
        
        # 信頼度の検証
        for obj_id, confidence in self.confidences.items():
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"Confidence for ID {obj_id} must be in [0, 1], got {confidence}")
    
    def to_dict(self) -> dict:
        """辞書形式に変換（シリアライズ用）"""
        return {
            "frame_index": self.frame_index,
            "data": self.data,
            "width": self.width,
            "height": self.height,
            "object_ids": self.object_ids,
            "classes": self.classes,
            "confidences": self.confidences,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MaskDTO":
        """辞書から生成"""
        return cls(
            frame_index=data["frame_index"],
            data=data["data"],
            width=data["width"],
            height=data["height"],
            object_ids=data["object_ids"],
            classes=data["classes"],
            confidences=data["confidences"],
        )
    
    def get_mask_for_id(self, object_id: int) -> np.ndarray:
        """特定IDのバイナリマスクを取得"""
        if object_id not in self.object_ids:
            raise ValueError(f"Object ID {object_id} not found")
        return (self.data == object_id).astype(np.uint8) * 255
    
    def count_pixels(self, object_id: Optional[int] = None) -> int:
        """ピクセル数をカウント"""
        if object_id is None:
            return np.sum(self.data > 0)
        return np.sum(self.data == object_id)


@dataclass(frozen=True)
class MaskOverlaySettingsDTO:
    """
    マスクオーバーレイ設定
    
    マスクの表示設定を管理。
    """
    
    # 全体設定
    opacity: float = 0.7  # 不透明度（0.0-1.0）
    enabled: bool = True  # オーバーレイ表示のON/OFF
    
    # ID別設定
    mask_visibility: Dict[int, bool] = field(default_factory=dict)  # ID別の表示/非表示
    mask_colors: Dict[int, str] = field(default_factory=dict)  # ID別の色（#RRGGBB形式）
    
    # デフォルトカラー設定
    default_colors: List[str] = field(default_factory=lambda: [
        "#FF0000",  # 赤
        "#00FF00",  # 緑
        "#0000FF",  # 青
        "#FFFF00",  # 黄
        "#FF00FF",  # マゼンタ
        "#00FFFF",  # シアン
        "#FFA500",  # オレンジ
        "#800080",  # 紫
        "#FF1493",  # ディープピンク
        "#32CD32",  # ライムグリーン
    ])
    
    # 表示オプション
    show_outlines: bool = False  # 輪郭線表示
    outline_width: int = 2  # 輪郭線の太さ
    show_labels: bool = False  # ラベル表示
    
    def __post_init__(self):
        """検証"""
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError(f"Opacity must be in [0, 1], got {self.opacity}")
        
        if self.outline_width < 1:
            raise ValueError(f"Outline width must be positive, got {self.outline_width}")
        
        # 色形式の検証
        import re
        color_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        
        for mask_id, color in self.mask_colors.items():
            if not color_pattern.match(color):
                raise ValueError(f"Invalid color format for mask {mask_id}: {color}")
        
        for color in self.default_colors:
            if not color_pattern.match(color):
                raise ValueError(f"Invalid default color format: {color}")
    
    def get_mask_color(self, mask_id: int) -> str:
        """マスクの色を取得（デフォルトカラーから自動割り当て）"""
        if mask_id in self.mask_colors:
            return self.mask_colors[mask_id]
        
        # デフォルトカラーから割り当て
        color_index = mask_id % len(self.default_colors)
        return self.default_colors[color_index]
    
    def is_mask_visible(self, mask_id: int) -> bool:
        """マスクが表示されているかチェック"""
        if not self.enabled:
            return False
        return self.mask_visibility.get(mask_id, True)  # デフォルトは表示
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "opacity": self.opacity,
            "enabled": self.enabled,
            "mask_visibility": self.mask_visibility,
            "mask_colors": self.mask_colors,
            "default_colors": self.default_colors,
            "show_outlines": self.show_outlines,
            "outline_width": self.outline_width,
            "show_labels": self.show_labels,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MaskOverlaySettingsDTO":
        """辞書から生成"""
        return cls(**data)