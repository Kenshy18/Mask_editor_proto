#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解像度Value Object

ビデオの解像度を表現する不変オブジェクト。
"""
from dataclasses import dataclass
from typing import Tuple, Optional
from enum import Enum


class AspectRatioType(Enum):
    """アスペクト比タイプ"""
    STANDARD_4_3 = (4, 3)
    WIDE_16_9 = (16, 9)
    ULTRAWIDE_21_9 = (21, 9)
    CINEMA_2_35_1 = (2.35, 1)
    CINEMA_2_39_1 = (2.39, 1)
    SQUARE_1_1 = (1, 1)
    VERTICAL_9_16 = (9, 16)


@dataclass(frozen=True)
class Resolution:
    """
    解像度値オブジェクト
    
    ビデオの解像度とアスペクト比を管理。
    """
    
    width: int
    height: int
    
    def __post_init__(self):
        """検証"""
        if self.width <= 0:
            raise ValueError(f"Width must be positive, got {self.width}")
        
        if self.height <= 0:
            raise ValueError(f"Height must be positive, got {self.height}")
        
        # 解像度の妥当性チェック（最大8K）
        if self.width > 7680 or self.height > 4320:
            raise ValueError(f"Resolution {self.width}x{self.height} exceeds 8K limit")
    
    @property
    def total_pixels(self) -> int:
        """総ピクセル数"""
        return self.width * self.height
    
    @property
    def megapixels(self) -> float:
        """メガピクセル数"""
        return self.total_pixels / 1_000_000
    
    @property
    def aspect_ratio(self) -> float:
        """アスペクト比（幅/高さ）"""
        return self.width / self.height
    
    @property
    def aspect_ratio_string(self) -> str:
        """アスペクト比の文字列表現"""
        # 一般的なアスペクト比をチェック
        ratio = self.aspect_ratio
        
        # 許容誤差
        tolerance = 0.02
        
        for ar_type in AspectRatioType:
            ar_value = ar_type.value[0] / ar_type.value[1] if isinstance(ar_type.value[0], int) else ar_type.value[0]
            if abs(ratio - ar_value) < tolerance:
                if isinstance(ar_type.value[0], int):
                    return f"{ar_type.value[0]}:{ar_type.value[1]}"
                else:
                    return f"{ar_type.value[0]:.2f}:1"
        
        # 最も近い整数比を計算
        gcd = self._gcd(self.width, self.height)
        return f"{self.width // gcd}:{self.height // gcd}"
    
    @property
    def is_portrait(self) -> bool:
        """縦向きかどうか"""
        return self.height > self.width
    
    @property
    def is_landscape(self) -> bool:
        """横向きかどうか"""
        return self.width > self.height
    
    @property
    def is_square(self) -> bool:
        """正方形かどうか"""
        return self.width == self.height
    
    @property
    def standard_name(self) -> Optional[str]:
        """標準的な解像度名"""
        resolutions = {
            (640, 480): "VGA",
            (720, 480): "NTSC SD",
            (720, 576): "PAL SD",
            (1280, 720): "HD 720p",
            (1920, 1080): "Full HD 1080p",
            (2560, 1440): "QHD 1440p",
            (3840, 2160): "4K UHD",
            (4096, 2160): "4K DCI",
            (5120, 2880): "5K",
            (7680, 4320): "8K UHD",
            (8192, 4320): "8K DCI",
        }
        
        return resolutions.get((self.width, self.height))
    
    def scale_to_fit(self, target_width: int, target_height: int) -> "Resolution":
        """
        アスペクト比を保ちながら指定サイズに収まるようスケール
        
        Args:
            target_width: 目標幅
            target_height: 目標高さ
            
        Returns:
            スケール後の解像度
        """
        # スケール比を計算
        scale_x = target_width / self.width
        scale_y = target_height / self.height
        scale = min(scale_x, scale_y)
        
        # 新しいサイズを計算（偶数に丸める）
        new_width = int(self.width * scale) & ~1
        new_height = int(self.height * scale) & ~1
        
        return Resolution(new_width, new_height)
    
    def scale_by_factor(self, factor: float) -> "Resolution":
        """
        指定倍率でスケール
        
        Args:
            factor: スケール倍率
            
        Returns:
            スケール後の解像度
        """
        if factor <= 0:
            raise ValueError(f"Scale factor must be positive, got {factor}")
        
        # 新しいサイズを計算（偶数に丸める）
        new_width = int(self.width * factor) & ~1
        new_height = int(self.height * factor) & ~1
        
        return Resolution(max(2, new_width), max(2, new_height))
    
    def pad_to_aspect_ratio(self, target_ratio: float) -> "Resolution":
        """
        アスペクト比に合わせてパディング
        
        Args:
            target_ratio: 目標アスペクト比
            
        Returns:
            パディング後の解像度
        """
        current_ratio = self.aspect_ratio
        
        if current_ratio < target_ratio:
            # 幅を増やす
            new_width = int(self.height * target_ratio) & ~1
            return Resolution(new_width, self.height)
        else:
            # 高さを増やす
            new_height = int(self.width / target_ratio) & ~1
            return Resolution(self.width, new_height)
    
    def _gcd(self, a: int, b: int) -> int:
        """最大公約数を計算"""
        while b:
            a, b = b, a % b
        return a
    
    def to_string(self) -> str:
        """文字列表現"""
        name = self.standard_name
        if name:
            return f"{self.width}x{self.height} ({name})"
        return f"{self.width}x{self.height}"
    
    # 標準解像度のファクトリメソッド
    @classmethod
    def vga(cls) -> "Resolution":
        """VGA (640x480)"""
        return cls(640, 480)
    
    @classmethod
    def hd_720p(cls) -> "Resolution":
        """HD 720p (1280x720)"""
        return cls(1280, 720)
    
    @classmethod
    def full_hd_1080p(cls) -> "Resolution":
        """Full HD 1080p (1920x1080)"""
        return cls(1920, 1080)
    
    @classmethod
    def uhd_4k(cls) -> "Resolution":
        """4K UHD (3840x2160)"""
        return cls(3840, 2160)
    
    @classmethod
    def dci_4k(cls) -> "Resolution":
        """4K DCI (4096x2160)"""
        return cls(4096, 2160)
    
    @classmethod
    def uhd_8k(cls) -> "Resolution":
        """8K UHD (7680x4320)"""
        return cls(7680, 4320)
    
    def __str__(self) -> str:
        """文字列表現"""
        return self.to_string()
    
    def __repr__(self) -> str:
        """詳細表現"""
        return f"Resolution({self.width}x{self.height}, {self.aspect_ratio_string}, {self.megapixels:.1f}MP)"