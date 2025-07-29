#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フレームDTO定義

ビデオフレームの転送用データクラス。
RGB24形式に統一して外部ライブラリ依存を排除。
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass(frozen=True)
class FrameDTO:
    """
    フレームデータ転送オブジェクト
    
    すべてのフレームデータはRGB24形式に統一される。
    外部ライブラリ（PyAV、OpenCV等）の型は含まない。
    """
    
    # フレーム識別情報
    index: int  # フレームインデックス（0始まり）
    pts: int  # Presentation Timestamp
    dts: Optional[int]  # Decode Timestamp
    
    # 画像データ（RGB24形式、shape: (height, width, 3)）
    data: np.ndarray
    
    # メタデータ
    width: int
    height: int
    timecode: Optional[str] = None
    
    def __post_init__(self):
        """検証とデータ整合性チェック"""
        # インデックスの検証
        if self.index < 0:
            raise ValueError(f"Frame index must be non-negative, got {self.index}")
        
        # PTSの検証
        if self.pts < 0:
            raise ValueError(f"PTS must be non-negative, got {self.pts}")
        
        # DTSの検証
        if self.dts is not None and self.dts < 0:
            raise ValueError(f"DTS must be non-negative, got {self.dts}")
        
        # データ形状の検証
        if self.data.ndim != 3:
            raise ValueError(f"Frame data must be 3D array, got {self.data.ndim}D")
        
        if self.data.shape[2] != 3:
            raise ValueError(f"Frame data must have 3 channels (RGB), got {self.data.shape[2]}")
        
        # データ型の検証（uint8）
        if self.data.dtype != np.uint8:
            raise ValueError(f"Frame data must be uint8, got {self.data.dtype}")
        
        # サイズの整合性チェック
        if self.data.shape[0] != self.height:
            raise ValueError(f"Height mismatch: data shape {self.data.shape[0]} != {self.height}")
        
        if self.data.shape[1] != self.width:
            raise ValueError(f"Width mismatch: data shape {self.data.shape[1]} != {self.width}")
    
    def to_dict(self) -> dict:
        """辞書形式に変換（シリアライズ用）"""
        return {
            "index": self.index,
            "pts": self.pts,
            "dts": self.dts,
            "data": self.data,
            "width": self.width,
            "height": self.height,
            "timecode": self.timecode,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FrameDTO":
        """辞書から生成"""
        return cls(
            index=data["index"],
            pts=data["pts"],
            dts=data.get("dts"),
            data=data["data"],
            width=data["width"],
            height=data["height"],
            timecode=data.get("timecode"),
        )