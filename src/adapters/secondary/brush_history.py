#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラシ履歴管理アダプター

ブラシストロークの履歴管理とUndo/Redo機能を提供。
"""
import logging
from typing import List, Optional
from collections import deque

from domain.dto.brush_dto import BrushStrokeDTO, BrushConfigDTO
from domain.ports.secondary.brush_ports import IBrushHistory

logger = logging.getLogger(__name__)


class BrushHistoryAdapter:
    """ブラシ履歴管理アダプター実装"""
    
    def __init__(self, max_history: int = 100):
        """
        初期化
        
        Args:
            max_history: 履歴の最大保持数
        """
        self._max_history = max_history
        self._undo_stack: deque[BrushStrokeDTO] = deque(maxlen=max_history)
        self._redo_stack: deque[BrushStrokeDTO] = deque(maxlen=max_history)
        
    def add_stroke(self, stroke: BrushStrokeDTO) -> None:
        """
        ストロークを履歴に追加
        
        Args:
            stroke: ストローク情報
        """
        self._undo_stack.append(stroke)
        # 新しいストロークが追加されたらRedoスタックをクリア
        self._redo_stack.clear()
        
        logger.debug(f"Stroke added to history. Undo stack size: {len(self._undo_stack)}")
    
    def undo(self) -> Optional[BrushStrokeDTO]:
        """
        直前のストロークを取り消し
        
        Returns:
            取り消されたストローク（ない場合はNone）
        """
        if not self._undo_stack:
            logger.debug("No strokes to undo")
            return None
        
        stroke = self._undo_stack.pop()
        self._redo_stack.append(stroke)
        
        logger.debug(f"Stroke undone. Undo stack: {len(self._undo_stack)}, "
                    f"Redo stack: {len(self._redo_stack)}")
        
        return stroke
    
    def redo(self) -> Optional[BrushStrokeDTO]:
        """
        取り消したストロークをやり直し
        
        Returns:
            やり直されたストローク（ない場合はNone）
        """
        if not self._redo_stack:
            logger.debug("No strokes to redo")
            return None
        
        stroke = self._redo_stack.pop()
        self._undo_stack.append(stroke)
        
        logger.debug(f"Stroke redone. Undo stack: {len(self._undo_stack)}, "
                    f"Redo stack: {len(self._redo_stack)}")
        
        return stroke
    
    def clear(self) -> None:
        """履歴をクリア"""
        self._undo_stack.clear()
        self._redo_stack.clear()
        
        logger.debug("History cleared")
    
    def can_undo(self) -> bool:
        """Undo可能かチェック"""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Redo可能かチェック"""
        return len(self._redo_stack) > 0
    
    def get_history_info(self) -> dict:
        """
        履歴情報を取得
        
        Returns:
            履歴情報の辞書
        """
        return {
            "undo_count": len(self._undo_stack),
            "redo_count": len(self._redo_stack),
            "max_history": self._max_history,
            "total_strokes": len(self._undo_stack) + len(self._redo_stack)
        }
    
    def get_all_strokes(self) -> List[BrushStrokeDTO]:
        """
        すべてのストロークを取得（Undo履歴のみ）
        
        Returns:
            ストロークのリスト
        """
        return list(self._undo_stack)
    
    def set_max_history(self, max_history: int) -> None:
        """
        最大履歴数を設定
        
        Args:
            max_history: 新しい最大履歴数
        """
        self._max_history = max_history
        
        # 既存のスタックのサイズを調整
        if len(self._undo_stack) > max_history:
            # 古いものから削除
            new_stack = deque(
                list(self._undo_stack)[-max_history:],
                maxlen=max_history
            )
            self._undo_stack = new_stack
        else:
            # maxlenを更新
            new_stack = deque(self._undo_stack, maxlen=max_history)
            self._undo_stack = new_stack
        
        # Redoスタックも同様に調整
        if len(self._redo_stack) > max_history:
            new_stack = deque(
                list(self._redo_stack)[-max_history:],
                maxlen=max_history
            )
            self._redo_stack = new_stack
        else:
            new_stack = deque(self._redo_stack, maxlen=max_history)
            self._redo_stack = new_stack
        
        logger.info(f"Max history set to {max_history}")
    
    def compress_history(self) -> int:
        """
        履歴を圧縮（連続する同一設定のストロークを結合）
        
        Returns:
            圧縮されたストローク数
        """
        if len(self._undo_stack) < 2:
            return 0
        
        compressed_count = 0
        new_stack = deque(maxlen=self._max_history)
        
        current_group = []
        prev_config = None
        
        for stroke in self._undo_stack:
            # 設定が同じ場合はグループ化
            if prev_config and self._is_same_config(stroke.config, prev_config):
                current_group.append(stroke)
            else:
                # 前のグループを処理
                if current_group:
                    merged = self._merge_strokes(current_group)
                    if merged:
                        new_stack.append(merged)
                        if len(current_group) > 1:
                            compressed_count += len(current_group) - 1
                
                # 新しいグループを開始
                current_group = [stroke]
                prev_config = stroke.config
        
        # 最後のグループを処理
        if current_group:
            merged = self._merge_strokes(current_group)
            if merged:
                new_stack.append(merged)
                if len(current_group) > 1:
                    compressed_count += len(current_group) - 1
        
        self._undo_stack = new_stack
        logger.info(f"History compressed. {compressed_count} strokes merged")
        
        return compressed_count
    
    def _is_same_config(self, config1: BrushConfigDTO, config2: BrushConfigDTO) -> bool:
        """
        2つのブラシ設定が同じかチェック
        
        Args:
            config1: 設定1
            config2: 設定2
            
        Returns:
            同じ場合True
        """
        return (
            config1.mode == config2.mode and
            config1.size == config2.size and
            config1.hardness == config2.hardness and
            config1.opacity == config2.opacity and
            config1.shape == config2.shape and
            config1.target_id == config2.target_id and
            config1.new_id == config2.new_id
        )
    
    def _merge_strokes(self, strokes: List[BrushStrokeDTO]) -> Optional[BrushStrokeDTO]:
        """
        複数のストロークを結合
        
        Args:
            strokes: ストロークのリスト
            
        Returns:
            結合されたストローク
        """
        if not strokes:
            return None
        
        if len(strokes) == 1:
            return strokes[0]
        
        # すべてのポイントを結合
        all_points = []
        for stroke in strokes:
            all_points.extend(stroke.points)
        
        # 最初のストロークの設定を使用
        from domain.dto.brush_dto import BrushStrokeDTO
        return BrushStrokeDTO(
            points=all_points,
            config=strokes[0].config,
            frame_index=strokes[0].frame_index
        )