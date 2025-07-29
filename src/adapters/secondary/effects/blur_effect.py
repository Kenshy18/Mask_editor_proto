#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラーエフェクト実装

指定領域にぼかし処理を適用するエフェクト。
"""
import time
from typing import Tuple, Dict, Any
import numpy as np
import cv2

from domain.dto.effect_dto import (
    EffectType, EffectConfigDTO, EffectResultDTO, 
    EffectDefinitionDTO, STANDARD_EFFECTS
)
from domain.ports.secondary.effect_ports import IEffect


class BlurEffect:
    """ブラーエフェクト実装"""
    
    def __init__(self):
        self._effect_type = EffectType.BLUR
        self._definition = STANDARD_EFFECTS[EffectType.BLUR]
    
    @property
    def effect_type(self) -> EffectType:
        """エフェクトタイプを取得"""
        return self._effect_type
    
    @property
    def definition(self) -> EffectDefinitionDTO:
        """エフェクト定義を取得"""
        return self._definition
    
    def validate_config(self, config: EffectConfigDTO) -> bool:
        """
        エフェクト設定の妥当性を検証
        
        Args:
            config: エフェクト設定
            
        Returns:
            妥当な場合True
        """
        if config.effect_type != self._effect_type:
            return False
        
        # パラメータの検証
        for param_def in self._definition.parameters:
            param_name = param_def.name
            if param_name in config.parameters:
                value = config.parameters[param_name]
                if not param_def.validate_value(value):
                    return False
        
        return True
    
    def apply(
        self, 
        frame: np.ndarray,
        mask: np.ndarray,
        config: EffectConfigDTO,
        gpu_available: bool = False
    ) -> Tuple[np.ndarray, EffectResultDTO]:
        """
        エフェクトを適用
        
        Args:
            frame: 入力フレーム（RGB、uint8）
            mask: 適用マスク（グレースケール、uint8）
            config: エフェクト設定
            gpu_available: GPU使用可能フラグ
            
        Returns:
            (処理済みフレーム, 結果情報)
        """
        start_time = time.time()
        
        # パラメータ取得
        radius = config.parameters.get("radius", 10.0)
        quality = config.parameters.get("quality", "high")
        intensity = config.intensity
        
        # 結果フレームを準備
        result_frame = frame.copy()
        
        # マスクの有効領域を取得
        mask_indices = np.where(mask > 0)
        if len(mask_indices[0]) == 0:
            # マスク領域がない場合は元画像をそのまま返す
            return result_frame, EffectResultDTO(
                success=True,
                processing_time_ms=0,
                statistics={"pixels_processed": 0}
            )
        
        # バウンディングボックスを計算（処理効率化のため）
        y_min, y_max = mask_indices[0].min(), mask_indices[0].max()
        x_min, x_max = mask_indices[1].min(), mask_indices[1].max()
        
        # ブラー処理のためのパディングを追加
        padding = int(radius * 3)  # ガウシアンカーネルのサイズ考慮
        y_min_pad = max(0, y_min - padding)
        y_max_pad = min(frame.shape[0], y_max + padding + 1)
        x_min_pad = max(0, x_min - padding)
        x_max_pad = min(frame.shape[1], x_max + padding + 1)
        
        # 処理領域を抽出
        roi = frame[y_min_pad:y_max_pad, x_min_pad:x_max_pad]
        
        # 品質に基づいてブラー処理
        if quality == "low":
            # 低品質：シンプルなボックスフィルタ
            kernel_size = int(radius * 2) + 1
            blurred_roi = cv2.blur(roi, (kernel_size, kernel_size))
        elif quality == "medium":
            # 中品質：標準的なガウシアンブラー
            blurred_roi = cv2.GaussianBlur(roi, (0, 0), sigmaX=radius, sigmaY=radius)
        else:  # high
            # 高品質：多段階ガウシアンブラー
            blurred_roi = self._apply_high_quality_blur(roi, radius)
        
        # 元のROIサイズにクロップ
        roi_y_start = y_min - y_min_pad
        roi_y_end = roi_y_start + (y_max - y_min + 1)
        roi_x_start = x_min - x_min_pad
        roi_x_end = roi_x_start + (x_max - x_min + 1)
        
        blurred_roi_cropped = blurred_roi[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
        original_roi = frame[y_min:y_max+1, x_min:x_max+1]
        roi_mask = mask[y_min:y_max+1, x_min:x_max+1]
        
        # マスクに基づいてブレンド
        roi_mask_3ch = cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2RGB)
        roi_mask_norm = roi_mask_3ch.astype(np.float32) / 255.0
        
        # 強度を適用
        roi_mask_norm *= intensity
        
        # エッジを滑らかにするためフェザリング
        if quality in ["medium", "high"]:
            feather_size = max(1, int(radius / 4))
            roi_mask_norm = cv2.GaussianBlur(roi_mask_norm, (0, 0), feather_size)
        
        # ブレンド処理
        blended_roi = (blurred_roi_cropped * roi_mask_norm + 
                      original_roi * (1 - roi_mask_norm)).astype(np.uint8)
        
        # 結果を元画像に戻す
        result_frame[y_min:y_max+1, x_min:x_max+1] = blended_roi
        
        # 処理時間を計算
        processing_time_ms = (time.time() - start_time) * 1000
        
        # 結果情報を作成
        result = EffectResultDTO(
            success=True,
            processing_time_ms=processing_time_ms,
            statistics={
                "pixels_processed": int(np.sum(mask > 0)),
                "radius": radius,
                "quality": quality,
                "intensity": intensity
            },
            gpu_used=False  # 現在の実装はCPUのみ
        )
        
        return result_frame, result
    
    def _apply_high_quality_blur(self, image: np.ndarray, radius: float) -> np.ndarray:
        """高品質ブラー（多段階処理）"""
        # 複数回のガウシアンブラーで高品質な結果を実現
        result = image.copy()
        
        # 段階的にブラーを適用
        steps = 3
        for i in range(steps):
            sigma = radius * (i + 1) / steps
            result = cv2.GaussianBlur(result, (0, 0), sigmaX=sigma, sigmaY=sigma)
        
        return result
    
    def estimate_performance(
        self, 
        resolution: Tuple[int, int],
        config: EffectConfigDTO
    ) -> float:
        """
        パフォーマンスを推定（ミリ秒）
        
        Args:
            resolution: 解像度（幅、高さ）
            config: エフェクト設定
            
        Returns:
            推定処理時間（ミリ秒）
        """
        width, height = resolution
        pixels = width * height
        radius = config.parameters.get("radius", 10.0)
        quality = config.parameters.get("quality", "high")
        
        # 基本処理時間（ミリ秒）
        base_time = 0.5
        
        # ピクセル数に基づく処理時間
        pixel_factor = pixels / (1920 * 1080)  # Full HDを基準
        
        # 半径による影響
        radius_factor = radius / 10.0  # 半径10を基準
        
        # 品質による補正
        quality_factors = {
            "low": 0.3,
            "medium": 1.0,
            "high": 3.0
        }
        quality_factor = quality_factors.get(quality, 1.0)
        
        estimated_time = base_time * pixel_factor * radius_factor * quality_factor
        
        return estimated_time