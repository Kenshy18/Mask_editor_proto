#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyAV Video Reader Adapter

PyAVを使用したビデオ読み込みアダプター実装。
IVideoReaderポートの実装を提供。
"""
from typing import Optional, Iterator, Union, Dict, Any
from pathlib import Path
import numpy as np
import av
from fractions import Fraction

from domain.ports.secondary import IVideoReader, IVideoMetadata, IFrame
from domain.dto import FrameDTO, VideoMetadataDTO
from domain.vo import FrameRate, ColorSpace, Timecode


class PyAVVideoMetadata:
    """PyAVビデオメタデータ実装"""
    
    def __init__(self, container: av.container.Container):
        self._container = container
        self._video_stream = next(s for s in container.streams if s.type == 'video')
        
    @property
    def width(self) -> int:
        return self._video_stream.width
    
    @property
    def height(self) -> int:
        return self._video_stream.height
    
    @property
    def fps(self) -> float:
        return float(self._video_stream.average_rate)
    
    @property
    def frame_count(self) -> int:
        return self._video_stream.frames
    
    @property
    def duration(self) -> float:
        if self._video_stream.duration:
            return float(self._video_stream.duration * self._video_stream.time_base)
        return self.frame_count / self.fps if self.fps > 0 else 0
    
    @property
    def codec(self) -> str:
        return self._video_stream.codec_context.name
    
    @property
    def bit_rate(self) -> Optional[int]:
        return self._video_stream.bit_rate
    
    @property
    def color_space(self) -> Optional[str]:
        # PyAVの色空間情報を取得
        if hasattr(self._video_stream.codec_context, 'colorspace'):
            return str(self._video_stream.codec_context.colorspace)
        return None
    
    @property
    def bit_depth(self) -> Optional[int]:
        # ピクセルフォーマットからビット深度を推定
        pix_fmt = self._video_stream.codec_context.pix_fmt
        if pix_fmt:
            if '10' in pix_fmt:
                return 10
            elif '12' in pix_fmt:
                return 12
            elif '16' in pix_fmt:
                return 16
        return 8
    
    @property
    def has_audio(self) -> bool:
        return any(s.type == 'audio' for s in self._container.streams)
    
    @property
    def timecode(self) -> Optional[str]:
        # メタデータからタイムコードを取得
        if 'timecode' in self._container.metadata:
            return self._container.metadata['timecode']
        return None


class PyAVFrame:
    """PyAVフレーム実装"""
    
    def __init__(self, frame: av.VideoFrame, index: int):
        self._frame = frame
        self._index = index
        
    @property
    def index(self) -> int:
        return self._index
    
    @property
    def pts(self) -> int:
        return self._frame.pts or 0
    
    @property
    def dts(self) -> Optional[int]:
        return self._frame.dts
    
    def to_dict(self) -> Dict[str, Any]:
        """FrameDTOの辞書形式に変換"""
        # PyAVフレームをRGB24のnumpy配列に変換
        rgb_frame = self._frame.to_rgb()
        data = rgb_frame.to_ndarray()
        
        return {
            "index": self._index,
            "pts": self.pts,
            "dts": self.dts,
            "data": data,
            "width": self._frame.width,
            "height": self._frame.height,
            "timecode": None,  # TODO: フレーム単位のタイムコード計算
        }


class PyAVVideoReaderAdapter:
    """
    PyAVを使用したビデオ読み込みアダプター
    
    IVideoReaderインターフェースの実装。
    PyAV固有の型をDTOに変換して返す。
    """
    
    def __init__(self):
        self._container: Optional[av.container.Container] = None
        self._video_stream: Optional[av.stream.Stream] = None
        self._metadata: Optional[PyAVVideoMetadata] = None
        self._frame_index: int = 0
        
    def open(self, path: Union[str, Path]) -> IVideoMetadata:
        """動画ファイルを開く"""
        try:
            self._container = av.open(str(path))
            self._video_stream = next(s for s in self._container.streams if s.type == 'video')
            self._metadata = PyAVVideoMetadata(self._container)
            self._frame_index = 0
            return self._metadata
        except Exception as e:
            raise IOError(f"Failed to open video file: {path}") from e
    
    def read_frame(self, index: int) -> Optional[IFrame]:
        """指定インデックスのフレームを読み込む"""
        if not self._container or not self._video_stream:
            raise RuntimeError("Video not opened")
        
        # シークが必要か判定
        if index != self._frame_index:
            self.seek(index / self._metadata.fps)
        
        # フレームを読み込む
        try:
            for frame in self._container.decode(self._video_stream):
                if isinstance(frame, av.VideoFrame):
                    self._frame_index = index + 1
                    return PyAVFrame(frame, index)
        except av.AVError:
            pass
        
        return None
    
    def read_frames(self, start: int = 0, end: Optional[int] = None) -> Iterator[IFrame]:
        """フレームをイテレートして読み込む"""
        if not self._container or not self._video_stream:
            raise RuntimeError("Video not opened")
        
        # 開始位置にシーク
        if start > 0:
            self.seek(start / self._metadata.fps)
        
        frame_count = 0
        for packet in self._container.demux(self._video_stream):
            for frame in packet.decode():
                if isinstance(frame, av.VideoFrame):
                    current_index = start + frame_count
                    
                    if end is not None and current_index >= end:
                        return
                    
                    yield PyAVFrame(frame, current_index)
                    frame_count += 1
    
    def seek(self, timestamp: float) -> bool:
        """指定時間にシーク"""
        if not self._container or not self._video_stream:
            return False
        
        try:
            # タイムスタンプをストリームのタイムベースに変換
            pts = int(timestamp / float(self._video_stream.time_base))
            self._container.seek(pts, stream=self._video_stream)
            self._frame_index = int(timestamp * self._metadata.fps)
            return True
        except av.AVError:
            return False
    
    def close(self) -> None:
        """リソースを解放"""
        if self._container:
            self._container.close()
            self._container = None
            self._video_stream = None
            self._metadata = None
    
    def __enter__(self) -> 'PyAVVideoReaderAdapter':
        """コンテキストマネージャー開始"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャー終了"""
        self.close()
    
    def to_dto(self) -> VideoMetadataDTO:
        """現在のメタデータをDTOに変換"""
        if not self._metadata:
            raise RuntimeError("Video not opened")
        
        # オーディオ情報を取得
        audio_stream = next((s for s in self._container.streams if s.type == 'audio'), None)
        
        return VideoMetadataDTO(
            width=self._metadata.width,
            height=self._metadata.height,
            fps=self._metadata.fps,
            frame_count=self._metadata.frame_count,
            duration=self._metadata.duration,
            video_codec=self._metadata.codec,
            audio_codec=audio_stream.codec_context.name if audio_stream else None,
            video_bit_rate=self._metadata.bit_rate,
            audio_bit_rate=audio_stream.bit_rate if audio_stream else None,
            color_space=self._metadata.color_space,
            bit_depth=self._metadata.bit_depth,
            subsampling=None,  # TODO: PyAVからサブサンプリング情報を取得
            hdr_metadata=None,  # TODO: HDRメタデータの取得
            start_timecode=self._metadata.timecode,
            has_audio=self._metadata.has_audio,
            audio_channels=audio_stream.channels if audio_stream else None,
            audio_sample_rate=audio_stream.sample_rate if audio_stream else None,
            container_format=self._container.format.name if self._container else None,
        )