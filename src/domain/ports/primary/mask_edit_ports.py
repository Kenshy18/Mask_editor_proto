#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスク編集制御ポート定義

マスクの編集操作を制御するインターフェース。
"""
from typing import Protocol, Optional, List, Tuple
from domain.dto.mask_dto import MaskDTO


class IMaskEditController(Protocol):
    """マスク編集制御ポート（Primary）
    
    マスクの編集操作を制御。
    """
    
    def apply_morphology(self, frame_index: int, mask_id: int, 
                        operation: str, kernel_size: int) -> MaskDTO:
        """モルフォロジー操作を適用
        
        Args:
            frame_index: フレームインデックス
            mask_id: マスクID
            operation: 操作種別（dilate, erode, open, close）
            kernel_size: カーネルサイズ
            
        Returns:
            編集後のマスクDTO
        """
        ...
    
    def preview_morphology(self, mask: MaskDTO, operation: str, 
                          kernel_size: int) -> MaskDTO:
        """モルフォロジー操作をプレビュー
        
        Args:
            mask: 対象マスク
            operation: 操作種別
            kernel_size: カーネルサイズ
            
        Returns:
            プレビュー用マスクDTO
        """
        ...
    
    def apply_brush_stroke(self, frame_index: int, mask_id: int,
                          points: List[Tuple[int, int]], 
                          brush_size: int, mode: str) -> MaskDTO:
        """ブラシストロークを適用
        
        Args:
            frame_index: フレームインデックス
            mask_id: マスクID（新規の場合は-1）
            points: ストローク座標リスト
            brush_size: ブラシサイズ
            mode: add（追加）またはremove（削除）
            
        Returns:
            編集後のマスクDTO
        """
        ...
    
    def delete_mask(self, frame_index: int, mask_id: int) -> bool:
        """マスクを削除
        
        Args:
            frame_index: フレームインデックス
            mask_id: マスクID
            
        Returns:
            削除成功した場合True
        """
        ...
    
    def merge_masks(self, frame_index: int, 
                   source_ids: List[int], target_id: int) -> MaskDTO:
        """複数のマスクを統合
        
        Args:
            frame_index: フレームインデックス
            source_ids: 統合元のマスクIDリスト
            target_id: 統合先のマスクID
            
        Returns:
            統合後のマスクDTO
        """
        ...
    
    def split_mask(self, frame_index: int, mask_id: int,
                  split_line: List[Tuple[int, int]]) -> List[MaskDTO]:
        """マスクを分割
        
        Args:
            frame_index: フレームインデックス
            mask_id: 分割対象のマスクID
            split_line: 分割線の座標リスト
            
        Returns:
            分割後のマスクDTOリスト
        """
        ...
    
    def undo_edit(self) -> bool:
        """編集を元に戻す"""
        ...
    
    def redo_edit(self) -> bool:
        """編集をやり直す"""
        ...
    
    def can_undo(self) -> bool:
        """Undo可能かどうか"""
        ...
    
    def can_redo(self) -> bool:
        """Redo可能かどうか"""
        ...