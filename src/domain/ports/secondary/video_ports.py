#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ビデオ処理ポート定義

ビデオの読み込み、書き出し、メタデータ処理に関するインターフェース。
"""
from typing import Protocol, Optional, Iterator, Dict, Any, Union
from pathlib import Path


class IVideoMetadata(Protocol):
    """ビデオメタデータインターフェース"""
    
    @property
    def width(self) -> int:
        """動画の幅（ピクセル）"""
        ...
    
    @property
    def height(self) -> int:
        """動画の高さ（ピクセル）"""
        ...
    
    @property
    def fps(self) -> float:
        """フレームレート"""
        ...
    
    @property
    def frame_count(self) -> int:
        """総フレーム数"""
        ...
    
    @property
    def duration(self) -> float:
        """動画の長さ（秒）"""
        ...
    
    @property
    def codec(self) -> str:
        """ビデオコーデック"""
        ...
    
    @property
    def bit_rate(self) -> Optional[int]:
        """ビットレート（bps）"""
        ...
    
    @property
    def color_space(self) -> Optional[str]:
        """色空間（BT.709, BT.2020等）"""
        ...
    
    @property
    def bit_depth(self) -> Optional[int]:
        """ビット深度（8, 10, 12等）"""
        ...
    
    @property
    def has_audio(self) -> bool:
        """音声トラックの有無"""
        ...
    
    @property
    def timecode(self) -> Optional[str]:
        """タイムコード"""
        ...


class IFrame(Protocol):
    """フレームデータインターフェース"""
    
    @property
    def index(self) -> int:
        """フレームインデックス（0始まり）"""
        ...
    
    @property
    def pts(self) -> int:
        """Presentation Timestamp"""
        ...
    
    @property
    def dts(self) -> Optional[int]:
        """Decode Timestamp"""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """DTOへの変換"""
        ...


class IVideoReader(Protocol):
    """ビデオ読み込みインターフェース"""
    
    def open(self, path: Union[str, Path]) -> IVideoMetadata:
        """
        動画ファイルを開く
        
        Args:
            path: 動画ファイルのパス
            
        Returns:
            ビデオメタデータ
            
        Raises:
            IOError: ファイルが開けない場合
        """
        ...
    
    def read_frame(self, index: int) -> Optional[IFrame]:
        """
        指定インデックスのフレームを読み込む
        
        Args:
            index: フレームインデックス
            
        Returns:
            フレームデータ（存在しない場合はNone）
        """
        ...
    
    def read_frames(self, start: int = 0, end: Optional[int] = None) -> Iterator[IFrame]:
        """
        フレームをイテレートして読み込む
        
        Args:
            start: 開始フレームインデックス
            end: 終了フレームインデックス（Noneの場合は最後まで）
            
        Yields:
            フレームデータ
        """
        ...
    
    def seek(self, timestamp: float) -> bool:
        """
        指定時間にシーク
        
        Args:
            timestamp: シーク先の時間（秒）
            
        Returns:
            成功した場合True
        """
        ...
    
    def close(self) -> None:
        """リソースを解放"""
        ...
    
    def __enter__(self) -> 'IVideoReader':
        """コンテキストマネージャー開始"""
        ...
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャー終了"""
        ...


class IVideoWriter(Protocol):
    """ビデオ書き出しインターフェース"""
    
    def open(self, path: Union[str, Path], metadata: IVideoMetadata) -> None:
        """
        書き出し用に動画ファイルを開く
        
        Args:
            path: 出力ファイルパス
            metadata: 動画メタデータ
            
        Raises:
            IOError: ファイルが作成できない場合
        """
        ...
    
    def write_frame(self, frame_data: Dict[str, Any]) -> None:
        """
        フレームを書き込む
        
        Args:
            frame_data: フレームDTO
            
        Raises:
            IOError: 書き込みエラー
        """
        ...
    
    def copy_stream(self, reader: IVideoReader, start: int = 0, end: Optional[int] = None) -> None:
        """
        ストリームをコピー（再エンコードなし）
        
        Args:
            reader: 入力リーダー
            start: 開始フレーム
            end: 終了フレーム
        """
        ...
    
    def close(self) -> None:
        """ファイルをファイナライズして閉じる"""
        ...
    
    def __enter__(self) -> 'IVideoWriter':
        """コンテキストマネージャー開始"""
        ...
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャー終了"""
        ...