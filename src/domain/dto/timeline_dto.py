#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タイムラインDTO (Data Transfer Object)

タイムライン関連の情報を表現する不変オブジェクト。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import timedelta
from enum import Enum


class FrameStatus(Enum):
    """フレームの処理状態"""
    UNPROCESSED = "unprocessed"    # 未処理
    UNCONFIRMED = "unconfirmed"    # 未確認
    CONFIRMED = "confirmed"         # 確認済み
    EDITED = "edited"              # 編集済み
    ALERT = "alert"                # アラート有り


@dataclass(frozen=True)
class TimelineStateDTO:
    """
    タイムライン状態データ転送オブジェクト
    
    タイムラインの現在状態を表現。
    """
    
    # 基本情報
    total_frames: int           # 総フレーム数
    fps: float                 # フレームレート
    duration: float            # 総時間（秒）
    current_frame: int         # 現在のフレーム
    
    # 表示設定
    zoom_level: float          # ズームレベル（1.0が標準）
    visible_start: int         # 表示開始フレーム
    visible_end: int           # 表示終了フレーム
    time_unit: str             # 時間単位（"frames", "seconds", "timecode"）
    
    # スクラブ状態
    is_scrubbing: bool         # スクラブ中かどうか
    scrub_frame: Optional[int] # スクラブ中のフレーム
    
    def __post_init__(self):
        """値の妥当性検証"""
        if self.total_frames < 0:
            raise ValueError(f"total_frames must be non-negative, got {self.total_frames}")
        
        if self.fps <= 0:
            raise ValueError(f"fps must be positive, got {self.fps}")
        
        if self.duration < 0:
            raise ValueError(f"duration must be non-negative, got {self.duration}")
        
        if not 0 <= self.current_frame < self.total_frames:
            raise ValueError(f"current_frame must be in [0, {self.total_frames}), got {self.current_frame}")
        
        if not 0.1 <= self.zoom_level <= 10.0:
            raise ValueError(f"zoom_level must be in [0.1, 10.0], got {self.zoom_level}")
        
        if self.visible_start >= self.visible_end:
            raise ValueError(f"visible_start must be less than visible_end")
    
    @property
    def current_time(self) -> float:
        """現在の時間（秒）"""
        return self.current_frame / self.fps
    
    @property
    def current_timecode(self) -> str:
        """現在のタイムコード（SMPTE形式）"""
        total_seconds = self.current_time
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames = int((total_seconds % 1) * self.fps)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    
    @property
    def visible_duration(self) -> float:
        """表示範囲の時間（秒）"""
        return (self.visible_end - self.visible_start) / self.fps
    
    def to_dict(self) -> Dict[str, any]:
        """辞書形式に変換"""
        return {
            "total_frames": self.total_frames,
            "fps": self.fps,
            "duration": self.duration,
            "current_frame": self.current_frame,
            "zoom_level": self.zoom_level,
            "visible_start": self.visible_start,
            "visible_end": self.visible_end,
            "time_unit": self.time_unit,
            "is_scrubbing": self.is_scrubbing,
            "scrub_frame": self.scrub_frame
        }


@dataclass(frozen=True)
class TimelineMarkerDTO:
    """
    タイムラインマーカーデータ転送オブジェクト
    
    タイムライン上のマーカー情報を表現。
    """
    
    id: str                    # マーカーID
    frame_index: int           # フレーム番号
    label: str                 # マーカーラベル
    color: str                 # マーカー色（hex形式）
    created_at: str            # 作成日時（ISO形式）
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """値の妥当性検証"""
        if self.frame_index < 0:
            raise ValueError(f"frame_index must be non-negative, got {self.frame_index}")
        
        if not self.label:
            raise ValueError("label must not be empty")
        
        # 色形式の検証（簡易的）
        if not self.color.startswith("#") or len(self.color) not in [4, 7]:
            raise ValueError(f"color must be hex format (#RGB or #RRGGBB), got {self.color}")
    
    @property
    def time(self) -> float:
        """時間（秒）- FPSが必要なため、外部で計算"""
        # 注：実際の時間はコンテキスト（FPS）に依存するため、ここでは計算しない
        return 0.0
    
    def to_dict(self) -> Dict[str, any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "frame_index": self.frame_index,
            "label": self.label,
            "color": self.color,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


@dataclass(frozen=True)
class FrameRangeDTO:
    """
    フレーム範囲データ転送オブジェクト
    
    フレームの範囲と状態を表現。
    """
    
    start_frame: int           # 開始フレーム
    end_frame: int             # 終了フレーム（含む）
    status: FrameStatus        # 範囲の状態
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """値の妥当性検証"""
        if self.start_frame < 0:
            raise ValueError(f"start_frame must be non-negative, got {self.start_frame}")
        
        if self.end_frame < self.start_frame:
            raise ValueError(f"end_frame must be >= start_frame, got {self.end_frame}")
    
    @property
    def frame_count(self) -> int:
        """フレーム数"""
        return self.end_frame - self.start_frame + 1
    
    def contains(self, frame_index: int) -> bool:
        """指定フレームが範囲内かどうか"""
        return self.start_frame <= frame_index <= self.end_frame
    
    def overlaps(self, other: "FrameRangeDTO") -> bool:
        """他の範囲と重なるかどうか"""
        return not (self.end_frame < other.start_frame or other.end_frame < self.start_frame)
    
    def to_dict(self) -> Dict[str, any]:
        """辞書形式に変換"""
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "status": self.status.value,
            "metadata": self.metadata
        }