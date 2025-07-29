#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクトDTO定義

エフェクト処理に関するデータ転送オブジェクト。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import numpy as np


class EffectType(Enum):
    """エフェクトタイプ列挙型"""
    MOSAIC = "mosaic"
    BLUR = "blur"
    PIXELATE = "pixelate"
    CUSTOM = "custom"


class ParameterType(Enum):
    """パラメータタイプ列挙型"""
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    COLOR = "color"
    RANGE = "range"


@dataclass(frozen=True)
class EffectParameterDTO:
    """
    エフェクトパラメータ定義
    
    各エフェクトが持つ調整可能なパラメータを表現。
    """
    # パラメータ名（一意識別子）
    name: str
    
    # 表示名（UI用）
    display_name: str
    
    # パラメータタイプ
    parameter_type: ParameterType
    
    # デフォルト値
    default_value: Union[int, float, bool, str]
    
    # 最小値（数値型の場合）
    min_value: Optional[Union[int, float]] = None
    
    # 最大値（数値型の場合）
    max_value: Optional[Union[int, float]] = None
    
    # ステップ（数値型の場合）
    step: Optional[Union[int, float]] = None
    
    # 選択肢（choice型の場合）
    choices: Optional[List[str]] = None
    
    # 単位（表示用）
    unit: Optional[str] = None
    
    # 説明
    description: Optional[str] = None
    
    # 高度な設定かどうか
    is_advanced: bool = False
    
    def __post_init__(self):
        """検証"""
        # 数値型の場合の検証
        if self.parameter_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            if self.min_value is not None and self.max_value is not None:
                if self.min_value > self.max_value:
                    raise ValueError(f"min_value ({self.min_value}) > max_value ({self.max_value})")
        
        # choice型の場合の検証
        if self.parameter_type == ParameterType.CHOICE:
            if not self.choices:
                raise ValueError("choices must be provided for CHOICE type")
    
    def validate_value(self, value: Any) -> bool:
        """値の妥当性を検証"""
        if self.parameter_type == ParameterType.INTEGER:
            if not isinstance(value, int):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
                
        elif self.parameter_type == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
                
        elif self.parameter_type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return False
                
        elif self.parameter_type == ParameterType.CHOICE:
            if value not in self.choices:
                return False
        
        return True


@dataclass(frozen=True)
class EffectConfigDTO:
    """
    エフェクト設定
    
    特定のエフェクトインスタンスの設定を保持。
    """
    # エフェクトタイプ
    effect_type: EffectType
    
    # エフェクトID（複数の同種エフェクトを区別）
    effect_id: str
    
    # 有効/無効
    enabled: bool = True
    
    # パラメータ値（パラメータ名 -> 値）
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 適用強度（0.0-1.0、全体的な効果の強さ）
    intensity: float = 1.0
    
    # ブレンドモード
    blend_mode: str = "normal"
    
    # 適用マスクID（特定のマスクにのみ適用する場合）
    target_mask_ids: Optional[List[int]] = None
    
    # カスタムデータ（エフェクト固有の追加情報）
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """検証"""
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError(f"intensity must be between 0.0 and 1.0, got {self.intensity}")
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "effect_type": self.effect_type.value,
            "effect_id": self.effect_id,
            "enabled": self.enabled,
            "parameters": self.parameters.copy(),
            "intensity": self.intensity,
            "blend_mode": self.blend_mode,
            "target_mask_ids": self.target_mask_ids.copy() if self.target_mask_ids else None,
            "custom_data": self.custom_data.copy()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EffectConfigDTO":
        """辞書から生成"""
        return cls(
            effect_type=EffectType(data["effect_type"]),
            effect_id=data["effect_id"],
            enabled=data.get("enabled", True),
            parameters=data.get("parameters", {}),
            intensity=data.get("intensity", 1.0),
            blend_mode=data.get("blend_mode", "normal"),
            target_mask_ids=data.get("target_mask_ids"),
            custom_data=data.get("custom_data", {})
        )


@dataclass(frozen=True)
class EffectPresetDTO:
    """
    エフェクトプリセット
    
    よく使うエフェクト設定の保存用。
    """
    # プリセット名
    name: str
    
    # 説明
    description: Optional[str] = None
    
    # エフェクトタイプ
    effect_type: EffectType = EffectType.MOSAIC
    
    # パラメータ値
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # カテゴリー（整理用）
    category: Optional[str] = None
    
    # タグ
    tags: List[str] = field(default_factory=list)
    
    # サムネイル（Base64エンコード画像）
    thumbnail: Optional[str] = None
    
    def to_config(self, effect_id: str) -> EffectConfigDTO:
        """プリセットからエフェクト設定を生成"""
        return EffectConfigDTO(
            effect_type=self.effect_type,
            effect_id=effect_id,
            parameters=self.parameters.copy()
        )


