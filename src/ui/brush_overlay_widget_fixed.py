#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正版ブラシオーバーレイウィジェット

ブラシモードの有効/無効を切り替え可能にし、
デフォルトでは無効にする。
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


class BrushOverlayWidgetFixed(VideoWithMaskWidget):
    """
    修正版ブラシオーバーレイウィジェット
    
    デフォルトでブラシモードは無効。
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
        self._brush_config = BrushConfigDTO(mode=BrushModeDTO.ERASE)
        self._is_drawing = False
        self._current_stroke_preview: Optional[QPixmap] = None
        self._brush_cursor: Optional[QPixmap] = None
        
        # ブラシモードの有効/無効
        self._brush_enabled = False  # デフォルトで無効
        
        # カーソル更新タイマー
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._update_cursor_display)
        self._cursor_timer.setInterval(50)  # 50ms
        
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
    
    def is_brush_enabled(self) -> bool:
        """ブラシモードが有効かどうか"""
        return self._brush_enabled
    
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
            
            # ストローク開始点を記録
            stroke_point = self._widget_to_image_coords(pos)
            if stroke_point:
                self._brush_engine.start_stroke(*stroke_point)
                self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """マウス移動イベント"""
        if not self._brush_enabled:
            super().mouseMoveEvent(event)
            return
            
        if self._is_drawing and self.current_mask_dto:
            pos = event.position().toPoint()
            stroke_point = self._widget_to_image_coords(pos)
            if stroke_point:
                self._brush_engine.add_stroke_point(*stroke_point)
                self._update_stroke_preview()
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """マウスリリースイベント"""
        if not self._brush_enabled:
            super().mouseReleaseEvent(event)
            return
            
        if event.button() == Qt.MouseButton.LeftButton and self._is_drawing:
            self._is_drawing = False
            
            # ストロークを終了してマスクに適用
            stroke = self._brush_engine.end_stroke()
            if stroke and self.current_mask_dto:
                # マスクを更新
                updated_mask = self._apply_stroke_to_mask(stroke)
                if updated_mask:
                    self.current_mask_dto = updated_mask
                    self.mask_updated.emit(updated_mask)
                    self.stroke_completed.emit(stroke)
            
            self._current_stroke_preview = None
            self.update()
    
    def enterEvent(self, event) -> None:
        """ウィジェットに入った時"""
        super().enterEvent(event)
        if self._brush_enabled and not self._cursor_timer.isActive():
            self._cursor_timer.start()
    
    def leaveEvent(self, event) -> None:
        """ウィジェットから出た時"""
        super().leaveEvent(event)
        if self._cursor_timer.isActive():
            self._cursor_timer.stop()
    
    def _widget_to_image_coords(self, pos: QPoint) -> Optional[Tuple[int, int]]:
        """ウィジェット座標を画像座標に変換"""
        if not self.current_frame or not self.current_mask_dto:
            return None
            
        # 画像の表示領域を計算
        widget_size = self.size()
        image_height, image_width = self.current_frame.shape[:2]
        
        # アスペクト比を保持したスケーリング
        scale = min(widget_size.width() / image_width,
                   widget_size.height() / image_height)
        
        display_width = int(image_width * scale)
        display_height = int(image_height * scale)
        
        # センタリングのオフセット
        offset_x = (widget_size.width() - display_width) // 2
        offset_y = (widget_size.height() - display_height) // 2
        
        # ウィジェット座標から画像座標へ
        x = int((pos.x() - offset_x) / scale)
        y = int((pos.y() - offset_y) / scale)
        
        # 画像範囲内かチェック
        if 0 <= x < image_width and 0 <= y < image_height:
            return (x, y)
        return None
    
    def _update_stroke_preview(self) -> None:
        """ストロークプレビューを更新"""
        if not self.current_mask_dto:
            return
            
        # 現在のストロークをプレビュー
        preview_array = self._brush_engine.preview_current_stroke(
            self.current_mask_dto.data.shape
        )
        
        if preview_array is not None:
            # プレビューをQPixmapに変換
            height, width = preview_array.shape[:2]
            bytes_per_line = 4 * width
            
            from PyQt6.QtGui import QImage
            qimage = QImage(
                preview_array.data,
                width, height,
                bytes_per_line,
                QImage.Format.Format_RGBA8888
            )
            
            self._current_stroke_preview = QPixmap.fromImage(qimage)
            self.update()
    
    def _apply_stroke_to_mask(self, stroke: BrushStrokeDTO) -> Optional[MaskDTO]:
        """ストロークをマスクに適用"""
        if not self.current_mask_dto:
            return None
            
        # ブラシエンジンでマスクを更新
        updated_mask_data = self._brush_engine.apply_stroke_to_mask(
            self.current_mask_dto.data,
            stroke
        )
        
        if updated_mask_data is not None:
            # 新しいMaskDTOを作成
            from dataclasses import replace
            return replace(
                self.current_mask_dto,
                data=updated_mask_data
            )
        return None
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """描画イベント"""
        super().paintEvent(event)
        
        # ストロークプレビューを描画
        if self._current_stroke_preview and self._brush_enabled:
            painter = QPainter(self)
            
            # 画像の表示領域を計算（_widget_to_image_coordsと同じロジック）
            if self.current_frame is not None:
                widget_size = self.size()
                image_height, image_width = self.current_frame.shape[:2]
                
                scale = min(widget_size.width() / image_width,
                           widget_size.height() / image_height)
                
                display_width = int(image_width * scale)
                display_height = int(image_height * scale)
                
                offset_x = (widget_size.width() - display_width) // 2
                offset_y = (widget_size.height() - display_height) // 2
                
                # プレビューを描画
                scaled_preview = self._current_stroke_preview.scaled(
                    display_width, display_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                painter.drawPixmap(offset_x, offset_y, scaled_preview)
    
    def _update_cursor_display(self) -> None:
        """カーソル表示を更新（必要に応じて）"""
        pass  # 現在は特に処理なし