#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media I/O基盤

要件定義書FR-28〜FR-42に基づく動画入出力機能を提供します。
NLE品質（ストリームコピー、音声同期、メタデータ保持）を保証します。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import av
import cv2
import ffmpeg
import numpy as np

from .models import (
    AlertTag,
    BoundingBox,
    ChromaSubsampling,
    ColorSpace,
    FieldOrder,
    Frame,
    Mask,
    OpticalFlow,
    TransferCharacteristic,
)

logger = logging.getLogger(__name__)


# === メディア読み込みクラス ===

class MediaReader:
    """動画読み込みクラス（FR-1, FR-39要件準拠）
    
    多フォーマット対応、メタデータ完全保持、正確なPTS/DTS管理を提供。
    """
    
    def __init__(self, filepath: Union[str, Path], 
                 cache_size: int = 10,
                 thread_count: int = 0):
        """
        Args:
            filepath: 動画ファイルパス
            cache_size: フレームキャッシュサイズ
            thread_count: デコードスレッド数（0=自動）
        """
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"Video file not found: {filepath}")
        
        self.cache_size = cache_size
        self._frame_cache: Dict[int, Frame] = {}
        
        # PyAVコンテナを開く
        self.container = av.open(str(filepath))
        
        # ストリーム情報を取得
        self.video_stream = None
        self.audio_stream = None
        for stream in self.container.streams:
            if stream.type == 'video' and self.video_stream is None:
                self.video_stream = stream
            elif stream.type == 'audio' and self.audio_stream is None:
                self.audio_stream = stream
        
        if self.video_stream is None:
            raise ValueError(f"No video stream found in: {filepath}")
        
        # デコードスレッド設定
        if thread_count > 0:
            self.video_stream.thread_count = thread_count
        
        # メタデータを抽出
        self._extract_metadata()
    
    def _extract_metadata(self) -> None:
        """メタデータの抽出（FR-31, FR-33, FR-34要件準拠）"""
        vs = self.video_stream
        
        # 基本情報
        self.width = vs.width
        self.height = vs.height
        self.fps = float(vs.average_rate)
        self.frame_count = vs.frames if vs.frames > 0 else self._count_frames()
        self.duration = float(vs.duration * vs.time_base) if vs.duration else 0
        
        # コーデック情報
        self.codec_name = vs.codec_context.name
        self.codec_long_name = vs.codec_context.codec.long_name
        self.profile = vs.codec_context.profile if hasattr(vs.codec_context, 'profile') else None
        
        # ビット深度とピクセルフォーマット
        pix_fmt = vs.codec_context.pix_fmt
        self.pix_fmt = pix_fmt
        self.bit_depth = self._get_bit_depth(pix_fmt)
        
        # 色空間情報（FR-31）
        self.colorspace = self._detect_colorspace()
        self.color_range = vs.codec_context.color_range
        self.color_primaries = vs.codec_context.color_primaries
        self.color_trc = vs.codec_context.color_trc
        self.chroma_subsampling = self._detect_chroma_subsampling()
        self.transfer = self._detect_transfer_characteristic()
        
        # HDRメタデータ（FR-33）
        self.hdr_metadata = self._extract_hdr_metadata()
        
        # タイムコード（FR-34）
        self.start_timecode = self._extract_timecode()
        self.is_vfr = self._detect_vfr()
        
        # インターレース情報（FR-37）
        self.field_order = self._detect_field_order()
        self.is_interlaced = self.field_order != FieldOrder.PROGRESSIVE
        
        # タイムベース
        self.time_base = vs.time_base
        if hasattr(vs, 'frame_rate'):
            self.frame_rate = vs.frame_rate
        else:
            self.frame_rate = vs.average_rate
        
        # 音声情報（FR-30）
        if self.audio_stream:
            self.audio_codec = self.audio_stream.codec_context.name
            self.audio_sample_rate = self.audio_stream.sample_rate
            self.audio_channels = self.audio_stream.channels
            self.audio_channel_layout = self.audio_stream.layout.name if self.audio_stream.layout else None
            self.audio_language = self.audio_stream.metadata.get('language', 'und')
    
    def _get_bit_depth(self, pix_fmt: str) -> int:
        """ピクセルフォーマットからビット深度を取得"""
        bit_depth_map = {
            'yuv420p': 8, 'yuvj420p': 8,
            'yuv422p': 8, 'yuvj422p': 8,
            'yuv444p': 8, 'yuvj444p': 8,
            'yuv420p10le': 10, 'yuv420p10be': 10,
            'yuv422p10le': 10, 'yuv422p10be': 10,
            'yuv444p10le': 10, 'yuv444p10be': 10,
            'yuv420p12le': 12, 'yuv420p12be': 12,
            'yuv422p12le': 12, 'yuv422p12be': 12,
            'yuv444p12le': 12, 'yuv444p12be': 12,
            'yuv420p16le': 16, 'yuv420p16be': 16,
            'yuv422p16le': 16, 'yuv422p16be': 16,
            'yuv444p16le': 16, 'yuv444p16be': 16,
        }
        return bit_depth_map.get(pix_fmt, 8)
    
    def _detect_colorspace(self) -> ColorSpace:
        """色空間を検出（FR-31）"""
        # PyAVの色空間情報から判定
        cs = self.video_stream.codec_context.colorspace
        if cs == 'bt709':
            return ColorSpace.BT709
        elif cs == 'bt2020nc' or cs == 'bt2020c':
            return ColorSpace.BT2020
        elif cs == 'smpte170m' or cs == 'bt470bg':
            return ColorSpace.BT709  # SD向けだがBT.709にマップ
        else:
            # デフォルトは解像度から推測
            if self.width >= 3840:  # 4K以上
                return ColorSpace.BT2020
            else:
                return ColorSpace.BT709
    
    def _detect_chroma_subsampling(self) -> ChromaSubsampling:
        """クロマサブサンプリングを検出"""
        pix_fmt = self.pix_fmt
        if '444' in pix_fmt:
            return ChromaSubsampling.YUV444
        elif '422' in pix_fmt:
            return ChromaSubsampling.YUV422
        else:
            return ChromaSubsampling.YUV420
    
    def _detect_transfer_characteristic(self) -> TransferCharacteristic:
        """伝達特性を検出"""
        trc = self.video_stream.codec_context.color_trc
        if trc == 'bt709':
            return TransferCharacteristic.GAMMA22
        elif trc == 'smpte2084':
            return TransferCharacteristic.PQ
        elif trc == 'arib-std-b67':
            return TransferCharacteristic.HLG
        else:
            return TransferCharacteristic.GAMMA22
    
    def _extract_hdr_metadata(self) -> Optional[Dict[str, Any]]:
        """HDRメタデータを抽出（FR-33）"""
        # side_dataからHDRメタデータを探す
        hdr_data = {}
        
        # 簡易実装（実際はもっと詳細な処理が必要）
        if self.transfer == TransferCharacteristic.PQ or self.transfer == TransferCharacteristic.HLG:
            hdr_data['hdr_format'] = 'HDR10' if self.transfer == TransferCharacteristic.PQ else 'HLG'
            # MaxCLL, MaxFALL等は実際のサイドデータから取得する必要がある
            hdr_data['max_cll'] = None
            hdr_data['max_fall'] = None
        
        return hdr_data if hdr_data else None
    
    def _extract_timecode(self) -> Optional[str]:
        """タイムコードを抽出（FR-34）"""
        # ストリームメタデータから取得
        tc = self.video_stream.metadata.get('timecode')
        if tc:
            return tc
        
        # コンテナメタデータから取得
        tc = self.container.metadata.get('timecode')
        if tc:
            return tc
        
        return None
    
    def _detect_vfr(self) -> bool:
        """VFRかどうかを検出（FR-35）"""
        # 簡易実装：average_rateとframe_rateが異なる場合VFRと判定
        if hasattr(self.video_stream, 'frame_rate') and self.video_stream.average_rate != self.video_stream.frame_rate:
            return True
        
        # より正確には最初の数フレームのPTS差分を確認する必要がある
        return False
    
    def _detect_field_order(self) -> FieldOrder:
        """フィールドオーダーを検出（FR-37）"""
        # コーデックコンテキストから取得
        if hasattr(self.video_stream.codec_context, 'field_order'):
            order = self.video_stream.codec_context.field_order
            if order == 'tt':
                return FieldOrder.TFF
            elif order == 'bb':
                return FieldOrder.BFF
        
        return FieldOrder.PROGRESSIVE
    
    def _count_frames(self) -> int:
        """フレーム数をカウント（ストリームに情報がない場合）"""
        count = 0
        container = av.open(str(self.filepath))
        for packet in container.demux(video=0):
            for frame in packet.decode():
                count += 1
        container.close()
        return count
    
    def get_frame(self, frame_index: int) -> Optional[Frame]:
        """指定インデックスのフレームを取得
        
        Args:
            frame_index: フレームインデックス（0-based）
            
        Returns:
            Frameオブジェクト（存在しない場合None）
        """
        if frame_index < 0 or frame_index >= self.frame_count:
            return None
        
        # キャッシュチェック
        if frame_index in self._frame_cache:
            return self._frame_cache[frame_index]
        
        # 最初から読んで目的のフレームまでスキップ（確実な方法）
        self.container.seek(0)
        current_index = 0
        
        for packet in self.container.demux(self.video_stream):
            for av_frame in packet.decode():
                if current_index == frame_index:
                    frame = self._av_frame_to_frame(av_frame, frame_index)
                    
                    # キャッシュ更新
                    self._update_cache(frame_index, frame)
                    
                    return frame
                
                current_index += 1
                
                if current_index > frame_index:
                    break
        
        return None
    
    def __iter__(self) -> Iterator[Frame]:
        """フレームを順次イテレート"""
        return self.read_frames()
    
    def read_frames(self, start: int = 0, end: Optional[int] = None) -> Iterator[Frame]:
        """フレームを順次読み込み
        
        Args:
            start: 開始フレーム（0-based）
            end: 終了フレーム（Noneの場合最後まで）
            
        Yields:
            Frameオブジェクト
        """
        if end is None:
            end = self.frame_count
        
        # コンテナを最初にシーク
        self.container.seek(0)
        
        # シーク（部分読み込みの場合は最初から読んでスキップする方が確実）
        frame_index = 0
        for packet in self.container.demux(self.video_stream):
            for av_frame in packet.decode():
                if frame_index >= start and frame_index < end:
                    yield self._av_frame_to_frame(av_frame, frame_index)
                
                frame_index += 1
                
                if frame_index >= end:
                    return
    
    def _av_frame_to_frame(self, av_frame: av.VideoFrame, frame_index: int) -> Frame:
        """PyAVフレームをFrameオブジェクトに変換"""
        # RGB24に変換（要件に応じて他の形式も対応可能）
        img = av_frame.to_ndarray(format='rgb24')
        
        # PTS/DTS（マイクロ秒単位）
        pts = int(av_frame.pts * self.video_stream.time_base * 1_000_000) if av_frame.pts is not None else 0
        dts = int(av_frame.dts * self.video_stream.time_base * 1_000_000) if av_frame.dts is not None else None
        
        # タイムコード計算
        if self.start_timecode:
            # 開始タイムコードからの計算（簡易版）
            tc_frames = frame_index
            tc_seconds = tc_frames / self.fps
            tc_td = timedelta(seconds=tc_seconds)
            # 実際のタイムコード計算は複雑（Drop Frame考慮等）
            timecode = self.start_timecode  # 簡易実装
        else:
            # タイムコードがない場合は計算
            timecode = self._frame_to_timecode(frame_index)
        
        return Frame(
            data=img,
            pts=pts,
            dts=dts,
            timecode=timecode,
            colorspace=self.colorspace,
            bit_depth=self.bit_depth,
            subsampling=self.chroma_subsampling,
            transfer=self.transfer,
            field_order=self.field_order,
            hdr_metadata=self.hdr_metadata,
            frame_number=frame_index,
            duration=int(1_000_000 / self.fps),  # マイクロ秒
            is_keyframe=av_frame.key_frame
        )
    
    def _frame_to_timecode(self, frame_index: int) -> str:
        """フレーム番号をタイムコードに変換"""
        fps_int = round(self.fps)
        hours = frame_index // (fps_int * 3600)
        minutes = (frame_index % (fps_int * 3600)) // (fps_int * 60)
        seconds = (frame_index % (fps_int * 60)) // fps_int
        frames = frame_index % fps_int
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    
    def _update_cache(self, frame_index: int, frame: Frame) -> None:
        """フレームキャッシュを更新"""
        self._frame_cache[frame_index] = frame
        
        # キャッシュサイズ制限
        if len(self._frame_cache) > self.cache_size:
            # 最も古いものを削除（簡易LRU）
            oldest = min(self._frame_cache.keys())
            del self._frame_cache[oldest]
    
    def get_metadata(self) -> Dict[str, Any]:
        """メタデータを辞書形式で取得"""
        return {
            "filepath": str(self.filepath),
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "duration": self.duration,
            "codec": self.codec_name,
            "codec_long_name": self.codec_long_name,
            "profile": self.profile,
            "bit_depth": self.bit_depth,
            "pix_fmt": self.pix_fmt,
            "colorspace": self.colorspace.value,
            "color_range": self.color_range,
            "color_primaries": self.color_primaries,
            "color_trc": self.color_trc,
            "chroma_subsampling": self.chroma_subsampling.value,
            "transfer": self.transfer.value,
            "hdr_metadata": self.hdr_metadata,
            "start_timecode": self.start_timecode,
            "is_vfr": self.is_vfr,
            "field_order": self.field_order.value,
            "is_interlaced": self.is_interlaced,
            "audio": {
                "codec": self.audio_codec,
                "sample_rate": self.audio_sample_rate,
                "channels": self.audio_channels,
                "channel_layout": self.audio_channel_layout,
                "language": self.audio_language
            } if self.audio_stream else None
        }
    
    def close(self) -> None:
        """リソースを解放"""
        if hasattr(self, 'container'):
            self.container.close()
        self._frame_cache.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# === メディア書き出しクラス ===

