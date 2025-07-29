#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスク処理ポート定義

マスクの読み込み、書き出し、処理に関するインターフェース。
"""
from typing import Protocol, Optional, List, Dict, Any, Tuple, Union, Iterator
from pathlib import Path
import numpy as np


class IMaskMetadata(Protocol):
    """マスクメタデータインターフェース"""
    
    @property
    def width(self) -> int:
        """マスクの幅"""
        ...
    
    @property
    def height(self) -> int:
        """マスクの高さ"""
        ...
    
    @property
    def object_ids(self) -> List[int]:
        """含まれるオブジェクトID一覧"""
        ...
    
    @property
    def classes(self) -> Dict[int, str]:
        """ID -> クラス名のマッピング"""
        ...
    
    @property
    def confidences(self) -> Dict[int, float]:
        """ID -> 信頼度のマッピング"""
        ...


class IMaskReader(Protocol):
    """マスク読み込みインターフェース"""
    
    def read_mask(self, path: Union[str, Path], frame_index: int) -> Optional[Dict[str, Any]]:
        """
        マスクを読み込む
        
        Args:
            path: マスクファイルパス（ディレクトリまたはファイル）
            frame_index: フレームインデックス
            
        Returns:
            マスクDTO（存在しない場合はNone）
        """
        ...
    
    def read_mask_sequence(self, path: Union[str, Path], start: int = 0, end: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        """
        マスクシーケンスを読み込む
        
        Args:
            path: マスクディレクトリパス
            start: 開始フレーム
            end: 終了フレーム
            
        Yields:
            マスクDTO
        """
        ...
    
    def get_metadata(self, path: Union[str, Path]) -> IMaskMetadata:
        """
        マスクメタデータを取得
        
        Args:
            path: マスクパス
            
        Returns:
            マスクメタデータ
        """
        ...


class IMaskWriter(Protocol):
    """マスク書き出しインターフェース"""
    
    def write_mask(self, mask_data: Dict[str, Any], path: Union[str, Path], frame_index: int) -> None:
        """
        マスクを書き出す
        
        Args:
            mask_data: マスクDTO
            path: 出力パス（ディレクトリまたはファイル）
            frame_index: フレームインデックス
        """
        ...
    
    def write_mask_sequence(self, masks: List[Dict[str, Any]], path: Union[str, Path]) -> None:
        """
        マスクシーケンスを書き出す
        
        Args:
            masks: マスクDTOのリスト
            path: 出力ディレクトリパス
        """
        ...


class IMaskProcessor(Protocol):
    """マスク処理インターフェース"""
    
    def dilate(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """
        膨張処理
        
        Args:
            mask_data: 入力マスクDTO
            kernel_size: カーネルサイズ
            
        Returns:
            処理後のマスクDTO
        """
        ...
    
    def erode(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """
        収縮処理
        
        Args:
            mask_data: 入力マスクDTO
            kernel_size: カーネルサイズ
            
        Returns:
            処理後のマスクDTO
        """
        ...
    
    def open(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """
        オープン処理（収縮→膨張）
        
        Args:
            mask_data: 入力マスクDTO
            kernel_size: カーネルサイズ
            
        Returns:
            処理後のマスクDTO
        """
        ...
    
    def close(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """
        クローズ処理（膨張→収縮）
        
        Args:
            mask_data: 入力マスクDTO
            kernel_size: カーネルサイズ
            
        Returns:
            処理後のマスクDTO
        """
        ...
    
    def merge_masks(self, masks: List[Dict[str, Any]], method: str = "union") -> Dict[str, Any]:
        """
        複数マスクのマージ
        
        Args:
            masks: マスクDTOのリスト
            method: マージ方法（"union", "intersection", "difference"）
            
        Returns:
            マージ後のマスクDTO
        """
        ...
    
    def split_by_id(self, mask_data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """
        IDごとにマスクを分割
        
        Args:
            mask_data: 入力マスクDTO
            
        Returns:
            ID -> マスクDTOのマッピング
        """
        ...
    
    def calculate_bbox(self, mask_data: Dict[str, Any], object_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        バウンディングボックスを計算
        
        Args:
            mask_data: 入力マスクDTO
            object_id: 特定のオブジェクトID（Noneの場合は全ID）
            
        Returns:
            バウンディングボックスDTOのリスト
        """
        ...