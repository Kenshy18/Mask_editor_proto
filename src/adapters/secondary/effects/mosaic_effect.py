#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
モザイクエフェクト実装

指定領域にモザイク処理を適用するエフェクト。
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


class MosaicEffect:
    """モザイクエフェクト実装"""
    
    def __init__(self):
        self._effect_type = EffectType.MOSAIC
        self._definition = STANDARD_EFFECTS[EffectType.MOSAIC]
    
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
        block_size = config.parameters.get("block_size", 16)
        shape = config.parameters.get("shape", "square")
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
        
        # モザイク処理
        if shape == "square":
            mosaic_roi = self._apply_square_mosaic(roi, block_size)
        elif shape == "hexagon":
            mosaic_roi = self._apply_hexagon_mosaic(roi, block_size)
        elif shape == "circle":
            mosaic_roi = self._apply_circle_mosaic(roi, block_size)
        else:
            mosaic_roi = self._apply_square_mosaic(roi, block_size)
        
        # マスクに基づいてブレンド
        roi_mask_3ch = cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2RGB)
        roi_mask_norm = roi_mask_3ch.astype(np.float32) / 255.0
        
        # 強度を適用
        roi_mask_norm *= intensity
        
        # ブレンド処理
        blended_roi = (mosaic_roi * roi_mask_norm + roi * (1 - roi_mask_norm)).astype(np.uint8)
        
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
                "block_size": block_size,
                "shape": shape,
                "intensity": intensity
            },
            gpu_used=False  # 現在の実装はCPUのみ
        )
        
        return result_frame, result
    
    def _apply_square_mosaic(self, image: np.ndarray, block_size: int) -> np.ndarray:
        """正方形モザイクを適用"""
        h, w = image.shape[:2]
        result = image.copy()
        
        # ブロックごとに処理
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                # ブロックの範囲を計算
                y_end = min(y + block_size, h)
                x_end = min(x + block_size, w)
                
                # ブロック内の平均色を計算
                block = image[y:y_end, x:x_end]
                avg_color = np.mean(block, axis=(0, 1))
                
                # ブロック全体を平均色で塗りつぶし
                result[y:y_end, x:x_end] = avg_color
        
        return result
    
    def _apply_hexagon_mosaic(self, image: np.ndarray, block_size: int) -> np.ndarray:
        """六角形モザイクを適用（簡易実装）"""
        # 現在は正方形モザイクで代用
        # TODO: 実際の六角形グリッドを実装
        return self._apply_square_mosaic(image, block_size)
    
    def _apply_circle_mosaic(self, image: np.ndarray, block_size: int) -> np.ndarray:
        """円形モザイクを適用"""
        h, w = image.shape[:2]
        result = image.copy()
        radius = block_size // 2
        
        # グリッド上に円を配置
        for y in range(radius, h - radius, block_size):
            for x in range(radius, w - radius, block_size):
                # 円内のピクセルを取得
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.circle(mask, (x, y), radius, 255, -1)
                
                # 円内の平均色を計算
                circle_pixels = image[mask > 0]
                if len(circle_pixels) > 0:
                    avg_color = np.mean(circle_pixels, axis=0)
                    
                    # 円を平均色で塗りつぶし
                    result[mask > 0] = avg_color
        
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
        block_size = config.parameters.get("block_size", 16)
        
        # ブロック数に基づく推定
        blocks = (width // block_size) * (height // block_size)
        
        # 基本処理時間（ミリ秒）
        base_time = 0.1  # 基本オーバーヘッド
        per_block_time = 0.001  # ブロックあたりの処理時間
        
        estimated_time = base_time + (blocks * per_block_time)
        
        # 形状による補正
        shape = config.parameters.get("shape", "square")
        if shape == "circle":
            estimated_time *= 1.5  # 円形は処理が重い
        elif shape == "hexagon":
            estimated_time *= 1.2
        
        return estimated_time