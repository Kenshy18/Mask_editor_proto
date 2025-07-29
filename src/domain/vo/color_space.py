#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色空間Value Object

ビデオの色空間情報を表現する不変オブジェクト。
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ColorPrimaries(Enum):
    """色度座標"""
    BT709 = "bt709"  # HD
    BT2020 = "bt2020"  # UHD/HDR
    BT601 = "bt601"  # SD
    DCI_P3 = "dci_p3"  # Digital Cinema
    DISPLAY_P3 = "display_p3"  # Apple Display P3
    SRGB = "srgb"  # sRGB


class TransferCharacteristics(Enum):
    """伝達関数"""
    BT709 = "bt709"  # Standard (gamma 2.4)
    SRGB = "srgb"  # sRGB (gamma 2.2)
    PQ = "pq"  # Perceptual Quantizer (HDR10)
    HLG = "hlg"  # Hybrid Log-Gamma (BBC/NHK)
    LINEAR = "linear"  # Linear
    BT2020_10 = "bt2020_10"  # BT.2020 10-bit
    BT2020_12 = "bt2020_12"  # BT.2020 12-bit


class MatrixCoefficients(Enum):
    """変換マトリクス"""
    BT709 = "bt709"  # HD
    BT2020_NCL = "bt2020_ncl"  # BT.2020 non-constant luminance
    BT2020_CL = "bt2020_cl"  # BT.2020 constant luminance
    BT601 = "bt601"  # SD
    SMPTE240M = "smpte240m"  # SMPTE 240M


@dataclass(frozen=True)
class ColorSpace:
    """
    色空間値オブジェクト
    
    ビデオの色空間情報を完全に定義。
    """
    
    primaries: ColorPrimaries
    transfer: TransferCharacteristics
    matrix: MatrixCoefficients
    full_range: bool = False  # Limited range (16-235) vs Full range (0-255)
    bit_depth: int = 8  # 8, 10, 12, 16
    
    def __post_init__(self):
        """検証"""
        # ビット深度の検証
        if self.bit_depth not in [8, 10, 12, 16]:
            raise ValueError(f"Bit depth must be 8, 10, 12, or 16, got {self.bit_depth}")
        
        # HDR検証
        if self.is_hdr and self.bit_depth < 10:
            raise ValueError("HDR requires at least 10-bit depth")
        
        # PQ/HLGの検証
        if self.transfer in [TransferCharacteristics.PQ, TransferCharacteristics.HLG]:
            if self.primaries != ColorPrimaries.BT2020:
                raise ValueError(f"{self.transfer.value} requires BT.2020 primaries")
    
    @property
    def is_hdr(self) -> bool:
        """HDRかどうか"""
        return self.transfer in [TransferCharacteristics.PQ, TransferCharacteristics.HLG]
    
    @property
    def is_wide_gamut(self) -> bool:
        """広色域かどうか"""
        return self.primaries in [ColorPrimaries.BT2020, ColorPrimaries.DCI_P3, ColorPrimaries.DISPLAY_P3]
    
    @property
    def max_value(self) -> int:
        """最大ピクセル値"""
        return (1 << self.bit_depth) - 1
    
    @property
    def min_luma(self) -> int:
        """最小輝度値"""
        if self.full_range:
            return 0
        else:
            # Limited range
            return 16 << (self.bit_depth - 8)
    
    @property
    def max_luma(self) -> int:
        """最大輝度値"""
        if self.full_range:
            return self.max_value
        else:
            # Limited range
            return 235 << (self.bit_depth - 8)
    
    @property
    def min_chroma(self) -> int:
        """最小色差値"""
        if self.full_range:
            return 0
        else:
            # Limited range
            return 16 << (self.bit_depth - 8)
    
    @property
    def max_chroma(self) -> int:
        """最大色差値"""
        if self.full_range:
            return self.max_value
        else:
            # Limited range
            return 240 << (self.bit_depth - 8)
    
    def to_string(self) -> str:
        """文字列表現"""
        range_str = "Full" if self.full_range else "Limited"
        hdr_str = " HDR" if self.is_hdr else ""
        return f"{self.primaries.value}/{self.transfer.value}/{self.matrix.value} {self.bit_depth}-bit {range_str}{hdr_str}"
    
    @classmethod
    def srgb(cls) -> "ColorSpace":
        """sRGB色空間を生成"""
        return cls(
            primaries=ColorPrimaries.SRGB,
            transfer=TransferCharacteristics.SRGB,
            matrix=MatrixCoefficients.BT709,
            full_range=True,
            bit_depth=8
        )
    
    @classmethod
    def rec709(cls, bit_depth: int = 8, full_range: bool = False) -> "ColorSpace":
        """Rec.709（HD）色空間を生成"""
        return cls(
            primaries=ColorPrimaries.BT709,
            transfer=TransferCharacteristics.BT709,
            matrix=MatrixCoefficients.BT709,
            full_range=full_range,
            bit_depth=bit_depth
        )
    
    @classmethod
    def rec2020_sdr(cls, bit_depth: int = 10, full_range: bool = False) -> "ColorSpace":
        """Rec.2020 SDR色空間を生成"""
        transfer = TransferCharacteristics.BT2020_10 if bit_depth == 10 else TransferCharacteristics.BT2020_12
        return cls(
            primaries=ColorPrimaries.BT2020,
            transfer=transfer,
            matrix=MatrixCoefficients.BT2020_NCL,
            full_range=full_range,
            bit_depth=bit_depth
        )
    
    @classmethod
    def rec2020_pq(cls, bit_depth: int = 10, full_range: bool = False) -> "ColorSpace":
        """Rec.2020 PQ（HDR10）色空間を生成"""
        return cls(
            primaries=ColorPrimaries.BT2020,
            transfer=TransferCharacteristics.PQ,
            matrix=MatrixCoefficients.BT2020_NCL,
            full_range=full_range,
            bit_depth=bit_depth
        )
    
    @classmethod
    def rec2020_hlg(cls, bit_depth: int = 10, full_range: bool = False) -> "ColorSpace":
        """Rec.2020 HLG色空間を生成"""
        return cls(
            primaries=ColorPrimaries.BT2020,
            transfer=TransferCharacteristics.HLG,
            matrix=MatrixCoefficients.BT2020_NCL,
            full_range=full_range,
            bit_depth=bit_depth
        )
    
    def __str__(self) -> str:
        """文字列表現"""
        return self.to_string()
    
    def __repr__(self) -> str:
        """詳細表現"""
        return f"ColorSpace({self.to_string()})"