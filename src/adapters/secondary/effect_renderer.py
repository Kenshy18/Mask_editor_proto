#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクトレンダラー実装

エフェクトのレンダリングとブレンディング機能を提供。
"""
from typing import Dict, Any
import numpy as np
import cv2
import logging

from domain.dto.effect_dto import EffectType
from domain.ports.secondary.effect_ports import IEffectRenderer

logger = logging.getLogger(__name__)


class EffectRenderer:
    """エフェクトレンダラー実装"""
    
    def render_region(
        self,
        frame: np.ndarray,
        region: np.ndarray,
        effect_type: EffectType,
        parameters: Dict[str, Any],
        quality: str = "high"
    ) -> np.ndarray:
        """
        指定領域にエフェクトをレンダリング
        
        Args:
            frame: 入力フレーム
            region: エフェクト適用領域（マスク）
            effect_type: エフェクトタイプ
            parameters: エフェクトパラメータ
            quality: レンダリング品質（low/medium/high）
            
        Returns:
            レンダリング済み領域
        """
        # 領域のバウンディングボックスを取得
        region_indices = np.where(region > 0)
        if len(region_indices[0]) == 0:
            return frame.copy()
        
        y_min, y_max = region_indices[0].min(), region_indices[0].max()
        x_min, x_max = region_indices[1].min(), region_indices[1].max()
        
        # 領域を抽出
        roi = frame[y_min:y_max+1, x_min:x_max+1].copy()
        roi_mask = region[y_min:y_max+1, x_min:x_max+1]
        
        # エフェクトタイプごとのレンダリング
        if effect_type == EffectType.MOSAIC:
            rendered_roi = self._render_mosaic(roi, parameters, quality)
        elif effect_type == EffectType.BLUR:
            rendered_roi = self._render_blur(roi, parameters, quality)
        elif effect_type == EffectType.PIXELATE:
            rendered_roi = self._render_pixelate(roi, parameters, quality)
        else:
            logger.warning(f"Unknown effect type: {effect_type}")
            rendered_roi = roi
        
        # マスクを適用
        mask_3ch = cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2RGB)
        mask_norm = mask_3ch.astype(np.float32) / 255.0
        
        # ブレンド
        blended = (rendered_roi * mask_norm + roi * (1 - mask_norm)).astype(np.uint8)
        
        # 結果フレームを作成
        result = frame.copy()
        result[y_min:y_max+1, x_min:x_max+1] = blended
        
        return result
    
    def blend_regions(
        self,
        original: np.ndarray,
        effected: np.ndarray,
        mask: np.ndarray,
        blend_mode: str = "normal",
        opacity: float = 1.0
    ) -> np.ndarray:
        """
        エフェクト領域をブレンド
        
        Args:
            original: 元フレーム
            effected: エフェクト適用済み領域
            mask: ブレンドマスク
            blend_mode: ブレンドモード
            opacity: 不透明度（0.0-1.0）
            
        Returns:
            ブレンド結果
        """
        # マスクを正規化
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        mask_norm = mask_3ch.astype(np.float32) / 255.0
        
        # 不透明度を適用
        mask_norm *= opacity
        
        # ブレンドモードごとの処理
        if blend_mode == "normal":
            # 通常ブレンド（アルファブレンド）
            result = (effected * mask_norm + original * (1 - mask_norm))
            
        elif blend_mode == "multiply":
            # 乗算ブレンド
            blended = (original.astype(np.float32) / 255.0) * (effected.astype(np.float32) / 255.0)
            blended = (blended * 255).astype(np.float32)
            result = (blended * mask_norm + original * (1 - mask_norm))
            
        elif blend_mode == "screen":
            # スクリーンブレンド
            inv_original = 255 - original.astype(np.float32)
            inv_effected = 255 - effected.astype(np.float32)
            blended = 255 - (inv_original * inv_effected / 255.0)
            result = (blended * mask_norm + original * (1 - mask_norm))
            
        elif blend_mode == "overlay":
            # オーバーレイブレンド
            result = np.zeros_like(original, dtype=np.float32)
            
            # 暗い部分は乗算、明るい部分はスクリーン
            dark_mask = original < 128
            bright_mask = ~dark_mask
            
            # 暗い部分
            result[dark_mask] = (2 * original[dark_mask] * effected[dark_mask] / 255.0)
            
            # 明るい部分
            result[bright_mask] = 255 - (2 * (255 - original[bright_mask]) * (255 - effected[bright_mask]) / 255.0)
            
            # マスクを適用
            result = (result * mask_norm + original * (1 - mask_norm))
            
        else:
            # 未知のブレンドモード
            logger.warning(f"Unknown blend mode: {blend_mode}, using normal")
            result = (effected * mask_norm + original * (1 - mask_norm))
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def apply_feather(
        self,
        mask: np.ndarray,
        feather_size: int
    ) -> np.ndarray:
        """
        マスクエッジをフェザリング
        
        Args:
            mask: 入力マスク
            feather_size: フェザーサイズ（ピクセル）
            
        Returns:
            フェザリング済みマスク
        """
        if feather_size <= 0:
            return mask
        
        # ガウシアンブラーでフェザリング
        kernel_size = feather_size * 2 + 1
        feathered = cv2.GaussianBlur(
            mask.astype(np.float32),
            (kernel_size, kernel_size),
            feather_size / 2
        )
        
        # エッジ部分のみフェザリング（内部は元のまま）
        # 収縮させたマスクを作成
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, 
            (feather_size * 2 + 1, feather_size * 2 + 1)
        )
        inner_mask = cv2.erode(mask, kernel, iterations=1)
        
        # 内部は元の値、エッジ部分はフェザリング値を使用
        result = np.where(inner_mask > 0, mask, feathered)
        
        return result.astype(np.uint8)
    
    def _render_mosaic(
        self, 
        image: np.ndarray,
        parameters: Dict[str, Any],
        quality: str
    ) -> np.ndarray:
        """モザイクレンダリング"""
        block_size = parameters.get("block_size", 16)
        
        # 品質に応じてブロックサイズを調整
        if quality == "low":
            block_size = max(block_size, 24)
        elif quality == "medium":
            block_size = max(block_size, 16)
        # high品質はそのまま
        
        h, w = image.shape[:2]
        result = image.copy()
        
        # ブロックごとに処理
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                y_end = min(y + block_size, h)
                x_end = min(x + block_size, w)
                
                block = image[y:y_end, x:x_end]
                avg_color = np.mean(block, axis=(0, 1))
                result[y:y_end, x:x_end] = avg_color
        
        return result
    
    def _render_blur(
        self, 
        image: np.ndarray,
        parameters: Dict[str, Any],
        quality: str
    ) -> np.ndarray:
        """ブラーレンダリング"""
        radius = parameters.get("radius", 10.0)
        
        # 品質に応じて処理を調整
        if quality == "low":
            # ボックスフィルタで高速処理
            kernel_size = int(radius * 2) + 1
            return cv2.blur(image, (kernel_size, kernel_size))
        elif quality == "medium":
            # ガウシアンブラー
            return cv2.GaussianBlur(image, (0, 0), sigmaX=radius, sigmaY=radius)
        else:  # high
            # 多段階ガウシアンブラー
            result = image.copy()
            steps = 3
            for i in range(steps):
                sigma = radius * (i + 1) / steps
                result = cv2.GaussianBlur(result, (0, 0), sigmaX=sigma, sigmaY=sigma)
            return result
    
    def _render_pixelate(
        self, 
        image: np.ndarray,
        parameters: Dict[str, Any],
        quality: str
    ) -> np.ndarray:
        """ピクセレートレンダリング"""
        pixel_size = parameters.get("pixel_size", 8)
        
        # 品質に応じてピクセルサイズを調整
        if quality == "low":
            pixel_size = max(pixel_size, 12)
        elif quality == "medium":
            pixel_size = max(pixel_size, 8)
        # high品質はそのまま
        
        h, w = image.shape[:2]
        
        # ダウンサンプリング
        new_h = max(1, h // pixel_size)
        new_w = max(1, w // pixel_size)
        
        small = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        
        return pixelated