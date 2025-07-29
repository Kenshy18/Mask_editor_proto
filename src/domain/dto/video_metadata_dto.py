#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ビデオメタデータDTO定義

ビデオのメタデータ転送用データクラス。
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class VideoMetadataDTO:
    """
    ビデオメタデータ転送オブジェクト
    
    ビデオファイルのメタデータを保持。
    外部ライブラリに依存しない純粋なデータ型のみ使用。
    """
    
    # 基本情報
    width: int
    height: int
    fps: float
    frame_count: int
    duration: float  # 秒
    
    # コーデック情報
    video_codec: str
    audio_codec: Optional[str] = None
    
    # ビットレート
    video_bit_rate: Optional[int] = None  # bps
    audio_bit_rate: Optional[int] = None  # bps
    
    # 色空間情報
    color_space: Optional[str] = None  # BT.709, BT.2020等
    bit_depth: Optional[int] = None  # 8, 10, 12等
    subsampling: Optional[str] = None  # 4:2:0, 4:2:2, 4:4:4等
    
    # HDR情報
    hdr_metadata: Optional[Dict[str, Any]] = None
    
    # タイムコード
    start_timecode: Optional[str] = None
    
    # オーディオ情報
    has_audio: bool = False
    audio_channels: Optional[int] = None
    audio_sample_rate: Optional[int] = None  # Hz
    
    # その他
    container_format: Optional[str] = None  # mp4, mov, mkv等
    
    def __post_init__(self):
        """検証とデータ整合性チェック"""
        # 基本パラメータの検証
        if self.width <= 0:
            raise ValueError(f"Width must be positive, got {self.width}")
        
        if self.height <= 0:
            raise ValueError(f"Height must be positive, got {self.height}")
        
        if self.fps <= 0:
            raise ValueError(f"FPS must be positive, got {self.fps}")
        
        if self.frame_count < 0:
            raise ValueError(f"Frame count must be non-negative, got {self.frame_count}")
        
        if self.duration < 0:
            raise ValueError(f"Duration must be non-negative, got {self.duration}")
        
        # ビットレートの検証
        if self.video_bit_rate is not None and self.video_bit_rate <= 0:
            raise ValueError(f"Video bit rate must be positive, got {self.video_bit_rate}")
        
        if self.audio_bit_rate is not None and self.audio_bit_rate <= 0:
            raise ValueError(f"Audio bit rate must be positive, got {self.audio_bit_rate}")
        
        # ビット深度の検証
        if self.bit_depth is not None:
            if self.bit_depth not in [8, 10, 12, 16]:
                raise ValueError(f"Invalid bit depth: {self.bit_depth}")
        
        # オーディオ情報の整合性チェック
        if self.has_audio:
            if self.audio_channels is None or self.audio_channels <= 0:
                raise ValueError("Audio channels must be specified when has_audio is True")
            if self.audio_sample_rate is None or self.audio_sample_rate <= 0:
                raise ValueError("Audio sample rate must be specified when has_audio is True")
    
    def to_dict(self) -> dict:
        """辞書形式に変換（シリアライズ用）"""
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "duration": self.duration,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "video_bit_rate": self.video_bit_rate,
            "audio_bit_rate": self.audio_bit_rate,
            "color_space": self.color_space,
            "bit_depth": self.bit_depth,
            "subsampling": self.subsampling,
            "hdr_metadata": self.hdr_metadata,
            "start_timecode": self.start_timecode,
            "has_audio": self.has_audio,
            "audio_channels": self.audio_channels,
            "audio_sample_rate": self.audio_sample_rate,
            "container_format": self.container_format,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VideoMetadataDTO":
        """辞書から生成"""
        return cls(**data)
    
    @property
    def resolution_string(self) -> str:
        """解像度を文字列で取得（例: "1920x1080"）"""
        return f"{self.width}x{self.height}"
    
    @property
    def aspect_ratio(self) -> float:
        """アスペクト比を計算"""
        return self.width / self.height