#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カスタムブラーエフェクトプラグイン

プラグインシステムの使用例として、高度なブラーエフェクトを実装。
"""
from typing import Dict, Any, Tuple
import numpy as np
import cv2
from enum import Enum

from domain.dto.effect_dto import (
    EffectDTO, EffectParameterDTO, EffectType,
    ParameterType, EffectBlendMode
)
from domain.ports.secondary.effect_ports import IEffect
from infrastructure.plugin_loader import EffectPluginBase


class CustomBlurType(Enum):
    """カスタムブラーの種類"""
    MOTION = "motion"
    RADIAL = "radial"
    ZOOM = "zoom"
    TILT_SHIFT = "tilt_shift"


class CustomBlurEffect(IEffect):
    """
    高度なカスタムブラーエフェクト
    
    モーションブラー、放射状ブラー、ズームブラー、
    ティルトシフトなどの高度なブラー効果を提供。
    """
    
    def get_metadata(self) -> EffectDTO:
        """エフェクトメタデータを取得"""
        return EffectDTO(
            effect_type=EffectType.CUSTOM,
            display_name="カスタムブラー",
            description="高度なブラー効果（モーション、放射状、ズーム、ティルトシフト）",
            parameters=[
                EffectParameterDTO(
                    name="blur_type",
                    display_name="ブラーの種類",
                    parameter_type=ParameterType.CHOICE,
                    default_value="motion",
                    choices=["motion", "radial", "zoom", "tilt_shift"]
                ),
                EffectParameterDTO(
                    name="strength",
                    display_name="強度",
                    parameter_type=ParameterType.FLOAT,
                    default_value=20.0,
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1
                ),
                EffectParameterDTO(
                    name="angle",
                    display_name="角度（モーションブラー用）",
                    parameter_type=ParameterType.FLOAT,
                    default_value=0.0,
                    min_value=-180.0,
                    max_value=180.0,
                    step=1.0
                ),
                EffectParameterDTO(
                    name="center_x",
                    display_name="中心X（放射状/ズーム用）",
                    parameter_type=ParameterType.FLOAT,
                    default_value=0.5,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01
                ),
                EffectParameterDTO(
                    name="center_y",
                    display_name="中心Y（放射状/ズーム用）",
                    parameter_type=ParameterType.FLOAT,
                    default_value=0.5,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.01
                ),
                EffectParameterDTO(
                    name="focus_area",
                    display_name="フォーカスエリア（ティルトシフト用）",
                    parameter_type=ParameterType.FLOAT,
                    default_value=0.3,
                    min_value=0.1,
                    max_value=0.9,
                    step=0.01
                )
            ],
            blend_modes=[EffectBlendMode.NORMAL, EffectBlendMode.OVERLAY],
            gpu_accelerated=True,
            supports_animation=True,
            version="1.0.0"
        )
    
    def apply(self, frame: np.ndarray, mask: np.ndarray, 
              parameters: Dict[str, Any]) -> np.ndarray:
        """エフェクトを適用"""
        blur_type = CustomBlurType(parameters.get("blur_type", "motion"))
        strength = parameters.get("strength", 20.0)
        
        if blur_type == CustomBlurType.MOTION:
            return self._apply_motion_blur(frame, mask, parameters)
        elif blur_type == CustomBlurType.RADIAL:
            return self._apply_radial_blur(frame, mask, parameters)
        elif blur_type == CustomBlurType.ZOOM:
            return self._apply_zoom_blur(frame, mask, parameters)
        elif blur_type == CustomBlurType.TILT_SHIFT:
            return self._apply_tilt_shift(frame, mask, parameters)
        
        return frame
    
    def _apply_motion_blur(self, frame: np.ndarray, mask: np.ndarray,
                          parameters: Dict[str, Any]) -> np.ndarray:
        """モーションブラーを適用"""
        strength = int(parameters.get("strength", 20))
        angle = parameters.get("angle", 0.0)
        
        # モーションブラーカーネルを作成
        kernel = self._create_motion_kernel(strength, angle)
        
        # ブラーを適用
        blurred = cv2.filter2D(frame, -1, kernel)
        
        # マスクを使って合成
        return self._blend_with_mask(frame, blurred, mask)
    
    def _apply_radial_blur(self, frame: np.ndarray, mask: np.ndarray,
                          parameters: Dict[str, Any]) -> np.ndarray:
        """放射状ブラーを適用"""
        strength = parameters.get("strength", 20.0) / 100.0
        center_x = parameters.get("center_x", 0.5)
        center_y = parameters.get("center_y", 0.5)
        
        h, w = frame.shape[:2]
        center = (int(w * center_x), int(h * center_y))
        
        # 放射状ブラーを段階的に適用
        result = frame.copy()
        num_steps = int(strength * 20) + 1
        
        for i in range(1, num_steps):
            scale = 1.0 + (i * strength / num_steps)
            M = cv2.getRotationMatrix2D(center, 0, scale)
            rotated = cv2.warpAffine(frame, M, (w, h))
            result = cv2.addWeighted(result, 0.7, rotated, 0.3, 0)
        
        return self._blend_with_mask(frame, result, mask)
    
    def _apply_zoom_blur(self, frame: np.ndarray, mask: np.ndarray,
                        parameters: Dict[str, Any]) -> np.ndarray:
        """ズームブラーを適用"""
        strength = parameters.get("strength", 20.0) / 100.0
        center_x = parameters.get("center_x", 0.5)
        center_y = parameters.get("center_y", 0.5)
        
        h, w = frame.shape[:2]
        center = (int(w * center_x), int(h * center_y))
        
        # ズームブラーを段階的に適用
        result = frame.copy()
        num_steps = int(strength * 15) + 1
        
        for i in range(1, num_steps):
            zoom = 1.0 - (i * strength / num_steps) * 0.2
            
            # 中心からズーム
            M = np.array([
                [zoom, 0, center[0] * (1 - zoom)],
                [0, zoom, center[1] * (1 - zoom)]
            ], dtype=np.float32)
            
            zoomed = cv2.warpAffine(frame, M, (w, h))
            result = cv2.addWeighted(result, 0.6, zoomed, 0.4, 0)
        
        return self._blend_with_mask(frame, result, mask)
    
    def _apply_tilt_shift(self, frame: np.ndarray, mask: np.ndarray,
                         parameters: Dict[str, Any]) -> np.ndarray:
        """ティルトシフト効果を適用"""
        strength = int(parameters.get("strength", 20))
        focus_area = parameters.get("focus_area", 0.3)
        center_y = parameters.get("center_y", 0.5)
        
        h, w = frame.shape[:2]
        
        # フォーカスエリアのグラデーションマスクを作成
        gradient_mask = np.zeros((h, w), dtype=np.float32)
        center_line = int(h * center_y)
        focus_height = int(h * focus_area)
        
        for y in range(h):
            distance = abs(y - center_line)
            if distance < focus_height / 2:
                gradient_mask[y, :] = 1.0
            else:
                blur_amount = min(1.0, (distance - focus_height / 2) / (h * 0.3))
                gradient_mask[y, :] = 1.0 - blur_amount
        
        # ブラーを適用
        blurred = cv2.GaussianBlur(frame, (strength * 2 + 1, strength * 2 + 1), 0)
        
        # グラデーションマスクで合成
        gradient_mask_3ch = np.stack([gradient_mask] * 3, axis=2)
        result = frame * gradient_mask_3ch + blurred * (1 - gradient_mask_3ch)
        result = result.astype(np.uint8)
        
        # 元のマスクとも合成
        return self._blend_with_mask(frame, result, mask)
    
    def _create_motion_kernel(self, size: int, angle: float) -> np.ndarray:
        """モーションブラーカーネルを作成"""
        # カーネルサイズは奇数にする
        kernel_size = size * 2 + 1
        kernel = np.zeros((kernel_size, kernel_size))
        
        # 角度をラジアンに変換
        angle_rad = np.deg2rad(angle)
        
        # 中心から指定角度方向にラインを引く
        center = kernel_size // 2
        for i in range(kernel_size):
            offset = i - center
            x = int(center + offset * np.cos(angle_rad))
            y = int(center + offset * np.sin(angle_rad))
            
            if 0 <= x < kernel_size and 0 <= y < kernel_size:
                kernel[y, x] = 1.0
        
        # 正規化
        kernel = kernel / np.sum(kernel)
        return kernel
    
    def _blend_with_mask(self, original: np.ndarray, processed: np.ndarray,
                        mask: np.ndarray) -> np.ndarray:
        """マスクを使って画像を合成"""
        # マスクを3チャンネルに拡張
        if len(mask.shape) == 2:
            mask_3ch = np.stack([mask] * 3, axis=2)
        else:
            mask_3ch = mask
        
        # 正規化
        mask_3ch = mask_3ch.astype(np.float32) / 255.0
        
        # 合成
        result = processed * mask_3ch + original * (1 - mask_3ch)
        return result.astype(np.uint8)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """パラメータを検証"""
        metadata = self.get_metadata()
        
        # 各パラメータを検証
        for param_def in metadata.parameters:
            param_name = param_def.name
            param_value = parameters.get(param_name, param_def.default_value)
            
            # 型チェック
            if param_def.parameter_type == ParameterType.CHOICE:
                if param_value not in param_def.choices:
                    return False, f"Invalid choice for {param_name}: {param_value}"
            
            elif param_def.parameter_type == ParameterType.FLOAT:
                if not isinstance(param_value, (int, float)):
                    return False, f"{param_name} must be a number"
                
                if param_def.min_value is not None and param_value < param_def.min_value:
                    return False, f"{param_name} must be >= {param_def.min_value}"
                
                if param_def.max_value is not None and param_value > param_def.max_value:
                    return False, f"{param_name} must be <= {param_def.max_value}"
        
        return True, ""
    
    def estimate_performance(self, frame_size: Tuple[int, int],
                           parameters: Dict[str, Any]) -> Dict[str, Any]:
        """パフォーマンスを推定"""
        width, height = frame_size
        pixels = width * height
        
        blur_type = parameters.get("blur_type", "motion")
        strength = parameters.get("strength", 20.0)
        
        # ブラータイプによって処理時間が異なる
        base_time = pixels / 1_000_000  # 1メガピクセルあたり1ms
        
        if blur_type == "motion":
            time_estimate = base_time * (1 + strength / 50)
        elif blur_type in ["radial", "zoom"]:
            # 段階的処理のため時間がかかる
            num_steps = int(strength / 100 * 20) + 1
            time_estimate = base_time * num_steps
        else:  # tilt_shift
            time_estimate = base_time * 2
        
        return {
            "estimated_time_ms": time_estimate,
            "memory_usage_mb": pixels * 4 * 3 / 1_000_000,  # RGB画像3枚分
            "gpu_capable": True,
            "complexity": "high" if blur_type in ["radial", "zoom"] else "medium"
        }


class CustomBlurPlugin(EffectPluginBase):
    """カスタムブラーエフェクトのプラグイン"""
    
    def __init__(self):
        super().__init__(CustomBlurEffect)
    
    @property
    def name(self) -> str:
        return "custom_blur"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "高度なブラー効果を提供するプラグイン"