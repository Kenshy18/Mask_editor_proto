#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ID管理ポート定義

マスクのID管理、削除、閾値調整に関するインターフェース。
"""
from typing import Protocol, List, Dict, Optional, Set, Tuple
import numpy as np


class IIDManager(Protocol):
    """ID管理インターフェース
    
    マスクのID削除、マージ、閾値管理を行う。
    """
    
    def delete_ids(self, mask_data: Dict[str, any], target_ids: List[int]) -> Dict[str, any]:
        """
        指定IDを削除
        
        Args:
            mask_data: マスクDTO
            target_ids: 削除対象のIDリスト
            
        Returns:
            処理後のマスクDTO
        """
        ...
    
    def delete_range(self, mask_data: Dict[str, any], id_range: Tuple[int, int]) -> Dict[str, any]:
        """
        ID範囲指定で削除
        
        Args:
            mask_data: マスクDTO
            id_range: 削除対象の範囲 (start, end) ※endは含む
            
        Returns:
            処理後のマスクDTO
        """
        ...
    
    def delete_all(self, mask_data: Dict[str, any]) -> Dict[str, any]:
        """
        全IDを削除（マスクをクリア）
        
        Args:
            mask_data: マスクDTO
            
        Returns:
            クリア後のマスクDTO
        """
        ...
    
    def merge_ids(self, mask_data: Dict[str, any], source_ids: List[int], target_id: int) -> Dict[str, any]:
        """
        複数のIDを単一IDにマージ
        
        Args:
            mask_data: マスクDTO
            source_ids: マージ元のIDリスト
            target_id: マージ先のID
            
        Returns:
            マージ後のマスクDTO
        """
        ...
    
    def renumber_ids(self, mask_data: Dict[str, any]) -> Dict[str, any]:
        """
        IDを連番に振り直し
        
        Args:
            mask_data: マスクDTO
            
        Returns:
            再番号付け後のマスクDTO
        """
        ...
    
    def get_id_statistics(self, mask_data: Dict[str, any]) -> Dict[int, Dict[str, any]]:
        """
        ID別の統計情報を取得
        
        Args:
            mask_data: マスクDTO
            
        Returns:
            ID -> {pixel_count, bbox, center} のマッピング
        """
        ...


class IThresholdManager(Protocol):
    """閾値管理インターフェース
    
    検出閾値とIDマージ閾値の管理を行う。
    """
    
    def get_detection_threshold(self) -> float:
        """
        現在の検出閾値を取得
        
        Returns:
            検出閾値（0.0-1.0）
        """
        ...
    
    def set_detection_threshold(self, threshold: float) -> None:
        """
        検出閾値を設定
        
        Args:
            threshold: 検出閾値（0.0-1.0）
        """
        ...
    
    def get_merge_threshold(self) -> float:
        """
        現在のIDマージ閾値を取得
        
        Returns:
            マージ閾値（0.0-1.0）
        """
        ...
    
    def set_merge_threshold(self, threshold: float) -> None:
        """
        IDマージ閾値を設定
        
        Args:
            threshold: マージ閾値（0.0-1.0）
        """
        ...
    
    def apply_detection_threshold(self, mask_data: Dict[str, any], 
                                confidences: Dict[int, float], 
                                threshold: float) -> Dict[str, any]:
        """
        検出閾値を適用してマスクをフィルタリング
        
        Args:
            mask_data: マスクDTO
            confidences: ID -> 信頼度のマッピング
            threshold: 適用する閾値
            
        Returns:
            フィルタリング後のマスクDTO
        """
        ...
    
    def suggest_merge_candidates(self, mask_data: Dict[str, any], 
                                threshold: float) -> List[Tuple[int, int, float]]:
        """
        マージ候補を提案
        
        Args:
            mask_data: マスクDTO
            threshold: マージ閾値
            
        Returns:
            [(id1, id2, similarity_score), ...] のリスト
        """
        ...
    
    def get_threshold_history(self) -> List[Dict[str, any]]:
        """
        閾値変更履歴を取得
        
        Returns:
            [{timestamp, type, old_value, new_value}, ...] のリスト
        """
        ...


class IIDPreview(Protocol):
    """ID操作プレビューインターフェース
    
    ID操作のプレビュー生成を行う。
    """
    
    def preview_delete(self, mask_data: Dict[str, any], target_ids: List[int]) -> np.ndarray:
        """
        ID削除のプレビュー画像を生成
        
        Args:
            mask_data: マスクDTO
            target_ids: 削除対象のIDリスト
            
        Returns:
            プレビュー画像（削除部分をハイライト）
        """
        ...
    
    def preview_merge(self, mask_data: Dict[str, any], 
                     source_ids: List[int], 
                     target_id: int) -> np.ndarray:
        """
        IDマージのプレビュー画像を生成
        
        Args:
            mask_data: マスクDTO
            source_ids: マージ元のIDリスト
            target_id: マージ先のID
            
        Returns:
            プレビュー画像（マージ結果を表示）
        """
        ...
    
    def preview_threshold(self, mask_data: Dict[str, any], 
                         confidences: Dict[int, float], 
                         threshold: float) -> np.ndarray:
        """
        閾値適用のプレビュー画像を生成
        
        Args:
            mask_data: マスクDTO
            confidences: ID -> 信頼度のマッピング
            threshold: 適用する閾値
            
        Returns:
            プレビュー画像（削除される部分をハイライト）
        """
        ...
    
    def generate_diff_visualization(self, before_mask: Dict[str, any], 
                                   after_mask: Dict[str, any]) -> np.ndarray:
        """
        変更前後の差分を可視化
        
        Args:
            before_mask: 変更前のマスクDTO
            after_mask: 変更後のマスクDTO
            
        Returns:
            差分可視化画像
        """
        ...