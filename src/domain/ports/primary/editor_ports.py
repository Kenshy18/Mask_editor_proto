#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスクエディタポート定義

マスク編集機能へのアクセスインターフェース。
"""
from typing import Protocol, Optional, Dict, Any, List, Tuple
from enum import Enum


class EditMode(Enum):
    """編集モード"""
    SELECT = "select"
    BRUSH = "brush"
    ERASER = "eraser"
    MORPHOLOGY = "morphology"


class BrushMode(Enum):
    """ブラシモード"""
    NEW_ID = "new_id"
    ADD_TO_ID = "add_to_id"


class MorphologyOperation(Enum):
    """モルフォロジー操作"""
    DILATE = "dilate"
    ERODE = "erode"
    OPEN = "open"
    CLOSE = "close"


class IMaskEditor(Protocol):
    """マスクエディタインターフェース"""
    
    # 編集モード
    def set_edit_mode(self, mode: EditMode) -> None:
        """編集モードを設定"""
        ...
    
    def get_edit_mode(self) -> EditMode:
        """現在の編集モードを取得"""
        ...
    
    # ブラシツール
    def set_brush_mode(self, mode: BrushMode) -> None:
        """ブラシモードを設定"""
        ...
    
    def set_brush_size(self, size: int) -> None:
        """ブラシサイズを設定"""
        ...
    
    def set_brush_hardness(self, hardness: float) -> None:
        """ブラシの硬さを設定（0.0-1.0）"""
        ...
    
    def set_target_id(self, object_id: int) -> None:
        """操作対象のオブジェクトIDを設定"""
        ...
    
    def draw_mask(
        self,
        frame_index: int,
        points: List[Tuple[int, int]],
        pressure: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        マスクを描画
        
        Args:
            frame_index: フレームインデックス
            points: 描画ポイントのリスト
            pressure: 筆圧のリスト（タブレット使用時）
            
        Returns:
            更新後のマスクDTO
        """
        ...
    
    def erase_mask(
        self,
        frame_index: int,
        points: List[Tuple[int, int]]
    ) -> Dict[str, Any]:
        """
        マスクを消去
        
        Args:
            frame_index: フレームインデックス
            points: 消去ポイントのリスト
            
        Returns:
            更新後のマスクDTO
        """
        ...
    
    # モルフォロジー操作
    def apply_morphology(
        self,
        frame_index: int,
        operation: MorphologyOperation,
        kernel_size: int,
        object_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        モルフォロジー操作を適用
        
        Args:
            frame_index: フレームインデックス
            operation: 操作タイプ
            kernel_size: カーネルサイズ
            object_ids: 対象オブジェクトID（Noneの場合は全体）
            
        Returns:
            処理後のマスクDTO
        """
        ...
    
    # ID管理
    def create_new_id(self) -> int:
        """新規オブジェクトIDを生成"""
        ...
    
    def delete_id(
        self,
        object_id: int,
        frame_range: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        オブジェクトIDを削除
        
        Args:
            object_id: 削除するID
            frame_range: フレーム範囲（Noneの場合は全フレーム）
            
        Returns:
            成功した場合True
        """
        ...
    
    def merge_ids(
        self,
        source_ids: List[int],
        target_id: int,
        frame_range: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        複数IDを統合
        
        Args:
            source_ids: 統合元IDリスト
            target_id: 統合先ID
            frame_range: フレーム範囲
            
        Returns:
            成功した場合True
        """
        ...
    
    def split_id(
        self,
        object_id: int,
        frame_index: int,
        split_mask: Dict[str, Any]
    ) -> List[int]:
        """
        IDを分割
        
        Args:
            object_id: 分割対象ID
            frame_index: フレームインデックス
            split_mask: 分割用マスク
            
        Returns:
            新規作成されたIDのリスト
        """
        ...
    
    # トラッキング
    def interpolate_masks(
        self,
        start_frame: int,
        end_frame: int,
        method: str = "linear",
        object_ids: Optional[List[int]] = None
    ) -> bool:
        """
        マスクを補間
        
        Args:
            start_frame: 開始フレーム
            end_frame: 終了フレーム
            method: 補間方法（"linear", "optical_flow"）
            object_ids: 対象オブジェクトID
            
        Returns:
            成功した場合True
        """
        ...
    
    def propagate_mask(
        self,
        source_frame: int,
        target_frames: List[int],
        object_ids: Optional[List[int]] = None
    ) -> bool:
        """
        マスクを他フレームに伝播
        
        Args:
            source_frame: コピー元フレーム
            target_frames: コピー先フレームリスト
            object_ids: 対象オブジェクトID
            
        Returns:
            成功した場合True
        """
        ...
    
    # 選択
    def select_objects(self, object_ids: List[int]) -> None:
        """オブジェクトを選択"""
        ...
    
    def clear_selection(self) -> None:
        """選択をクリア"""
        ...
    
    def get_selected_objects(self) -> List[int]:
        """選択中のオブジェクトIDリストを取得"""
        ...