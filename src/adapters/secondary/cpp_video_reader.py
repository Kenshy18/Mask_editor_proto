#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Video Reader Adapter

C++実装のビデオリーダーをPythonのIVideoReaderインターフェースに適合させる。
"""
from typing import Optional, Iterator, Union, Dict, Any
from pathlib import Path
import numpy as np

from domain.ports.secondary import IVideoReader, IVideoMetadata, IFrame
from domain.dto import FrameDTO, VideoMetadataDTO

# C++モジュールをインポート（ビルド済みの場合）
try:
    from .cpp_bindings import mask_editor_cpp
except ImportError:
    # C++モジュールが利用できない場合のフォールバック
    mask_editor_cpp = None


class CppVideoMetadata:
    """C++ビデオメタデータのラッパー"""
    
    def __init__(self, cpp_metadata):
        self._metadata = cpp_metadata
        
    @property
    def width(self) -> int:
        return self._metadata.width
    
    @property
    def height(self) -> int:
        return self._metadata.height
    
    @property
    def fps(self) -> float:
        return self._metadata.fps
    
    @property
    def frame_count(self) -> int:
        return self._metadata.frame_count
    
    @property
    def duration(self) -> float:
        return self._metadata.duration
    
    @property
    def codec(self) -> str:
        return self._metadata.codec
    
    @property
    def bit_rate(self) -> Optional[int]:
        return self._metadata.bit_rate if self._metadata.bit_rate else None
    
    @property
    def color_space(self) -> Optional[str]:
        return self._metadata.color_space if self._metadata.color_space else None
    
    @property
    def bit_depth(self) -> Optional[int]:
        return self._metadata.bit_depth if self._metadata.bit_depth else None
    
    @property
    def has_audio(self) -> bool:
        return self._metadata.has_audio
    
    @property
    def timecode(self) -> Optional[str]:
        return self._metadata.timecode if self._metadata.timecode else None


class CppFrame:
    """C++フレームのラッパー"""
    
    def __init__(self, cpp_frame):
        self._frame = cpp_frame
        
    @property
    def index(self) -> int:
        return self._frame.index
    
    @property
    def pts(self) -> int:
        return self._frame.pts
    
    @property
    def dts(self) -> Optional[int]:
        return self._frame.dts if self._frame.dts else None
    
    def to_dict(self) -> Dict[str, Any]:
        """FrameDTOの辞書形式に変換"""
        return {
            "index": self._frame.index,
            "pts": self._frame.pts,
            "dts": self.dts,
            "data": self._frame.data,  # C++側でnumpy配列に変換済み
            "width": self._frame.width,
            "height": self._frame.height,
            "timecode": None,  # TODO: フレーム単位のタイムコード計算
        }


class CppVideoReaderAdapter:
    """
    C++実装のビデオリーダーアダプター
    
    高速なC++実装をPythonのIVideoReaderインターフェースに適合させる。
    C++モジュールが利用できない場合は初期化時にエラーを発生させる。
    """
    
    def __init__(self):
        if mask_editor_cpp is None:
            raise ImportError(
                "C++ video reader module not available. "
                "Please build the C++ extension first."
            )
        self._reader = mask_editor_cpp.CppVideoReader()
        self._metadata: Optional[CppVideoMetadata] = None
        self._frame_index: int = 0
        
    def open(self, path: Union[str, Path]) -> IVideoMetadata:
        """動画ファイルを開く"""
        try:
            cpp_metadata = self._reader.open(str(path))
            self._metadata = CppVideoMetadata(cpp_metadata)
            self._frame_index = 0
            return self._metadata
        except RuntimeError as e:
            raise IOError(f"Failed to open video file: {path}") from e
    
    def read_frame(self, index: int) -> Optional[IFrame]:
        """指定インデックスのフレームを読み込む"""
        if not self._reader.is_open():
            raise RuntimeError("Video not opened")
        
        # シークが必要か判定
        if index != self._frame_index:
            self.seek(index / self._metadata.fps)
        
        # フレームを読み込む
        cpp_frame = self._reader.read_frame(index)
        if cpp_frame:
            self._frame_index = index + 1
            return CppFrame(cpp_frame)
        
        return None
    
    def read_frames(self, start: int = 0, end: Optional[int] = None) -> Iterator[IFrame]:
        """フレームをイテレートして読み込む"""
        if not self._reader.is_open():
            raise RuntimeError("Video not opened")
        
        # 開始位置にシーク
        if start > 0:
            self.seek(start / self._metadata.fps)
        
        current_index = start
        while True:
            if end is not None and current_index >= end:
                break
            
            frame = self.read_frame(current_index)
            if frame is None:
                break
            
            yield frame
            current_index += 1
    
    def seek(self, timestamp: float) -> bool:
        """指定時間にシーク"""
        if not self._reader.is_open():
            return False
        
        success = self._reader.seek(timestamp)
        if success and self._metadata:
            self._frame_index = int(timestamp * self._metadata.fps)
        return success
    
    def close(self) -> None:
        """リソースを解放"""
        self._reader.close()
        self._metadata = None
    
    def __enter__(self) -> 'CppVideoReaderAdapter':
        """コンテキストマネージャー開始"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャー終了"""
        self.close()
    
    def to_dto(self) -> VideoMetadataDTO:
        """現在のメタデータをDTOに変換"""
        if not self._metadata:
            raise RuntimeError("Video not opened")
        
        return VideoMetadataDTO(
            width=self._metadata.width,
            height=self._metadata.height,
            fps=self._metadata.fps,
            frame_count=self._metadata.frame_count,
            duration=self._metadata.duration,
            video_codec=self._metadata.codec,
            audio_codec=None,  # TODO: C++側でオーディオ情報を取得
            video_bit_rate=self._metadata.bit_rate,
            audio_bit_rate=None,
            color_space=self._metadata.color_space,
            bit_depth=self._metadata.bit_depth,
            subsampling=None,  # TODO: C++側でサブサンプリング情報を取得
            hdr_metadata=None,  # TODO: HDRメタデータの取得
            start_timecode=self._metadata.timecode,
            has_audio=self._metadata.has_audio,
            audio_channels=None,
            audio_sample_rate=None,
            container_format=None,  # TODO: C++側でコンテナ形式を取得
        )