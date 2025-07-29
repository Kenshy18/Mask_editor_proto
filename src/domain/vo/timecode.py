#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タイムコードValue Object

SMPTEタイムコードを表現する不変オブジェクト。
"""
from dataclasses import dataclass
import re
from typing import Tuple, Optional


@dataclass(frozen=True)
class Timecode:
    """
    タイムコード値オブジェクト
    
    SMPTE準拠のタイムコード（HH:MM:SS:FF）を表現。
    ドロップフレーム（DF）とノンドロップフレーム（NDF）の両方をサポート。
    """
    
    hours: int
    minutes: int
    seconds: int
    frames: int
    fps: float
    drop_frame: bool = False
    
    def __post_init__(self):
        """検証"""
        # 時間の検証
        if not 0 <= self.hours <= 23:
            raise ValueError(f"Hours must be 0-23, got {self.hours}")
        
        if not 0 <= self.minutes <= 59:
            raise ValueError(f"Minutes must be 0-59, got {self.minutes}")
        
        if not 0 <= self.seconds <= 59:
            raise ValueError(f"Seconds must be 0-59, got {self.seconds}")
        
        # フレーム数の検証
        max_frames = int(self.fps) - 1
        if not 0 <= self.frames <= max_frames:
            raise ValueError(f"Frames must be 0-{max_frames} for {self.fps}fps, got {self.frames}")
        
        # ドロップフレームの検証
        if self.drop_frame:
            # ドロップフレームは29.97fpsと59.94fpsでのみ有効
            if self.fps not in [29.97, 59.94]:
                raise ValueError(f"Drop frame is only valid for 29.97/59.94 fps, got {self.fps}")
            
            # ドロップフレームのルール：毎分の最初の2フレームをスキップ（10分毎を除く）
            if self.minutes % 10 != 0 and self.seconds == 0 and self.frames < 2:
                raise ValueError(f"Invalid drop frame timecode: {self}")
    
    @classmethod
    def from_string(cls, tc_string: str, fps: float, drop_frame: Optional[bool] = None) -> "Timecode":
        """
        文字列からタイムコードを生成
        
        Args:
            tc_string: タイムコード文字列（例: "01:23:45:12" or "01:23:45;12"）
            fps: フレームレート
            drop_frame: ドロップフレームフラグ（Noneの場合は文字列から判定）
        """
        # セミコロンがある場合はドロップフレーム
        if drop_frame is None:
            drop_frame = ";" in tc_string
        
        # パターンマッチング
        pattern = r"^(\d{2}):(\d{2}):(\d{2})[:;](\d{2})$"
        match = re.match(pattern, tc_string)
        
        if not match:
            raise ValueError(f"Invalid timecode format: {tc_string}")
        
        hours, minutes, seconds, frames = map(int, match.groups())
        
        return cls(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            frames=frames,
            fps=fps,
            drop_frame=drop_frame
        )
    
    def to_string(self) -> str:
        """タイムコード文字列に変換"""
        separator = ";" if self.drop_frame else ":"
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}{separator}{self.frames:02d}"
    
    def to_frames(self) -> int:
        """総フレーム数に変換"""
        if not self.drop_frame:
            # ノンドロップフレーム
            total = self.hours * 3600 * self.fps
            total += self.minutes * 60 * self.fps
            total += self.seconds * self.fps
            total += self.frames
            return int(total)
        else:
            # ドロップフレーム（29.97fpsの場合）
            # 1分あたり2フレームドロップ（10分毎を除く）
            total_minutes = self.hours * 60 + self.minutes
            dropped_frames = (total_minutes - total_minutes // 10) * 2
            
            total = self.hours * 3600 * self.fps
            total += self.minutes * 60 * self.fps
            total += self.seconds * self.fps
            total += self.frames
            total -= dropped_frames
            
            return int(total)
    
    @classmethod
    def from_frames(cls, total_frames: int, fps: float, drop_frame: bool = False) -> "Timecode":
        """フレーム数からタイムコードを生成"""
        if drop_frame and fps == 29.97:
            # ドロップフレームの逆計算
            frames_per_minute = int(60 * fps) - 2  # 1798 frames
            frames_per_10_minutes = frames_per_minute * 10 + 2  # 17982 frames
            
            # 10分単位の計算
            d = total_frames // frames_per_10_minutes
            m = total_frames % frames_per_10_minutes
            
            if m > 2:
                m = m - 2
            
            # 分とフレームの計算
            minutes = d * 10 + m // frames_per_minute
            frames = m % frames_per_minute
            
            if frames < 2 and minutes % 10:
                frames = frames + 2
            
            hours = minutes // 60
            minutes = minutes % 60
            seconds = frames // int(fps)
            frames = frames % int(fps)
        else:
            # ノンドロップフレーム
            fps_int = int(fps)
            hours = total_frames // (3600 * fps_int)
            remainder = total_frames % (3600 * fps_int)
            minutes = remainder // (60 * fps_int)
            remainder = remainder % (60 * fps_int)
            seconds = remainder // fps_int
            frames = remainder % fps_int
        
        return cls(
            hours=int(hours),
            minutes=int(minutes),
            seconds=int(seconds),
            frames=int(frames),
            fps=fps,
            drop_frame=drop_frame
        )
    
    def add_frames(self, frames: int) -> "Timecode":
        """フレーム数を加算した新しいタイムコードを生成"""
        total = self.to_frames() + frames
        return self.from_frames(total, self.fps, self.drop_frame)
    
    def __str__(self) -> str:
        """文字列表現"""
        return self.to_string()
    
    def __repr__(self) -> str:
        """詳細表現"""
        df_str = "DF" if self.drop_frame else "NDF"
        return f"Timecode('{self.to_string()}', {self.fps}fps, {df_str})"