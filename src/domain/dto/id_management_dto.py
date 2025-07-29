#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ID管理DTO定義

ID管理機能に関するデータ転送オブジェクト。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


@dataclass(frozen=True)
class IDStatisticsDTO:
    """ID統計情報DTO
    
    各IDの統計情報を保持。
    """
    id: int
    pixel_count: int  # ピクセル数
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center: Tuple[float, float]  # 重心座標 (x, y)
    area_ratio: float  # 画像全体に対する面積比率（0.0-1.0）
    confidence: Optional[float] = None  # 信頼度（ある場合）
    class_name: Optional[str] = None  # クラス名（ある場合）
    
    def __post_init__(self):
        """検証"""
        if self.pixel_count < 0:
            raise ValueError(f"Pixel count must be non-negative, got {self.pixel_count}")
        
        if not 0.0 <= self.area_ratio <= 1.0:
            raise ValueError(f"Area ratio must be in [0, 1], got {self.area_ratio}")
        
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass(frozen=True)
class IDOperationDTO:
    """ID操作DTO
    
    ID削除・マージ等の操作を表現。
    """
    operation_type: str  # "delete", "merge", "renumber"
    target_ids: List[int]  # 対象ID
    parameters: Dict[str, any] = field(default_factory=dict)  # 操作固有のパラメータ
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """検証"""
        valid_operations = {"delete", "merge", "renumber", "delete_range", "delete_all"}
        if self.operation_type not in valid_operations:
            raise ValueError(f"Invalid operation type: {self.operation_type}")
        
        # 操作ごとのパラメータ検証
        if self.operation_type == "merge" and "target_id" not in self.parameters:
            raise ValueError("Merge operation requires 'target_id' parameter")
        
        if self.operation_type == "delete_range":
            if "start" not in self.parameters or "end" not in self.parameters:
                raise ValueError("Delete range operation requires 'start' and 'end' parameters")


@dataclass(frozen=True)
class ThresholdSettingsDTO:
    """閾値設定DTO
    
    検出閾値とマージ閾値の設定を保持。
    """
    detection_threshold: float = 0.5  # 検出閾値（0.0-1.0）
    merge_threshold: float = 0.8  # マージ閾値（0.0-1.0）
    
    # 詳細設定
    min_pixel_count: int = 100  # 最小ピクセル数（これ以下は削除）
    max_merge_distance: float = 50.0  # 最大マージ距離（ピクセル）
    merge_overlap_ratio: float = 0.7  # マージ時の重なり比率
    
    def __post_init__(self):
        """検証"""
        if not 0.0 <= self.detection_threshold <= 1.0:
            raise ValueError(f"Detection threshold must be in [0, 1], got {self.detection_threshold}")
        
        if not 0.0 <= self.merge_threshold <= 1.0:
            raise ValueError(f"Merge threshold must be in [0, 1], got {self.merge_threshold}")
        
        if self.min_pixel_count < 0:
            raise ValueError(f"Min pixel count must be non-negative, got {self.min_pixel_count}")
        
        if self.max_merge_distance < 0:
            raise ValueError(f"Max merge distance must be non-negative, got {self.max_merge_distance}")
        
        if not 0.0 <= self.merge_overlap_ratio <= 1.0:
            raise ValueError(f"Merge overlap ratio must be in [0, 1], got {self.merge_overlap_ratio}")


@dataclass(frozen=True)
class MergeCandidateDTO:
    """マージ候補DTO
    
    IDマージの候補ペアを表現。
    """
    id1: int
    id2: int
    similarity_score: float  # 類似度スコア（0.0-1.0）
    
    # 詳細情報
    distance: float  # 重心間距離
    overlap_ratio: float  # 重なり比率
    size_ratio: float  # サイズ比率（小さい方/大きい方）
    confidence_diff: Optional[float] = None  # 信頼度の差
    
    # マージ推奨理由
    reason: str = ""  # "close_proximity", "high_overlap", "similar_confidence"等
    
    def __post_init__(self):
        """検証"""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(f"Similarity score must be in [0, 1], got {self.similarity_score}")
        
        if not 0.0 <= self.overlap_ratio <= 1.0:
            raise ValueError(f"Overlap ratio must be in [0, 1], got {self.overlap_ratio}")
        
        if not 0.0 <= self.size_ratio <= 1.0:
            raise ValueError(f"Size ratio must be in [0, 1], got {self.size_ratio}")
        
        if self.distance < 0:
            raise ValueError(f"Distance must be non-negative, got {self.distance}")


@dataclass(frozen=True)
class ThresholdHistoryDTO:
    """閾値変更履歴DTO
    
    閾値の変更履歴を記録。
    """
    timestamp: datetime
    threshold_type: str  # "detection" or "merge"
    old_value: float
    new_value: float
    affected_ids: List[int] = field(default_factory=list)  # 影響を受けたID
    affected_pixel_count: int = 0  # 影響を受けたピクセル数
    
    def __post_init__(self):
        """検証"""
        valid_types = {"detection", "merge"}
        if self.threshold_type not in valid_types:
            raise ValueError(f"Invalid threshold type: {self.threshold_type}")
        
        if not 0.0 <= self.old_value <= 1.0:
            raise ValueError(f"Old value must be in [0, 1], got {self.old_value}")
        
        if not 0.0 <= self.new_value <= 1.0:
            raise ValueError(f"New value must be in [0, 1], got {self.new_value}")