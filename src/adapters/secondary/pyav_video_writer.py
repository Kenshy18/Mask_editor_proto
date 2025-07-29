#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyAV Video Writer Adapter

PyAVを使用したビデオ書き出しアダプター実装。
IVideoWriterポートの実装を提供。
"""
from typing import Optional, Union, Dict, Any
from pathlib import Path
import numpy as np
import av
from fractions import Fraction

from domain.ports.secondary import IVideoWriter, IVideoReader, IVideoMetadata
from domain.dto import FrameDTO, VideoMetadataDTO


class PyAVVideoWriterAdapter:
    """
    PyAVを使用したビデオ書き出しアダプター
    
    IVideoWriterインターフェースの実装。
    ストリームコピーを優先的に使用（FR-28）。
    """
    
    def __init__(self):
        self._container: Optional[av.container.OutputContainer] = None
        self._video_stream: Optional[av.stream.Stream] = None
        self._audio_stream: Optional[av.stream.Stream] = None
        self._metadata: Optional[VideoMetadataDTO] = None
        self._frame_count: int = 0
        self._stream_copy_mode: bool = False
        
    def open(self, path: Union[str, Path], metadata: IVideoMetadata) -> None:
        """書き出し用に動画ファイルを開く"""
        try:
            # メタデータをDTOに変換（互換性のため）
            if hasattr(metadata, 'to_dict'):
                metadata_dict = metadata.to_dict()
                self._metadata = VideoMetadataDTO.from_dict(metadata_dict)
            else:
                # IVideoMetadataから直接DTOを構築
                self._metadata = VideoMetadataDTO(
                    width=metadata.width,
                    height=metadata.height,
                    fps=metadata.fps,
                    frame_count=metadata.frame_count,
                    duration=metadata.duration,
                    video_codec=metadata.codec,
                    audio_codec=None,
                    video_bit_rate=metadata.bit_rate,
                    has_audio=metadata.has_audio,
                )
            
            # コンテナを作成
            self._container = av.open(str(path), mode='w')
            
            # ビデオストリームを追加
            self._setup_video_stream()
            
            # オーディオストリームを追加（必要な場合）
            if self._metadata.has_audio:
                self._setup_audio_stream()
                
        except Exception as e:
            raise IOError(f"Failed to create output file: {path}") from e
    
    def _setup_video_stream(self) -> None:
        """ビデオストリームをセットアップ"""
        # コーデックを選択
        codec_name = self._metadata.video_codec
        if codec_name in ['h264', 'libx264']:
            codec_name = 'libx264'
        elif codec_name in ['h265', 'hevc', 'libx265']:
            codec_name = 'libx265'
        
        # ストリームを作成
        self._video_stream = self._container.add_stream(codec_name, rate=self._metadata.fps)
        
        # ストリーム設定
        self._video_stream.width = self._metadata.width
        self._video_stream.height = self._metadata.height
        self._video_stream.pix_fmt = 'yuv420p'  # 互換性のため
        
        # ビットレート設定
        if self._metadata.video_bit_rate:
            self._video_stream.bit_rate = self._metadata.video_bit_rate
        
        # タイムベース設定
        fps_fraction = Fraction(self._metadata.fps).limit_denominator(1000000)
        self._video_stream.time_base = Fraction(1, fps_fraction.denominator)
        
        # コーデックオプション
        if codec_name == 'libx264':
            self._video_stream.options = {
                'crf': '23',
                'preset': 'medium',
                'profile': 'high',
            }
    
    def _setup_audio_stream(self) -> None:
        """オーディオストリームをセットアップ"""
        if not self._metadata.audio_codec:
            return
        
        codec_name = self._metadata.audio_codec
        if codec_name in ['aac', 'libfdk_aac']:
            codec_name = 'aac'
        
        self._audio_stream = self._container.add_stream(codec_name)
        
        if self._metadata.audio_channels:
            self._audio_stream.channels = self._metadata.audio_channels
        
        if self._metadata.audio_sample_rate:
            self._audio_stream.rate = self._metadata.audio_sample_rate
        
        if self._metadata.audio_bit_rate:
            self._audio_stream.bit_rate = self._metadata.audio_bit_rate
    
    def write_frame(self, frame_data: Dict[str, Any]) -> None:
        """フレームを書き込む"""
        if not self._container or not self._video_stream:
            raise RuntimeError("Video not opened for writing")
        
        # DTOから作成またはdictから作成
        if isinstance(frame_data, dict):
            frame_dto = FrameDTO.from_dict(frame_data)
        else:
            frame_dto = frame_data
        
        # numpy配列からAVフレームを作成
        av_frame = av.VideoFrame.from_ndarray(frame_dto.data, format='rgb24')
        av_frame.pts = frame_dto.pts
        av_frame.time_base = self._video_stream.time_base
        
        # エンコードして書き込み
        for packet in self._video_stream.encode(av_frame):
            self._container.mux(packet)
        
        self._frame_count += 1
    
    def copy_stream(self, reader: IVideoReader, start: int = 0, end: Optional[int] = None) -> None:
        """
        ストリームをコピー（再エンコードなし）
        
        FR-28: ストリームコピーを優先使用
        """
        if not self._container:
            raise RuntimeError("Video not opened for writing")
        
        # PyAVリーダーの場合は直接ストリームコピー
        if hasattr(reader, '_container') and hasattr(reader, '_video_stream'):
            self._stream_copy_mode = True
            self._copy_pyav_stream(reader, start, end)
        else:
            # その他のリーダーの場合は通常の読み書き
            for frame in reader.read_frames(start, end):
                self.write_frame(frame.to_dict())
    
    def _copy_pyav_stream(self, reader: Any, start: int, end: Optional[int]) -> None:
        """PyAVストリームを直接コピー"""
        input_container = reader._container
        input_stream = reader._video_stream
        
        # ストリームコピー用の設定
        self._video_stream.codec_context.codec_tag = input_stream.codec_context.codec_tag
        
        # 開始位置にシーク
        if start > 0:
            reader.seek(start / reader._metadata.fps)
        
        # パケットをコピー
        packet_count = 0
        for packet in input_container.demux(input_stream):
            if packet.dts is None:
                continue
            
            # フレーム範囲チェック
            if end is not None:
                frame_index = int(packet.pts * float(input_stream.time_base) * reader._metadata.fps)
                if frame_index >= end:
                    break
            
            # パケットをリマップしてmux
            packet.stream = self._video_stream
            self._container.mux(packet)
            packet_count += 1
        
        # オーディオストリームもコピー（存在する場合）
        if self._metadata.has_audio and self._audio_stream:
            for input_audio_stream in input_container.streams.audio:
                for packet in input_container.demux(input_audio_stream):
                    packet.stream = self._audio_stream
                    self._container.mux(packet)
    
    def close(self) -> None:
        """ファイルをファイナライズして閉じる"""
        if self._container:
            # 残りのフレームをフラッシュ
            if self._video_stream and not self._stream_copy_mode:
                for packet in self._video_stream.encode(None):
                    self._container.mux(packet)
            
            # コンテナを閉じる
            self._container.close()
            self._container = None
            self._video_stream = None
            self._audio_stream = None
    
    def __enter__(self) -> 'PyAVVideoWriterAdapter':
        """コンテキストマネージャー開始"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャー終了"""
        self.close()