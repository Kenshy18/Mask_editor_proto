#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスクオーバーレイウィジェット

ビデオフレーム上にマスクを重ねて表示するウィジェット。
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, List
import numpy as np

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QImage, QPixmap, QColor, QPen, QFont
from PyQt6.QtWidgets import QWidget

from domain.dto.frame_dto import FrameDTO
from domain.dto.mask_dto import MaskDTO, MaskOverlaySettingsDTO

logger = logging.getLogger(__name__)


class MaskOverlayWidget(QWidget):
    """マスクオーバーレイウィジェット
    
    ビデオフレーム上にマスクを半透明で重ねて表示。
    ID別の色分けとON/OFF切り替えをサポート。
    """
    
    # シグナル
    mask_clicked = pyqtSignal(int, QPoint)  # マスクID、クリック位置
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 表示データ
        self.frame_dto: Optional[FrameDTO] = None
        self.mask_dto: Optional[MaskDTO] = None
        self.overlay_settings = MaskOverlaySettingsDTO()
        
        # 表示用キャッシュ
        self._frame_pixmap: Optional[QPixmap] = None
        self._mask_pixmaps: Dict[int, QPixmap] = {}
        self._combined_overlay: Optional[QPixmap] = None
        
        # マウス操作用
        self.last_mouse_pos = QPoint()
        
        # UI設定
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
    def set_frame(self, frame_dto: FrameDTO) -> None:
        """フレームを設定"""
        self.frame_dto = frame_dto
        self._update_frame_pixmap()
        self._update_combined_overlay()
        self.update()
    
    def set_mask(self, mask_dto: Optional[MaskDTO]) -> None:
        """マスクを設定"""
        self.mask_dto = mask_dto
        self._update_mask_pixmaps()
        self._update_combined_overlay()
        self.update()
    
    def set_overlay_settings(self, settings: MaskOverlaySettingsDTO) -> None:
        """オーバーレイ設定を更新"""
        self.overlay_settings = settings
        self._update_combined_overlay()
        self.update()
    
    def toggle_mask_visibility(self, mask_id: int, visible: bool) -> None:
        """特定マスクの表示/非表示を切り替え"""
        self.overlay_settings.mask_visibility[mask_id] = visible
        self._update_combined_overlay()
        self.update()
    
    def set_mask_color(self, mask_id: int, color: str) -> None:
        """特定マスクの色を設定"""
        self.overlay_settings.mask_colors[mask_id] = color
        self._update_mask_pixmaps()
        self._update_combined_overlay()
        self.update()
    
    def _update_frame_pixmap(self) -> None:
        """フレームPixmapを更新"""
        if not self.frame_dto:
            self._frame_pixmap = None
            return
        
        # RGB24データからQImageを作成
        height, width = self.frame_dto.height, self.frame_dto.width
        image = QImage(
            self.frame_dto.data.tobytes(),
            width, height,
            width * 3,  # RGB24なので3バイト/ピクセル
            QImage.Format.Format_RGB888
        )
        
        self._frame_pixmap = QPixmap.fromImage(image)
    
    def _update_mask_pixmaps(self) -> None:
        """マスクPixmapを更新"""
        self._mask_pixmaps.clear()
        
        if not self.mask_dto:
            return
        
        # 各オブジェクトIDごとにPixmapを作成
        for obj_id in self.mask_dto.object_ids:
            if obj_id == 0:  # 背景は無視
                continue
            
            # バイナリマスクを取得
            binary_mask = self.mask_dto.get_mask_for_id(obj_id)
            
            # カラーマスクを作成
            color_str = self.overlay_settings.get_mask_color(obj_id)
            color = QColor(color_str)
            
            # RGBA画像を作成
            height, width = binary_mask.shape
            rgba_data = np.zeros((height, width, 4), dtype=np.uint8)
            
            # マスク領域に色を設定
            mask_indices = binary_mask > 0
            rgba_data[mask_indices, 0] = color.red()
            rgba_data[mask_indices, 1] = color.green()
            rgba_data[mask_indices, 2] = color.blue()
            rgba_data[mask_indices, 3] = 255  # 完全不透明（後で透明度を適用）
            
            # QImageを作成
            image = QImage(
                rgba_data.tobytes(),
                width, height,
                width * 4,
                QImage.Format.Format_RGBA8888
            )
            
            self._mask_pixmaps[obj_id] = QPixmap.fromImage(image)
    
    def _update_combined_overlay(self) -> None:
        """統合オーバーレイを更新"""
        if not self._frame_pixmap or not self.overlay_settings.enabled:
            self._combined_overlay = None
            return
        
        # フレームサイズでPixmapを作成
        width = self._frame_pixmap.width()
        height = self._frame_pixmap.height()
        
        combined = QPixmap(width, height)
        combined.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(combined)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # 透明度を設定
        painter.setOpacity(self.overlay_settings.opacity)
        
        # 表示されている各マスクを描画
        for obj_id, pixmap in self._mask_pixmaps.items():
            if self.overlay_settings.is_mask_visible(obj_id):
                painter.drawPixmap(0, 0, pixmap)
        
        painter.end()
        
        self._combined_overlay = combined
    
    def paintEvent(self, event) -> None:
        """描画イベント"""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # 背景を透明にする
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        
        if not self._frame_pixmap:
            return
        
        # 描画対象の矩形を計算（フレームサイズに基づく）
        target_rect = self._calculate_target_rect()
        
        # オーバーレイを描画
        if self._combined_overlay and self.overlay_settings.enabled:
            painter.drawPixmap(target_rect, self._combined_overlay)
        
        # 輪郭線を描画
        if self.overlay_settings.show_outlines and self.mask_dto:
            self._draw_outlines(painter, target_rect)
        
        # ラベルを描画
        if self.overlay_settings.show_labels and self.mask_dto:
            self._draw_labels(painter, target_rect)
    
    def _calculate_target_rect(self) -> QRect:
        """描画対象の矩形を計算（アスペクト比を維持）"""
        if not self._frame_pixmap:
            return QRect()
        
        widget_size = self.size()
        pixmap_size = self._frame_pixmap.size()
        
        # アスペクト比を維持してスケール
        scaled_size = pixmap_size.scaled(
            widget_size,
            Qt.AspectRatioMode.KeepAspectRatio
        )
        
        # 中央に配置
        x = (widget_size.width() - scaled_size.width()) // 2
        y = (widget_size.height() - scaled_size.height()) // 2
        
        return QRect(x, y, scaled_size.width(), scaled_size.height())
    
    def _draw_outlines(self, painter: QPainter, target_rect: QRect) -> None:
        """マスクの輪郭線を描画"""
        if not self.mask_dto:
            return
        
        # スケール係数を計算
        scale_x = target_rect.width() / self.mask_dto.width
        scale_y = target_rect.height() / self.mask_dto.height
        
        for obj_id in self.mask_dto.object_ids:
            if not self.overlay_settings.is_mask_visible(obj_id):
                continue
            
            # 輪郭線の色を設定
            color = QColor(self.overlay_settings.get_mask_color(obj_id))
            pen = QPen(color, self.overlay_settings.outline_width)
            painter.setPen(pen)
            
            # 輪郭を検出して描画（簡易実装）
            # 実際の実装では、OpenCVのfindContoursを使用する
            binary_mask = self.mask_dto.get_mask_for_id(obj_id)
            
            # エッジ検出（簡易版）
            # scipyの代わりにOpenCVを使用
            import cv2
            edges = cv2.Canny(binary_mask, 50, 150) > 0
            
            # エッジ点を描画
            y_indices, x_indices = np.where(edges)
            for y, x in zip(y_indices[::10], x_indices[::10]):  # 間引いて描画
                px = int(target_rect.x() + x * scale_x)
                py = int(target_rect.y() + y * scale_y)
                painter.drawPoint(px, py)
    
    def _draw_labels(self, painter: QPainter, target_rect: QRect) -> None:
        """マスクのラベルを描画"""
        if not self.mask_dto:
            return
        
        # フォント設定 - アプリケーションのデフォルトフォントを使用（日本語対応）
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        
        # スケール係数を計算
        scale_x = target_rect.width() / self.mask_dto.width
        scale_y = target_rect.height() / self.mask_dto.height
        
        for obj_id in self.mask_dto.object_ids:
            if not self.overlay_settings.is_mask_visible(obj_id):
                continue
            
            # マスクの重心を計算
            binary_mask = self.mask_dto.get_mask_for_id(obj_id)
            y_indices, x_indices = np.where(binary_mask > 0)
            
            if len(y_indices) == 0:
                continue
            
            center_y = int(np.mean(y_indices))
            center_x = int(np.mean(x_indices))
            
            # 画面座標に変換
            px = int(target_rect.x() + center_x * scale_x)
            py = int(target_rect.y() + center_y * scale_y)
            
            # ラベルテキスト
            class_name = self.mask_dto.classes.get(obj_id, f"ID{obj_id}")
            confidence = self.mask_dto.confidences.get(obj_id, 0.0)
            label = f"{class_name} ({confidence:.2f})"
            
            # 背景付きでテキストを描画
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(px - 1, py - 1, label)
            painter.drawText(px + 1, py - 1, label)
            painter.drawText(px - 1, py + 1, label)
            painter.drawText(px + 1, py + 1, label)
            
            color = QColor(self.overlay_settings.get_mask_color(obj_id))
            painter.setPen(QPen(color))
            painter.drawText(px, py, label)
    
    def mousePressEvent(self, event) -> None:
        """マウスクリックイベント"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.pos()
            
            # クリック位置のマスクIDを取得
            mask_id = self._get_mask_id_at_position(event.pos())
            if mask_id > 0:
                self.mask_clicked.emit(mask_id, event.pos())
    
    def _get_mask_id_at_position(self, pos: QPoint) -> int:
        """指定位置のマスクIDを取得"""
        if not self.mask_dto or not self._frame_pixmap:
            return 0
        
        target_rect = self._calculate_target_rect()
        
        # ウィジェット座標をマスク座標に変換
        rel_x = pos.x() - target_rect.x()
        rel_y = pos.y() - target_rect.y()
        
        if rel_x < 0 or rel_y < 0:
            return 0
        
        mask_x = int(rel_x * self.mask_dto.width / target_rect.width())
        mask_y = int(rel_y * self.mask_dto.height / target_rect.height())
        
        if (0 <= mask_x < self.mask_dto.width and 
            0 <= mask_y < self.mask_dto.height):
            return int(self.mask_dto.data[mask_y, mask_x])
        
        return 0
    
    def get_visible_mask_ids(self) -> List[int]:
        """表示中のマスクIDリストを取得"""
        if not self.mask_dto:
            return []
        
        return [
            obj_id for obj_id in self.mask_dto.object_ids
            if self.overlay_settings.is_mask_visible(obj_id)
        ]