#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラシプレビューアダプター

ブラシカーソルとプレビュー画像の生成を担当。
"""
import numpy as np
import cv2

from domain.dto.brush_dto import BrushConfigDTO, BrushShapeDTO
from domain.ports.secondary.brush_ports import IBrushPreview


class BrushPreviewAdapter:
    """ブラシプレビューアダプター実装"""
    
    def generate_cursor(self, size: int, hardness: float) -> np.ndarray:
        """
        ブラシカーソル画像を生成
        
        Args:
            size: ブラシサイズ
            hardness: ブラシ硬さ（0.0-1.0）
            
        Returns:
            カーソル画像（RGBA）
        """
        # カーソルサイズ（ブラシサイズ + マージン）
        cursor_size = size + 4
        cursor = np.zeros((cursor_size, cursor_size, 4), dtype=np.uint8)
        
        center = cursor_size // 2
        radius = size // 2
        
        # 外側の円（白い輪郭）
        cv2.circle(cursor, (center, center), radius + 1, 
                  (255, 255, 255, 200), 1, cv2.LINE_AA)
        
        # 内側の円（黒い輪郭）
        cv2.circle(cursor, (center, center), radius, 
                  (0, 0, 0, 200), 1, cv2.LINE_AA)
        
        # ハードネスを視覚化（中心部分）
        if hardness < 1.0:
            hard_radius = int(radius * hardness)
            if hard_radius > 1:
                # ハードエッジ部分を点線で表示
                for angle in range(0, 360, 10):
                    x = int(center + hard_radius * np.cos(np.radians(angle)))
                    y = int(center + hard_radius * np.sin(np.radians(angle)))
                    cv2.circle(cursor, (x, y), 1, (128, 128, 128, 128), -1)
        
        # 中心点
        cv2.circle(cursor, (center, center), 1, (255, 255, 255, 255), -1)
        
        return cursor
    
    def generate_preview(self, config: BrushConfigDTO) -> np.ndarray:
        """
        ブラシプレビュー画像を生成
        
        Args:
            config: ブラシ設定
            
        Returns:
            プレビュー画像（RGBA）
        """
        # プレビューサイズ
        preview_size = 64
        preview = np.zeros((preview_size, preview_size, 4), dtype=np.uint8)
        
        # 背景（チェッカーボード）
        checker_size = 8
        for y in range(0, preview_size, checker_size):
            for x in range(0, preview_size, checker_size):
                if (x // checker_size + y // checker_size) % 2 == 0:
                    preview[y:y+checker_size, x:x+checker_size, :3] = 200
                else:
                    preview[y:y+checker_size, x:x+checker_size, :3] = 240
        preview[:, :, 3] = 255
        
        # ブラシストロークを描画
        center = preview_size // 2
        brush_size = min(config.size, preview_size - 10)
        
        if config.shape == BrushShapeDTO.CIRCLE:
            # 円形ブラシ
            if config.hardness >= 1.0:
                # ハードブラシ
                cv2.circle(preview, (center, center), brush_size // 2,
                          (50, 50, 50, int(255 * config.opacity)), -1, cv2.LINE_AA)
            else:
                # ソフトブラシ
                self._draw_soft_preview(preview, center, center, brush_size,
                                      config.hardness, config.opacity)
        
        elif config.shape == BrushShapeDTO.SQUARE:
            # 四角形ブラシ
            half_size = brush_size // 2
            color = (50, 50, 50, int(255 * config.opacity))
            cv2.rectangle(preview,
                        (center - half_size, center - half_size),
                        (center + half_size, center + half_size),
                        color, -1)
        
        return preview
    
    def _draw_soft_preview(self, image: np.ndarray, cx: int, cy: int,
                          size: int, hardness: float, opacity: float) -> None:
        """
        ソフトブラシのプレビューを描画
        
        Args:
            image: 描画対象画像（RGBA）
            cx, cy: 中心座標
            size: 直径
            hardness: 硬さ
            opacity: 不透明度
        """
        radius = size // 2
        if radius < 1:
            return
        
        # アルファマスクを作成
        mask_size = size + 2
        mask = np.zeros((mask_size, mask_size), dtype=np.float32)
        mask_center = mask_size // 2
        
        # メッシュグリッドを作成
        y, x = np.ogrid[0:mask_size, 0:mask_size]
        dist = np.sqrt((x - mask_center)**2 + (y - mask_center)**2)
        
        # ソフトエッジのマスクを作成
        hard_radius = radius * hardness
        
        mask[dist <= hard_radius] = 1.0
        
        # ソフトエッジ部分
        soft_area = (dist > hard_radius) & (dist <= radius)
        if radius - hard_radius > 0:
            mask[soft_area] = 1.0 - (dist[soft_area] - hard_radius) / (radius - hard_radius)
        
        # 画像に適用
        x1 = max(0, cx - mask_center)
        y1 = max(0, cy - mask_center)
        x2 = min(image.shape[1], cx - mask_center + mask_size)
        y2 = min(image.shape[0], cy - mask_center + mask_size)
        
        if x2 > x1 and y2 > y1:
            # マスクの対応部分を切り出し
            mask_x1 = x1 - (cx - mask_center)
            mask_y1 = y1 - (cy - mask_center)
            mask_x2 = mask_x1 + (x2 - x1)
            mask_y2 = mask_y1 + (y2 - y1)
            
            mask_roi = mask[mask_y1:mask_y2, mask_x1:mask_x2]
            
            # 色を適用
            color = np.array([50, 50, 50, 255 * opacity], dtype=np.float32)
            for c in range(3):
                image[y1:y2, x1:x2, c] = (
                    image[y1:y2, x1:x2, c] * (1 - mask_roi * opacity) +
                    color[c] * mask_roi * opacity
                )
            
            # アルファチャンネル
            image[y1:y2, x1:x2, 3] = np.clip(
                image[y1:y2, x1:x2, 3] + mask_roi * color[3],
                0, 255
            ).astype(np.uint8)