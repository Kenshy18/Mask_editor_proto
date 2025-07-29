#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクトエンジン実装

複数のエフェクトを管理し、適用するエンジン。
"""
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from domain.dto.effect_dto import (
    EffectType, EffectConfigDTO, EffectResultDTO, 
    EffectDefinitionDTO, STANDARD_EFFECTS
)
from domain.dto.frame_dto import FrameDTO
from domain.dto.mask_dto import MaskDTO
from domain.ports.secondary.effect_ports import IEffect, IEffectEngine
from .effects import MosaicEffect, BlurEffect, PixelateEffect

logger = logging.getLogger(__name__)


class EffectEngine:
    """エフェクトエンジン実装"""
    
    def __init__(self, max_workers: int = 4):
        """
        初期化
        
        Args:
            max_workers: 並列処理の最大ワーカー数
        """
        self._effects: Dict[EffectType, IEffect] = {}
        self._gpu_enabled = False
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        
        # 標準エフェクトを登録
        self._register_standard_effects()
    
    def _register_standard_effects(self):
        """標準エフェクトを登録"""
        standard_effects = [
            MosaicEffect(),
            BlurEffect(),
            PixelateEffect()
        ]
        
        for effect in standard_effects:
            self.register_effect(effect)
    
    def register_effect(self, effect: IEffect) -> None:
        """
        エフェクトを登録
        
        Args:
            effect: エフェクト実装
        """
        with self._lock:
            self._effects[effect.effect_type] = effect
            logger.info(f"Registered effect: {effect.effect_type.value}")
    
    def get_available_effects(self) -> List[EffectDefinitionDTO]:
        """
        利用可能なエフェクト一覧を取得
        
        Returns:
            エフェクト定義のリスト
        """
        definitions = []
        with self._lock:
            for effect in self._effects.values():
                definitions.append(effect.definition)
        return definitions
    
    def get_effect(self, effect_type: EffectType) -> Optional[IEffect]:
        """
        指定タイプのエフェクトを取得
        
        Args:
            effect_type: エフェクトタイプ
            
        Returns:
            エフェクト実装（存在しない場合None）
        """
        with self._lock:
            return self._effects.get(effect_type)
    
    def apply_effects(
        self,
        frame: FrameDTO,
        masks: List[MaskDTO],
        configs: List[EffectConfigDTO],
        preview_mode: bool = False
    ) -> Tuple[FrameDTO, Dict[str, EffectResultDTO]]:
        """
        複数のエフェクトを連続適用
        
        Args:
            frame: 入力フレーム
            masks: マスクリスト
            configs: エフェクト設定リスト
            preview_mode: プレビューモード（低品質高速）
            
        Returns:
            (処理済みフレーム, エフェクトID -> 結果のマップ)
        """
        start_time = time.time()
        
        # フレームデータをnumpy配列に変換
        result_data = frame.data.copy()
        results = {}
        
        # 有効な設定のみフィルタリング
        active_configs = [c for c in configs if c.enabled]
        
        if not active_configs:
            # エフェクトがない場合は元のフレームをそのまま返す
            return frame, results
        
        # プレビューモードの場合、低品質設定に調整
        if preview_mode:
            active_configs = self._adjust_for_preview(active_configs)
        
        # エフェクトを順次適用
        for config in active_configs:
            effect = self.get_effect(config.effect_type)
            if not effect:
                logger.warning(f"Effect not found: {config.effect_type.value}")
                results[config.effect_id] = EffectResultDTO(
                    success=False,
                    processing_time_ms=0,
                    error_message=f"Effect type {config.effect_type.value} not registered"
                )
                continue
            
            # 対象マスクを選択
            target_masks = self._select_target_masks(masks, config.target_mask_ids)
            if not target_masks:
                logger.info(f"No target masks for effect: {config.effect_id}")
                results[config.effect_id] = EffectResultDTO(
                    success=True,
                    processing_time_ms=0,
                    statistics={"skipped": "no_target_masks"}
                )
                continue
            
            # マスクを統合
            combined_mask = self._combine_masks(target_masks, frame.width, frame.height)
            
            # エフェクトを適用
            try:
                processed_data, result = effect.apply(
                    result_data,
                    combined_mask,
                    config,
                    gpu_available=self._gpu_enabled
                )
                result_data = processed_data
                results[config.effect_id] = result
                
            except Exception as e:
                logger.error(f"Effect application failed: {config.effect_id}", exc_info=True)
                results[config.effect_id] = EffectResultDTO(
                    success=False,
                    processing_time_ms=0,
                    error_message=str(e)
                )
        
        # 処理済みフレームを作成
        total_time_ms = (time.time() - start_time) * 1000
        
        processed_frame = FrameDTO(
            data=result_data,
            width=frame.width,
            height=frame.height,
            frame_number=frame.frame_number,
            timestamp_ms=frame.timestamp_ms,
            pts=frame.pts,
            dts=frame.dts,
            duration_ms=frame.duration_ms,
            is_keyframe=frame.is_keyframe,
            colorspace=frame.colorspace,
            metadata=frame.metadata
        )
        
        # 全体の処理時間を記録
        results["_total"] = EffectResultDTO(
            success=True,
            processing_time_ms=total_time_ms,
            statistics={
                "effects_applied": len([r for r in results.values() if r.success]),
                "preview_mode": preview_mode
            }
        )
        
        return processed_frame, results
    
    def create_composite(
        self,
        effects: List[Tuple[EffectConfigDTO, MaskDTO]],
        resolution: Tuple[int, int]
    ) -> EffectConfigDTO:
        """
        複数エフェクトを合成して単一エフェクトとして扱う
        
        Args:
            effects: (設定, マスク)のリスト
            resolution: 合成解像度
            
        Returns:
            合成エフェクト設定
        """
        # 合成エフェクトのID生成
        composite_id = f"composite_{int(time.time() * 1000)}"
        
        # カスタムデータに元のエフェクト情報を保存
        custom_data = {
            "type": "composite",
            "resolution": resolution,
            "effects": []
        }
        
        for config, mask in effects:
            effect_info = {
                "config": config.to_dict(),
                "mask_data": mask.data.tolist() if mask.data.size < 1000 else "large_data",
                "mask_id": mask.mask_id
            }
            custom_data["effects"].append(effect_info)
        
        # 合成エフェクト設定を作成
        composite_config = EffectConfigDTO(
            effect_type=EffectType.CUSTOM,
            effect_id=composite_id,
            enabled=True,
            parameters={
                "composite_count": len(effects),
                "resolution": resolution
            },
            custom_data=custom_data
        )
        
        return composite_config
    
    @property
    def gpu_available(self) -> bool:
        """GPU高速化が利用可能か"""
        # TODO: 実際のGPU検出ロジックを実装
        return self._gpu_enabled
    
    def set_gpu_enabled(self, enabled: bool) -> None:
        """
        GPU高速化の有効/無効を設定
        
        Args:
            enabled: 有効にする場合True
        """
        self._gpu_enabled = enabled
        logger.info(f"GPU acceleration {'enabled' if enabled else 'disabled'}")
    
    def _adjust_for_preview(
        self, 
        configs: List[EffectConfigDTO]
    ) -> List[EffectConfigDTO]:
        """
        プレビュー用に設定を調整
        
        Args:
            configs: 元の設定リスト
            
        Returns:
            調整済み設定リスト
        """
        adjusted = []
        
        for config in configs:
            # パラメータをコピーして調整
            preview_params = config.parameters.copy()
            
            # エフェクトタイプごとの調整
            if config.effect_type == EffectType.MOSAIC:
                # ブロックサイズを大きくして高速化
                current_size = preview_params.get("block_size", 16)
                preview_params["block_size"] = min(32, current_size * 2)
                
            elif config.effect_type == EffectType.BLUR:
                # 品質を下げて高速化
                preview_params["quality"] = "low"
                # 半径も制限
                current_radius = preview_params.get("radius", 10.0)
                preview_params["radius"] = min(10.0, current_radius)
                
            elif config.effect_type == EffectType.PIXELATE:
                # ピクセルサイズを大きくして高速化
                current_size = preview_params.get("pixel_size", 8)
                preview_params["pixel_size"] = min(16, current_size * 2)
                # 補間も最速に
                preview_params["interpolation"] = "nearest"
            
            # 調整済み設定を作成
            preview_config = EffectConfigDTO(
                effect_type=config.effect_type,
                effect_id=config.effect_id,
                enabled=config.enabled,
                parameters=preview_params,
                intensity=config.intensity,
                blend_mode=config.blend_mode,
                target_mask_ids=config.target_mask_ids,
                custom_data=config.custom_data
            )
            
            adjusted.append(preview_config)
        
        return adjusted
    
    def _select_target_masks(
        self, 
        masks: List[MaskDTO],
        target_ids: Optional[List[int]]
    ) -> List[MaskDTO]:
        """
        対象マスクを選択
        
        Args:
            masks: 全マスクリスト
            target_ids: 対象ID（Noneの場合全て）
            
        Returns:
            選択されたマスクリスト
        """
        if target_ids is None:
            return masks
        
        return [m for m in masks if m.mask_id in target_ids]
    
    def _combine_masks(
        self, 
        masks: List[MaskDTO],
        width: int,
        height: int
    ) -> np.ndarray:
        """
        複数のマスクを統合
        
        Args:
            masks: マスクリスト
            width: 画像幅
            height: 画像高さ
            
        Returns:
            統合されたマスク
        """
        # 空のマスクを作成
        combined = np.zeros((height, width), dtype=np.uint8)
        
        # 各マスクを統合（OR演算）
        for mask in masks:
            # マスクデータが画像サイズと一致するか確認
            if mask.data.shape == (height, width):
                combined = np.maximum(combined, mask.data)
            else:
                logger.warning(
                    f"Mask size mismatch: expected ({height}, {width}), "
                    f"got {mask.data.shape}"
                )
        
        return combined
    
    def __del__(self):
        """クリーンアップ"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)