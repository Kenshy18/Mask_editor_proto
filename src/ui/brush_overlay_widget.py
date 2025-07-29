#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラシオーバーレイウィジェット

マスクオーバーレイウィジェットを拡張し、ブラシ描画機能を追加。
"""
import logging
from typing import Optional, Tuple
import numpy as np

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPixmap, QCursor, QMouseEvent, QPaintEvent
from PyQt6.QtWidgets import QWidget

from ui.video_with_mask_widget import VideoWithMaskWidget
from domain.dto.brush_dto import BrushConfigDTO, BrushStrokeDTO, BrushModeDTO
from domain.dto.mask_dto import MaskDTO
from domain.ports.secondary.brush_ports import IBrushEngine, IBrushPreview

logger = logging.getLogger(__name__)


class BrushOverlayWidget(VideoWithMaskWidget):
    """
    ブラシオーバーレイウィジェット
    
    マスクオーバーレイにブラシ描画機能を追加。
    """
    
    # シグナル
    stroke_completed = pyqtSignal(BrushStrokeDTO)  # ストローク完了時
    mask_updated = pyqtSignal(MaskDTO)  # マスク更新時
    
    def __init__(self, 
                 brush_engine: IBrushEngine,
                 brush_preview: IBrushPreview,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # ブラシエンジン
        self._brush_engine = brush_engine
        self._brush_preview = brush_preview
        
        # ブラシ状態
        # デフォルトではERASEモードを使用（new_id/target_idが不要）
        self._brush_config = BrushConfigDTO(mode=BrushModeDTO.ERASE)
        self._is_drawing = False
        self._current_stroke_preview: Optional[QPixmap] = None
        self._brush_cursor: Optional[QPixmap] = None
        
        # カーソル更新タイマー
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._update_cursor_display)
        self._cursor_timer.setInterval(50)  # 50ms
        
        # ブラシモードの有効/無効フラグ
        self._brush_enabled = False  # デフォルトで無効
        
        # デフォルトカーソルに設定
        self.unsetCursor()
        
    def set_brush_enabled(self, enabled: bool) -> None:
        """ブラシモードの有効/無効を設定"""
        self._brush_enabled = enabled
        if enabled:
            self._update_brush_cursor()
        else:
            self.unsetCursor()  # デフォルトカーソルに戻す
            self._is_drawing = False  # 描画中の場合は中断
    
    def set_brush_config(self, config: BrushConfigDTO) -> None:
        """ブラシ設定を更新"""
        self._brush_config = config
        self._brush_engine.set_brush_config(config)
        if self._brush_enabled:
            self._update_brush_cursor()
        
    def _update_brush_cursor(self) -> None:
        """ブラシカーソルを更新"""
        if not self._brush_preview or not self._brush_enabled:
            return
            
        # カーソル画像を生成
        cursor_array = self._brush_preview.generate_cursor(
            self._brush_config.size,
            self._brush_config.hardness
        )
        
        # QPixmapに変換
        height, width = cursor_array.shape[:2]
        bytes_per_line = 4 * width
        
        from PyQt6.QtGui import QImage
        qimage = QImage(
            cursor_array.data,
            width, height,
            bytes_per_line,
            QImage.Format.Format_RGBA8888
        )
        
        self._brush_cursor = QPixmap.fromImage(qimage)
        
        # カスタムカーソルを設定
        cursor = QCursor(self._brush_cursor, width // 2, height // 2)
        self.setCursor(cursor)
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """マウスプレスイベント"""
        if not self._brush_enabled:
            super().mousePressEvent(event)  # 親クラスに処理を委譲
            return
            
        if event.button() == Qt.MouseButton.LeftButton and self.current_mask_dto:
            # ストローク開始
            self._is_drawing = True
            pos = event.position().toPoint()
            
            # ビューポート座標をマスク座標に変換
            mask_pos = self._viewport_to_mask_coords(pos.x(), pos.y())
            if mask_pos:
                self._brush_engine.begin_stroke(
                    mask_pos[0], mask_pos[1],
                    pressure=1.0  # タブレット対応は後で実装
                )
                self._cursor_timer.start()
                
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """マウス移動イベント"""
        if not self._brush_enabled:
            super().mouseMoveEvent(event)
            return
            
        if self._is_drawing and self.current_mask_dto:
            pos = event.position().toPoint()
            
            # ビューポート座標をマスク座標に変換
            mask_pos = self._viewport_to_mask_coords(pos.x(), pos.y())
            if mask_pos:
                self._brush_engine.add_stroke_point(
                    mask_pos[0], mask_pos[1],
                    pressure=1.0
                )
                
                # プレビューを更新
                self._update_stroke_preview()
                
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """マウスリリースイベント"""
        if not self._brush_enabled:
            super().mouseReleaseEvent(event)
            return
            
        if event.button() == Qt.MouseButton.LeftButton and self._is_drawing:
            # ストローク終了
            self._is_drawing = False
            self._cursor_timer.stop()
            
            # ストロークを取得
            stroke = self._brush_engine.end_stroke()
            
            # マスクを更新
            if self.current_mask_dto and stroke:
                self._apply_stroke_to_mask(stroke)
                
            # プレビューをクリア
            self._current_stroke_preview = None
            self.update()
            
        super().mouseReleaseEvent(event)
        
    def paintEvent(self, event: QPaintEvent) -> None:
        """描画イベント"""
        # 親クラスの描画を実行
        super().paintEvent(event)
        
        # ストロークプレビューを描画
        if self._current_stroke_preview and self._is_drawing:
            painter = QPainter(self)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, self._current_stroke_preview)
            
    def _viewport_to_mask_coords(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        """
        ビューポート座標をマスク座標に変換
        
        Args:
            x, y: ビューポート座標
            
        Returns:
            マスク座標 (x, y) または None
        """
        if not self.current_mask_dto or not self.mask_overlay.frame_dto:
            return None
            
        # ビューポートサイズ
        widget_width = self.width()
        widget_height = self.height()
        
        if widget_width == 0 or widget_height == 0:
            return None
            
        # フレームサイズ
        frame_width = self.mask_overlay.frame_dto.width
        frame_height = self.mask_overlay.frame_dto.height
        
        # スケール計算
        scale_x = frame_width / widget_width
        scale_y = frame_height / widget_height
        
        # マスク座標に変換
        mask_x = int(x * scale_x)
        mask_y = int(y * scale_y)
        
        # 境界チェック
        if 0 <= mask_x < self.current_mask_dto.width and 0 <= mask_y < self.current_mask_dto.height:
            return (mask_x, mask_y)
            
        return None
        
    def _update_stroke_preview(self) -> None:
        """ストロークプレビューを更新"""
        if not self.current_mask_dto or not self._is_drawing:
            return
            
        # 現在のストロークを取得（まだ終了していない）
        # 暫定的にダミーストロークを作成
        from domain.dto.brush_dto import BrushPointDTO
        current_points = [BrushPointDTO(x=0, y=0)]  # 実際の実装では現在の点を取得
        
        stroke = BrushStrokeDTO(
            points=current_points,
            config=self._brush_config,
            frame_index=self.current_mask_dto.frame_index
        )
        
        # プレビュー画像を生成
        preview_array = self._brush_engine.preview_stroke(
            self.current_mask_dto.width,
            self.current_mask_dto.height,
            stroke
        )
        
        # ビューポートサイズにリサイズ
        if self.width() > 0 and self.height() > 0:
            import cv2
            resized = cv2.resize(
                preview_array,
                (self.width(), self.height()),
                interpolation=cv2.INTER_LINEAR
            )
            
            # QPixmapに変換
            height, width = resized.shape[:2]
            bytes_per_line = 4 * width
            
            from PyQt6.QtGui import QImage
            qimage = QImage(
                resized.data,
                width, height,
                bytes_per_line,
                QImage.Format.Format_RGBA8888
            )
            
            self._current_stroke_preview = QPixmap.fromImage(qimage)
            self.update()
            
    def _apply_stroke_to_mask(self, stroke: BrushStrokeDTO) -> None:
        """
        ストロークをマスクに適用
        
        Args:
            stroke: 適用するストローク
        """
        if not self.current_mask_dto:
            return
            
        # マスクデータを更新
        updated_data = self._brush_engine.apply_stroke(
            self.current_mask_dto.data,
            stroke
        )
        
        # 新しいマスクDTOを作成（frozen=Trueのため）
        from dataclasses import replace
        updated_mask = replace(
            self.current_mask_dto,
            data=updated_data
        )
        
        # マスクを設定
        self.set_mask(updated_mask)
        
        # シグナルを発行
        self.stroke_completed.emit(stroke)
        self.mask_updated.emit(updated_mask)
        
        logger.debug("Stroke applied to mask")
        
    def _update_cursor_display(self) -> None:
        """カーソル表示を更新（描画中のアニメーション等）"""
        # 将来的にはカーソルアニメーションを実装
        pass
        
    def set_brush_enabled(self, enabled: bool) -> None:
        """
        ブラシ機能の有効/無効を設定
        
        Args:
            enabled: 有効化フラグ
        """
        if enabled:
            self._update_brush_cursor()
        else:
            self.unsetCursor()
            
    def clear_preview(self) -> None:
        """プレビューをクリア"""
        self._current_stroke_preview = None
        self._is_drawing = False
        self._cursor_timer.stop()
        self.update()