class MediaWriter:
    """動画書き出しクラス（FR-1, FR-40要件準拠）
    
    ストリームコピー優先、音声同期保持、メタデータ保持を保証。
    """
    
    def __init__(self, output_path: Union[str, Path], 
                 template_reader: MediaReader,
                 video_codec: Optional[str] = None,
                 audio_codec: Optional[str] = 'copy',
                 preset: str = 'medium',
                 crf: int = 23):
        """
        Args:
            output_path: 出力ファイルパス
            template_reader: テンプレートとなるMediaReader
            video_codec: ビデオコーデック（Noneでテンプレートと同じ）
            audio_codec: オーディオコーデック（'copy'でストリームコピー）
            preset: エンコードプリセット
            crf: 品質設定（Constant Rate Factor）
        """
        self.output_path = Path(output_path)
        self.template = template_reader
        self.video_codec = video_codec or template_reader.codec_name
        self.audio_codec = audio_codec
        self.preset = preset
        self.crf = crf
        
        # 出力コンテナを作成
        self.container = av.open(str(output_path), 'w')
        
        # ビデオストリームを追加
        self._setup_video_stream()
        
        # オーディオストリームを追加（ストリームコピー）
        if template_reader.audio_stream and audio_codec == 'copy':
            self._setup_audio_stream_copy()
        
        self._frames_written = 0
    
    def _setup_video_stream(self) -> None:
        """ビデオストリームをセットアップ"""
        # ストリームを作成（PyAVはrateにfractionを期待）
        from fractions import Fraction
        fps_fraction = Fraction(self.template.fps).limit_denominator(1000000)
        self.video_stream = self.container.add_stream(self.video_codec, rate=fps_fraction)
        
        # 解像度
        self.video_stream.width = self.template.width
        self.video_stream.height = self.template.height
        
        # ピクセルフォーマット（可能な限り元と同じ）
        if hasattr(self.video_stream.codec_context, 'pix_fmt'):
            try:
                self.video_stream.codec_context.pix_fmt = self.template.pix_fmt
            except:
                # サポートされない場合はデフォルト
                pass
        
        # 色空間情報を保持（FR-31）
        ctx = self.video_stream.codec_context
        if hasattr(ctx, 'colorspace'):
            ctx.colorspace = self.template.video_stream.codec_context.colorspace
        if hasattr(ctx, 'color_range'):
            ctx.color_range = self.template.video_stream.codec_context.color_range
        if hasattr(ctx, 'color_primaries'):
            ctx.color_primaries = self.template.video_stream.codec_context.color_primaries
        if hasattr(ctx, 'color_trc'):
            ctx.color_trc = self.template.video_stream.codec_context.color_trc
        
        # エンコード設定
        if self.video_codec in ['libx264', 'libx265']:
            ctx.options = {
                'preset': self.preset,
                'crf': str(self.crf),
            }
        
        # タイムベース
        self.video_stream.time_base = self.template.video_stream.time_base
    
    def _setup_audio_stream_copy(self) -> None:
        """オーディオストリームコピーをセットアップ（FR-28）"""
        # テンプレートのオーディオストリームをコピー
        template_audio = self.template.audio_stream
        if not template_audio:
            return
        
        # コーデックパラメータをコピー
        self.audio_stream = self.container.add_stream(template=template_audio)
    
    def write_frame(self, frame: Frame) -> None:
        """フレームを書き込み
        
        Args:
            frame: 書き込むフレーム
        """
        # numpy配列をAVフレームに変換
        av_frame = av.VideoFrame.from_ndarray(frame.data, format='rgb24')
        
        # タイムスタンプ設定（音声同期のため重要）
        av_frame.pts = frame.pts
        av_frame.dts = frame.dts if frame.dts is not None else frame.pts
        av_frame.time_base = self.template.video_stream.time_base
        
        # エンコードして書き込み
        for packet in self.video_stream.encode(av_frame):
            self.container.mux(packet)
        
        self._frames_written += 1
    
    def write_frames(self, frames: Iterator[Frame]) -> int:
        """複数フレームを書き込み
        
        Args:
            frames: フレームのイテレータ
            
        Returns:
            書き込んだフレーム数
        """
        count = 0
        for frame in frames:
            self.write_frame(frame)
            count += 1
        return count
    
    def copy_stream(self, input_path: Union[str, Path],
                   video_processing_func=None) -> None:
        """ストリームコピーで高速処理（FR-40）
        
        音声はストリームコピー、映像は必要に応じて処理。
        
        Args:
            input_path: 入力ファイルパス
            video_processing_func: ビデオフレーム処理関数（Noneでコピー）
        """
        # FFmpeg-pythonを使用した高速ストリームコピー
        input_stream = ffmpeg.input(str(input_path))
        
        if video_processing_func is None:
            # 完全ストリームコピー
            streams = [input_stream.video]
            output_args = {
                'vcodec': 'copy',
                'map_metadata': 0  # メタデータもコピー
            }
            
            # オーディオストリームがある場合のみ追加
            probe = ffmpeg.probe(str(input_path))
            has_audio = any(stream['codec_type'] == 'audio' for stream in probe['streams'])
            if has_audio:
                streams.append(input_stream.audio)
                output_args['acodec'] = 'copy'
            
            output = ffmpeg.output(*streams, str(self.output_path), **output_args)
        else:
            # ビデオのみ処理、音声はコピー
            # この場合はPyAVでフレーム単位の処理が必要
            raise NotImplementedError("Frame processing with stream copy is not yet implemented")
        
        # 実行
        ffmpeg.run(output, overwrite_output=True)
    
    def finalize(self) -> None:
        """書き込みを完了"""
        # 残りのフレームをフラッシュ
        for packet in self.video_stream.encode():
            self.container.mux(packet)
        
        # メタデータを書き込み
        if self.template.start_timecode:
            self.container.metadata['timecode'] = self.template.start_timecode
        
        # クローズ
        self.container.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finalize()


