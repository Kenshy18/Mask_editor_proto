#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フレームレートValue Object

ビデオのフレームレートを表現する不変オブジェクト。
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple, Optional
from enum import Enum


class FrameRateType(Enum):
    """標準フレームレートタイプ"""
    FILM = (24, 1)  # 24fps (Cinema)
    PAL = (25, 1)  # 25fps (PAL TV)
    NTSC = (30000, 1001)  # 29.97fps (NTSC TV)
    NTSC_FILM = (24000, 1001)  # 23.976fps (NTSC Film)
    WEB_30 = (30, 1)  # 30fps (Web)
    HIGH_50 = (50, 1)  # 50fps (PAL High)
    HIGH_60 = (60000, 1001)  # 59.94fps (NTSC High)
    WEB_60 = (60, 1)  # 60fps (Web High)
    HFR_120 = (120, 1)  # 120fps (High Frame Rate)


@dataclass(frozen=True)
class FrameRate:
    """
    フレームレート値オブジェクト
    
    正確なフレームレートを分数で管理。
    """
    
    numerator: int  # 分子
    denominator: int  # 分母
    
    def __post_init__(self):
        """検証と正規化"""
        if self.denominator == 0:
            raise ValueError("Denominator cannot be zero")
        
        if self.numerator <= 0:
            raise ValueError(f"Frame rate must be positive, got {self.numerator}/{self.denominator}")
        
        # 分数を約分
        fraction = Fraction(self.numerator, self.denominator)
        object.__setattr__(self, 'numerator', fraction.numerator)
        object.__setattr__(self, 'denominator', fraction.denominator)
    
    @property
    def fps(self) -> float:
        """浮動小数点のFPS値"""
        return self.numerator / self.denominator
    
    @property
    def is_fractional(self) -> bool:
        """分数フレームレートかどうか（29.97fpsなど）"""
        return self.denominator != 1
    
    @property
    def is_drop_frame_compatible(self) -> bool:
        """ドロップフレームタイムコードと互換性があるか"""
        fps = self.fps
        return abs(fps - 29.97) < 0.01 or abs(fps - 59.94) < 0.01
    
    @property
    def frame_duration_seconds(self) -> float:
        """1フレームの継続時間（秒）"""
        return self.denominator / self.numerator
    
    @property
    def frame_duration_ms(self) -> float:
        """1フレームの継続時間（ミリ秒）"""
        return self.frame_duration_seconds * 1000
    
    @property
    def standard_name(self) -> Optional[str]:
        """標準的なフレームレート名"""
        # 標準フレームレートをチェック
        for fr_type in FrameRateType:
            if (self.numerator, self.denominator) == fr_type.value:
                return fr_type.name
        
        # 一般的な値をチェック
        fps = self.fps
        if abs(fps - 23.976) < 0.001:
            return "23.976fps (NTSC Film)"
        elif abs(fps - 24) < 0.001:
            return "24fps (Film)"
        elif abs(fps - 25) < 0.001:
            return "25fps (PAL)"
        elif abs(fps - 29.97) < 0.001:
            return "29.97fps (NTSC)"
        elif abs(fps - 30) < 0.001:
            return "30fps"
        elif abs(fps - 50) < 0.001:
            return "50fps"
        elif abs(fps - 59.94) < 0.001:
            return "59.94fps"
        elif abs(fps - 60) < 0.001:
            return "60fps"
        
        return None
    
    def to_timebase(self) -> Tuple[int, int]:
        """FFmpeg/PyAVのタイムベース形式に変換"""
        return (self.denominator, self.numerator)
    
    def frame_to_seconds(self, frame_number: int) -> float:
        """
        フレーム番号を時間（秒）に変換
        
        Args:
            frame_number: フレーム番号（0始まり）
            
        Returns:
            時間（秒）
        """
        return frame_number * self.frame_duration_seconds
    
    def seconds_to_frame(self, seconds: float) -> int:
        """
        時間（秒）をフレーム番号に変換
        
        Args:
            seconds: 時間（秒）
            
        Returns:
            フレーム番号（0始まり）
        """
        return int(seconds * self.fps)
    
    def is_compatible_with(self, other: "FrameRate", tolerance: float = 0.001) -> bool:
        """
        他のフレームレートと互換性があるか判定
        
        Args:
            other: 比較対象のフレームレート
            tolerance: 許容誤差
            
        Returns:
            互換性がある場合True
        """
        return abs(self.fps - other.fps) < tolerance
    
    @classmethod
    def from_float(cls, fps: float) -> "FrameRate":
        """
        浮動小数点値からフレームレートを生成
        
        Args:
            fps: フレームレート（例: 29.97）
            
        Returns:
            FrameRate オブジェクト
        """
        # 一般的な分数フレームレートをチェック
        if abs(fps - 23.976) < 0.001:
            return cls(24000, 1001)
        elif abs(fps - 29.97) < 0.001:
            return cls(30000, 1001)
        elif abs(fps - 59.94) < 0.001:
            return cls(60000, 1001)
        elif abs(fps - 119.88) < 0.001:
            return cls(120000, 1001)
        
        # その他は分数に変換
        fraction = Fraction(fps).limit_denominator(10000)
        return cls(fraction.numerator, fraction.denominator)
    
    @classmethod
    def from_standard(cls, fr_type: FrameRateType) -> "FrameRate":
        """標準フレームレートタイプから生成"""
        return cls(*fr_type.value)
    
    # 標準フレームレートのファクトリメソッド
    @classmethod
    def film_24(cls) -> "FrameRate":
        """24fps (Cinema)"""
        return cls.from_standard(FrameRateType.FILM)
    
    @classmethod
    def ntsc_film(cls) -> "FrameRate":
        """23.976fps (NTSC Film)"""
        return cls.from_standard(FrameRateType.NTSC_FILM)
    
    @classmethod
    def pal_25(cls) -> "FrameRate":
        """25fps (PAL)"""
        return cls.from_standard(FrameRateType.PAL)
    
    @classmethod
    def ntsc_30(cls) -> "FrameRate":
        """29.97fps (NTSC)"""
        return cls.from_standard(FrameRateType.NTSC)
    
    @classmethod
    def web_30(cls) -> "FrameRate":
        """30fps (Web)"""
        return cls.from_standard(FrameRateType.WEB_30)
    
    @classmethod
    def ntsc_60(cls) -> "FrameRate":
        """59.94fps (NTSC High)"""
        return cls.from_standard(FrameRateType.HIGH_60)
    
    @classmethod
    def web_60(cls) -> "FrameRate":
        """60fps (Web High)"""
        return cls.from_standard(FrameRateType.WEB_60)
    
    def to_string(self) -> str:
        """文字列表現"""
        name = self.standard_name
        if name:
            return name
        
        if self.denominator == 1:
            return f"{self.numerator}fps"
        else:
            return f"{self.fps:.3f}fps ({self.numerator}/{self.denominator})"
    
    def __str__(self) -> str:
        """文字列表現"""
        return self.to_string()
    
    def __repr__(self) -> str:
        """詳細表現"""
        return f"FrameRate({self.numerator}/{self.denominator} = {self.fps:.3f}fps)"
    
    def __eq__(self, other) -> bool:
        """等価性比較"""
        if not isinstance(other, FrameRate):
            return False
        return self.numerator == other.numerator and self.denominator == other.denominator
    
    def __hash__(self) -> int:
        """ハッシュ値"""
        return hash((self.numerator, self.denominator))