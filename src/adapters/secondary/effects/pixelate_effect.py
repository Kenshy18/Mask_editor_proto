#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ピクセレートエフェクト実装

指定領域をピクセル化するエフェクト。
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


class PixelateEffect:
    """ピクセレートエフェクト実装"""
    
    def __init__(self):
        self._effect_type = EffectType.PIXELATE
        self._definition = STANDARD_EFFECTS[EffectType.PIXELATE]
    
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
        pixel_size = config.parameters.get("pixel_size", 8)
        interpolation = config.parameters.get("interpolation", "nearest")
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
        
        # バウンディングボックスを計算
        y_min, y_max = mask_indices[0].min(), mask_indices[0].max()
        x_min, x_max = mask_indices[1].min(), mask_indices[1].max()
        
        # 処理領域を抽出
        roi = frame[y_min:y_max+1, x_min:x_max+1]
        roi_mask = mask[y_min:y_max+1, x_min:x_max+1]
        
        # ピクセレート処理
        pixelated_roi = self._apply_pixelation(roi, pixel_size, interpolation)
        
        # マスクに基づいてブレンド
        roi_mask_3ch = cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2RGB)
        roi_mask_norm = roi_mask_3ch.astype(np.float32) / 255.0
        
        # 強度を適用
        roi_mask_norm *= intensity
        
        # エッジを滑らかにするため軽いフェザリング
        if interpolation != "nearest":
            feather_size = max(1, pixel_size // 4)
            kernel_size = feather_size * 2 + 1
            roi_mask_norm = cv2.GaussianBlur(
                roi_mask_norm, 
                (kernel_size, kernel_size), 
                feather_size / 2
            )
        
        # ブレンド処理
        blended_roi = (pixelated_roi * roi_mask_norm + 
                      roi * (1 - roi_mask_norm)).astype(np.uint8)
        
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
                "pixel_size": pixel_size,
                "interpolation": interpolation,
                "intensity": intensity,
                "effective_pixels": (roi.shape[0] // pixel_size) * (roi.shape[1] // pixel_size)
            },
            gpu_used=False  # 現在の実装はCPUのみ
        )
        
        return result_frame, result
    
    def _apply_pixelation(
        self, 
        image: np.ndarray, 
        pixel_size: int, 
        interpolation: str
    ) -> np.ndarray:
        """
        ピクセレート処理を適用
        
        Args:
            image: 入力画像
            pixel_size: ピクセルサイズ
            interpolation: 補間方法
            
        Returns:
            ピクセル化された画像
        """
        h, w = image.shape[:2]
        
        # ダウンサンプリング
        # 新しいサイズを計算（最低1ピクセルは保持）
        new_h = max(1, h // pixel_size)
        new_w = max(1, w // pixel_size)
        
        # 補間方法を選択
        if interpolation == "nearest":
            inter_method = cv2.INTER_NEAREST
        elif interpolation == "linear":
            inter_method = cv2.INTER_LINEAR
        elif interpolation == "cubic":
            inter_method = cv2.INTER_CUBIC
        else:
            inter_method = cv2.INTER_NEAREST
        
        # ダウンサンプリング
        small = cv2.resize(image, (new_w, new_h), interpolation=inter_method)
        
        # アップサンプリング（最近傍補間で元のサイズに戻す）
        # ピクセレート効果を維持するため、アップサンプリングは常に最近傍補間
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        
        return pixelated
    
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
        pixel_size = config.parameters.get("pixel_size", 8)
        interpolation = config.parameters.get("interpolation", "nearest")
        
        # 基本処理時間（ミリ秒）
        base_time = 0.3
        
        # ピクセル数に基づく処理時間
        pixel_factor = pixels / (1920 * 1080)  # Full HDを基準
        
        # ピクセルサイズによる影響（小さいほど処理が重い）
        size_factor = 8.0 / pixel_size  # サイズ8を基準
        
        # 補間方法による補正
        interpolation_factors = {
            "nearest": 0.5,
            "linear": 1.0,
            "cubic": 2.0
        }
        interpolation_factor = interpolation_factors.get(interpolation, 1.0)
        
        estimated_time = base_time * pixel_factor * size_factor * interpolation_factor
        
        return estimated_time