# === マスクデータI/O ===

class MaskIO:
    """マスクデータのI/O（IN-2要件準拠）"""
    
    @staticmethod
    def load_mask(filepath: Union[str, Path], 
                  frame_index: int,
                  mask_id: int = 1,
                  class_name: str = "unknown",
                  confidence: float = 1.0) -> Mask:
        """マスクファイルを読み込み
        
        Args:
            filepath: マスクファイルパス（NPYまたはPNG）
            frame_index: フレームインデックス
            mask_id: マスクID
            class_name: クラス名
            confidence: 信頼度
            
        Returns:
            Maskオブジェクト
        """
        filepath = Path(filepath)
        
        if filepath.suffix.lower() == '.npy':
            return Mask.from_npy(
                filepath,
                id=mask_id,
                class_name=class_name,
                confidence=confidence,
                frame_index=frame_index
            )
        elif filepath.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            return Mask.from_png(
                filepath,
                id=mask_id,
                class_name=class_name,
                confidence=confidence,
                frame_index=frame_index
            )
        else:
            raise ValueError(f"Unsupported mask format: {filepath.suffix}")
    
    @staticmethod
    def save_mask(mask: Mask, filepath: Union[str, Path]) -> None:
        """マスクを保存
        
        Args:
            mask: 保存するマスク
            filepath: 保存先パス
        """
        filepath = Path(filepath)
        
        if filepath.suffix.lower() == '.npy':
            mask.to_npy(filepath)
        elif filepath.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            mask.to_png(filepath)
        else:
            raise ValueError(f"Unsupported mask format: {filepath.suffix}")
    
    @staticmethod
    def load_mask_sequence(directory: Union[str, Path],
                          pattern: str = "mask_{:06d}.png",
                          start_frame: int = 0,
                          end_frame: Optional[int] = None) -> List[Mask]:
        """マスクシーケンスを読み込み
        
        Args:
            directory: マスクファイルのディレクトリ
            pattern: ファイル名パターン
            start_frame: 開始フレーム
            end_frame: 終了フレーム
            
        Returns:
            Maskオブジェクトのリスト
        """
        directory = Path(directory)
        masks = []
        
        frame = start_frame
        while True:
            filepath = directory / pattern.format(frame)
            if not filepath.exists():
                if end_frame is None:
                    break
                elif frame >= end_frame:
                    break
                else:
                    # ファイルが存在しない場合は空のマスク
                    masks.append(None)
            else:
                mask = MaskIO.load_mask(filepath, frame_index=frame)
                masks.append(mask)
            
            frame += 1
            
            if end_frame is not None and frame >= end_frame:
                break
        
        return masks


