#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラシツールポート定義

ブラシツールの描画エンジンと関連機能のインターフェース。
"""
from typing import Protocol, Tuple, Optional, List, Dict, Any
import numpy as np
from enum import Enum

from domain.dto.brush_dto import BrushModeDTO, BrushStrokeDTO, BrushConfigDTO


class BrushMode(Enum):
    """ブラシモード"""
    ADD_NEW_ID = "add_new_id"      # 新規ID追加モード
    ADD_TO_EXISTING = "add_to_existing"  # 既存ID加筆モード
    ERASE = "erase"                # 消去モード


class IBrushEngine(Protocol):
    """ブラシエンジンインターフェース"""
    
    def set_brush_config(self, config: BrushConfigDTO) -> None:
        """
        ブラシ設定を更新
        
        Args:
            config: ブラシ設定
        """
        ...
    
    def begin_stroke(self, x: int, y: int, pressure: float = 1.0) -> None:
        """
        ストローク開始
        
        Args:
            x: X座標
            y: Y座標
            pressure: 筆圧（0.0-1.0）
        """
        ...
    
    def add_stroke_point(self, x: int, y: int, pressure: float = 1.0) -> None:
        """
        ストロークポイント追加
        
        Args:
            x: X座標
            y: Y座標
            pressure: 筆圧（0.0-1.0）
        """
        ...
    
    def end_stroke(self) -> BrushStrokeDTO:
        """
        ストローク終了
        
        Returns:
            完了したストローク情報
        """
        ...
    
    def apply_stroke(self, mask: np.ndarray, stroke: BrushStrokeDTO) -> np.ndarray:
        """
        マスクにストロークを適用
        
        Args:
            mask: 対象マスク（uint8）
            stroke: ストローク情報
            
        Returns:
            更新されたマスク
        """
        ...
    
    def preview_stroke(self, width: int, height: int, stroke: BrushStrokeDTO) -> np.ndarray:
        """
        ストロークのプレビュー生成
        
        Args:
            width: キャンバス幅
            height: キャンバス高さ
            stroke: ストローク情報
            
        Returns:
            プレビュー画像（RGBA）
        """
        ...


class IBrushPreview(Protocol):
    """ブラシプレビューインターフェース"""
    
    def generate_cursor(self, size: int, hardness: float) -> np.ndarray:
        """
        ブラシカーソル画像を生成
        
        Args:
            size: ブラシサイズ
            hardness: ブラシ硬さ（0.0-1.0）
            
        Returns:
            カーソル画像（RGBA）
        """
        ...
    
    def generate_preview(self, config: BrushConfigDTO) -> np.ndarray:
        """
        ブラシプレビュー画像を生成
        
        Args:
            config: ブラシ設定
            
        Returns:
            プレビュー画像（RGBA）
        """
        ...


class IBrushHistory(Protocol):
    """ブラシ履歴管理インターフェース"""
    
    def add_stroke(self, stroke: BrushStrokeDTO) -> None:
        """
        ストロークを履歴に追加
        
        Args:
            stroke: ストローク情報
        """
        ...
    
    def undo(self) -> Optional[BrushStrokeDTO]:
        """
        直前のストロークを取り消し
        
        Returns:
            取り消されたストローク（ない場合はNone）
        """
        ...
    
    def redo(self) -> Optional[BrushStrokeDTO]:
        """
        取り消したストロークをやり直し
        
        Returns:
            やり直されたストローク（ない場合はNone）
        """
        ...
    
    def clear(self) -> None:
        """履歴をクリア"""
        ...
    
    def can_undo(self) -> bool:
        """Undo可能かチェック"""
        ...
    
    def can_redo(self) -> bool:
        """Redo可能かチェック"""
        ...


class IBrushOptimizer(Protocol):
    """ブラシ描画最適化インターフェース"""
    
    def smooth_points(self, points: List[Tuple[int, int]], window_size: int = 5) -> List[Tuple[int, int]]:
        """
        ポイント列をスムージング
        
        Args:
            points: ポイントリスト
            window_size: スムージングウィンドウサイズ
            
        Returns:
            スムージングされたポイントリスト
        """
        ...
    
    def interpolate_points(self, p1: Tuple[int, int], p2: Tuple[int, int], 
                          density: float = 1.0) -> List[Tuple[int, int]]:
        """
        2点間を補間
        
        Args:
            p1: 開始点
            p2: 終了点
            density: 補間密度
            
        Returns:
            補間されたポイントリスト
        """
        ...
    
    def optimize_stroke(self, stroke: BrushStrokeDTO) -> BrushStrokeDTO:
        """
        ストロークを最適化
        
        Args:
            stroke: 元のストローク
            
        Returns:
            最適化されたストローク
        """
        ...