@dataclass(frozen=True)
class EffectDefinitionDTO:
    """
    エフェクト定義
    
    エフェクトタイプの完全な定義。
    """
    # エフェクトタイプ
    effect_type: EffectType
    
    # 表示名
    display_name: str
    
    # 説明
    description: str
    
    # アイコン（リソースパス）
    icon: Optional[str] = None
    
    # パラメータ定義
    parameters: List[EffectParameterDTO] = field(default_factory=list)
    
    # GPU高速化対応
    gpu_accelerated: bool = False
    
    # リアルタイムプレビュー対応
    realtime_preview: bool = True
    
    # 推奨される最大解像度
    max_resolution: Optional[tuple[int, int]] = None
    
    # パフォーマンスレベル（1:軽量、2:標準、3:重い）
    performance_level: int = 2
    
    def get_parameter(self, name: str) -> Optional[EffectParameterDTO]:
        """パラメータ定義を取得"""
        for param in self.parameters:
            if param.name == name:
                return param
        return None
    
    def get_default_config(self, effect_id: str) -> EffectConfigDTO:
        """デフォルト設定を生成"""
        default_params = {}
        for param in self.parameters:
            default_params[param.name] = param.default_value
        
        return EffectConfigDTO(
            effect_type=self.effect_type,
            effect_id=effect_id,
            parameters=default_params
        )


@dataclass(frozen=True)
class EffectResultDTO:
    """
    エフェクト適用結果
    
    エフェクト処理の結果を表現。
    """
    # 成功/失敗
    success: bool
    
    # 処理時間（ミリ秒）
    processing_time_ms: float
    
    # エラーメッセージ（失敗時）
    error_message: Optional[str] = None
    
    # 警告メッセージ
    warnings: List[str] = field(default_factory=list)
    
    # 処理統計
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    # GPU使用状況
    gpu_used: bool = False
    
    # メモリ使用量（MB）
    memory_usage_mb: Optional[float] = None


# 標準エフェクト定義
STANDARD_EFFECTS = {
    EffectType.MOSAIC: EffectDefinitionDTO(
        effect_type=EffectType.MOSAIC,
        display_name="モザイク",
        description="指定領域をモザイク処理します",
        parameters=[
            EffectParameterDTO(
                name="block_size",
                display_name="ブロックサイズ",
                parameter_type=ParameterType.INTEGER,
                default_value=16,
                min_value=4,
                max_value=64,
                step=2,
                unit="ピクセル",
                description="モザイクブロックのサイズ"
            ),
            EffectParameterDTO(
                name="shape",
                display_name="形状",
                parameter_type=ParameterType.CHOICE,
                default_value="square",
                choices=["square", "hexagon", "circle"],
                description="モザイクブロックの形状"
            )
        ],
        gpu_accelerated=True,
        performance_level=1
    ),
    
    EffectType.BLUR: EffectDefinitionDTO(
        effect_type=EffectType.BLUR,
        display_name="ブラー",
        description="指定領域をぼかし処理します",
        parameters=[
            EffectParameterDTO(
                name="radius",
                display_name="ぼかし半径",
                parameter_type=ParameterType.FLOAT,
                default_value=10.0,
                min_value=0.5,
                max_value=50.0,
                step=0.5,
                unit="ピクセル",
                description="ガウシアンブラーの半径"
            ),
            EffectParameterDTO(
                name="quality",
                display_name="品質",
                parameter_type=ParameterType.CHOICE,
                default_value="high",
                choices=["low", "medium", "high"],
                description="ブラー処理の品質"
            )
        ],
        gpu_accelerated=True,
        performance_level=2
    ),
    
    EffectType.PIXELATE: EffectDefinitionDTO(
        effect_type=EffectType.PIXELATE,
        display_name="ピクセレート",
        description="指定領域をピクセル化します",
        parameters=[
            EffectParameterDTO(
                name="pixel_size",
                display_name="ピクセルサイズ",
                parameter_type=ParameterType.INTEGER,
                default_value=8,
                min_value=2,
                max_value=32,
                step=1,
                unit="ピクセル",
                description="ピクセル化のサイズ"
            ),
            EffectParameterDTO(
                name="interpolation",
                display_name="補間方法",
                parameter_type=ParameterType.CHOICE,
                default_value="nearest",
                choices=["nearest", "linear", "cubic"],
                description="ピクセル補間方法",
                is_advanced=True
            )
        ],
        gpu_accelerated=True,
        performance_level=1
    )
}