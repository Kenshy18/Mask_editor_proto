#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入力データソースポート定義

AI生成マスクとバウンディングボックスの入力ソースを抽象化。
将来的な入力フォーマットの変更に備える。
"""
from typing import Protocol, Optional, List, Dict, Any, Iterator
from pathlib import Path


class IDetection(Protocol):
    """検出情報インターフェース"""
    
    @property
    def track_id(self) -> int:
        """トラッキングID"""
        ...
    
    @property
    def class_id(self) -> int:
        """クラスID"""
        ...
    
    @property
    def class_name(self) -> str:
        """クラス名"""
        ...
    
    @property
    def confidence(self) -> float:
        """信頼度（0.0-1.0）"""
        ...
    
    @property
    def bbox(self) -> Dict[str, float]:
        """バウンディングボックス（x1, y1, x2, y2）"""
        ...


class IInputDataSource(Protocol):
    """
    入力データソースインターフェース
    
    注意: このインターフェースは暫定的なものです。
    将来的に入力データ形式が変更される可能性があります。
    """
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        データソースを初期化
        
        Args:
            config: 設定辞書（パス、接続情報など）
        """
        ...
    
    def get_video_path(self) -> Path:
        """
        動画ファイルパスを取得
        
        Returns:
            動画ファイルパス
            
        Raises:
            FileNotFoundError: 動画ファイルが存在しない
        """
        ...
    
    def get_video_metadata(self) -> Dict[str, Any]:
        """
        動画メタデータを取得
        
        Returns:
            メタデータ辞書（width, height, fps, total_frames等）
        """
        ...
    
    def get_detections(self, frame_index: int) -> List[Dict[str, Any]]:
        """
        指定フレームの検出情報を取得
        
        Args:
            frame_index: フレーム番号（0-based）
            
        Returns:
            検出情報DTOのリスト
        """
        ...
    
    def get_mask(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """
        指定フレームのマスクを取得
        
        Args:
            frame_index: フレーム番号（0-based）
            
        Returns:
            マスクDTO（存在しない場合はNone）
        """
        ...
    
    def get_frame_indices(self) -> List[int]:
        """
        利用可能なフレームインデックスのリストを取得
        
        Returns:
            フレームインデックスのリスト
        """
        ...
    
    def iterate_frames(self, start: int = 0, end: Optional[int] = None) -> Iterator[tuple[int, List[Dict[str, Any]], Optional[Dict[str, Any]]]]:
        """
        フレームを順次イテレート
        
        Args:
            start: 開始フレーム
            end: 終了フレーム（Noneの場合は最後まで）
            
        Yields:
            (frame_index, detections, mask)のタプル
        """
        ...
    
    def close(self) -> None:
        """リソースを解放"""
        ...


class IInputDataValidator(Protocol):
    """入力データ検証インターフェース"""
    
    def validate_video(self, video_path: Path) -> bool:
        """
        動画ファイルの妥当性を検証
        
        Args:
            video_path: 動画ファイルパス
            
        Returns:
            妥当な場合True
        """
        ...
    
    def validate_detections(self, detections: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        検出情報の妥当性を検証
        
        Args:
            detections: 検出情報辞書
            
        Returns:
            (妥当性, エラーメッセージリスト)
        """
        ...
    
    def validate_mask(self, mask_data: Any, frame_index: int, detections: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
        """
        マスクデータの妥当性を検証
        
        Args:
            mask_data: マスクデータ
            frame_index: フレーム番号
            detections: 対応する検出情報
            
        Returns:
            (妥当性, エラーメッセージリスト)
        """
        ...
    
    def validate_consistency(self, video_metadata: Dict[str, Any], detections_metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        動画と検出情報の整合性を検証
        
        Args:
            video_metadata: 動画メタデータ
            detections_metadata: 検出情報メタデータ
            
        Returns:
            (整合性, エラーメッセージリスト)
        """
        ...


class IInputDataCache(Protocol):
    """入力データキャッシュインターフェース"""
    
    def cache_detections(self, frame_index: int, detections: List[Dict[str, Any]]) -> None:
        """検出情報をキャッシュ"""
        ...
    
    def get_cached_detections(self, frame_index: int) -> Optional[List[Dict[str, Any]]]:
        """キャッシュから検出情報を取得"""
        ...
    
    def cache_mask(self, frame_index: int, mask: Dict[str, Any]) -> None:
        """マスクをキャッシュ"""
        ...
    
    def get_cached_mask(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """キャッシュからマスクを取得"""
        ...
    
    def clear_cache(self, frame_index: Optional[int] = None) -> None:
        """キャッシュをクリア（frame_indexがNoneの場合は全クリア）"""
        ...