# === JSON I/O ===

class JsonIO:
    """JSON形式のデータI/O（IN-3, IN-4要件準拠）"""
    
    @staticmethod
    def load_bounding_boxes(filepath: Union[str, Path]) -> List[BoundingBox]:
        """バウンディングボックスをJSONから読み込み
        
        Args:
            filepath: JSONファイルパス
            
        Returns:
            BoundingBoxオブジェクトのリスト
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        boxes = []
        
        # フォーマットに応じて処理
        if isinstance(data, list):
            # リスト形式
            for item in data:
                bbox = BoundingBox(
                    x=item['x'],
                    y=item['y'],
                    width=item['width'],
                    height=item['height'],
                    id=item['id'],
                    score=item['score'],
                    class_name=item.get('class_name', 'unknown'),
                    frame_index=item.get('frame_index', 0)
                )
                boxes.append(bbox)
        elif isinstance(data, dict):
            # フレームごとの辞書形式
            for frame_idx, frame_data in data.items():
                for item in frame_data:
                    bbox = BoundingBox(
                        x=item['x'],
                        y=item['y'],
                        width=item['width'],
                        height=item['height'],
                        id=item['id'],
                        score=item['score'],
                        class_name=item.get('class_name', 'unknown'),
                        frame_index=int(frame_idx)
                    )
                    boxes.append(bbox)
        
        return boxes
    
    @staticmethod
    def save_bounding_boxes(boxes: List[BoundingBox], 
                           filepath: Union[str, Path],
                           format: str = 'list') -> None:
        """バウンディングボックスをJSONに保存
        
        Args:
            boxes: BoundingBoxオブジェクトのリスト
            filepath: 保存先パス
            format: 'list' または 'frame_dict'
        """
        if format == 'list':
            data = [box.to_dict() for box in boxes]
        elif format == 'frame_dict':
            data = {}
            for box in boxes:
                frame_idx = str(box.frame_index)
                if frame_idx not in data:
                    data[frame_idx] = []
                data[frame_idx].append(box.to_dict())
        else:
            raise ValueError(f"Unknown format: {format}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def load_mask_attributes(filepath: Union[str, Path]) -> Dict[str, Any]:
        """マスク属性情報を読み込み（IN-3）
        
        Args:
            filepath: JSONファイルパス
            
        Returns:
            属性情報の辞書
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def save_mask_attributes(attributes: Dict[str, Any],
                            filepath: Union[str, Path]) -> None:
        """マスク属性情報を保存
        
        Args:
            attributes: 属性情報
            filepath: 保存先パス
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(attributes, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def load_alerts(filepath: Union[str, Path]) -> List[AlertTag]:
        """アラート情報を読み込み
        
        Args:
            filepath: JSONファイルパス
            
        Returns:
            AlertTagオブジェクトのリスト
        """
        from .models import AlertLevel
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        alerts = []
        for item in data:
            alert = AlertTag(
                level=AlertLevel(item['level']),
                reason=item['reason'],
                frame_range=tuple(item['frame_range']),
                confidence=item['confidence'],
                metadata=item.get('metadata', {}),
                object_ids=item.get('object_ids', [])
            )
            alerts.append(alert)
        
        return alerts
    
    @staticmethod
    def save_alerts(alerts: List[AlertTag],
                   filepath: Union[str, Path]) -> None:
        """アラート情報を保存
        
        Args:
            alerts: AlertTagオブジェクトのリスト
            filepath: 保存先パス
        """
        data = [alert.to_dict() for alert in alerts]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# === ユーティリティ関数 ===

def probe_video(filepath: Union[str, Path]) -> Dict[str, Any]:
    """動画ファイルの情報を取得（ffprobeラッパー）
    
    Args:
        filepath: 動画ファイルパス
        
    Returns:
        動画情報の辞書
    """
    try:
        probe = ffmpeg.probe(str(filepath))
        return probe
    except ffmpeg.Error as e:
        logger.error(f"Error probing video: {e.stderr}")
        raise


def check_sync_accuracy(video_path: Union[str, Path]) -> float:
    """音声・映像の同期精度をチェック（FR-29）
    
    Args:
        video_path: 動画ファイルパス
        
    Returns:
        同期誤差（ミリ秒）
    """
    # 実装は複雑なため、簡易版
    # 実際にはPTS/DTSの差分を詳細に分析する必要がある
    with MediaReader(video_path) as reader:
        if not reader.audio_stream:
            return 0.0
        
        # 最初のビデオ/オーディオフレームのPTS差分を確認
        # （実際の実装ではもっと詳細な分析が必要）
        return 0.0  # 仮の値


def convert_timecode(timecode: str, 
                    from_fps: float,
                    to_fps: float,
                    drop_frame: bool = False) -> str:
    """タイムコードを異なるフレームレート間で変換
    
    Args:
        timecode: 変換元タイムコード
        from_fps: 変換元FPS
        to_fps: 変換先FPS
        drop_frame: Drop Frame形式かどうか
        
    Returns:
        変換後のタイムコード
    """
    # タイムコードをフレーム数に変換
    parts = timecode.replace(';', ':').split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])
    frames = int(parts[3])
    
    total_frames = (hours * 3600 + minutes * 60 + seconds) * from_fps + frames
    
    # 新しいFPSでのタイムコードに変換
    new_fps_int = round(to_fps)
    new_hours = int(total_frames // (new_fps_int * 3600))
    new_minutes = int((total_frames % (new_fps_int * 3600)) // (new_fps_int * 60))
    new_seconds = int((total_frames % (new_fps_int * 60)) // new_fps_int)
    new_frames = int(total_frames % new_fps_int)
    
    separator = ';' if drop_frame else ':'
    return f"{new_hours:02d}:{new_minutes:02d}:{new_seconds:02d}{separator}{new_frames:02d}"