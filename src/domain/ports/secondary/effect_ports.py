#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクト処理ポート定義

エフェクトの適用、管理、プレビューに関するインターフェース。
"""
from typing import Protocol, Optional, List, Dict, Any, Tuple
import numpy as np

from domain.dto.effect_dto import (
    EffectType, EffectConfigDTO, EffectResultDTO, 
    EffectDefinitionDTO, EffectPresetDTO
)
from domain.dto.frame_dto import FrameDTO
from domain.dto.mask_dto import MaskDTO


class IEffect(Protocol):
    """個別エフェクトインターフェース"""
    
    @property
    def effect_type(self) -> EffectType:
        """エフェクトタイプを取得"""
        ...
    
    @property
    def definition(self) -> EffectDefinitionDTO:
        """エフェクト定義を取得"""
        ...
    
    def validate_config(self, config: EffectConfigDTO) -> bool:
        """
        エフェクト設定の妥当性を検証
        
        Args:
            config: エフェクト設定
            
        Returns:
            妥当な場合True
        """
        ...
    
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
        ...
    
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
        ...


class IEffectEngine(Protocol):
    """エフェクトエンジンインターフェース"""
    
    def register_effect(self, effect: IEffect) -> None:
        """
        エフェクトを登録
        
        Args:
            effect: エフェクト実装
        """
        ...
    
    def get_available_effects(self) -> List[EffectDefinitionDTO]:
        """
        利用可能なエフェクト一覧を取得
        
        Returns:
            エフェクト定義のリスト
        """
        ...
    
    def get_effect(self, effect_type: EffectType) -> Optional[IEffect]:
        """
        指定タイプのエフェクトを取得
        
        Args:
            effect_type: エフェクトタイプ
            
        Returns:
            エフェクト実装（存在しない場合None）
        """
        ...
    
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
        ...
    
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
        ...
    
    @property
    def gpu_available(self) -> bool:
        """GPU高速化が利用可能か"""
        ...
    
    def set_gpu_enabled(self, enabled: bool) -> None:
        """
        GPU高速化の有効/無効を設定
        
        Args:
            enabled: 有効にする場合True
        """
        ...


class IEffectRenderer(Protocol):
    """エフェクトレンダラーインターフェース"""
    
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
        ...
    
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
        ...
    
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
        ...


class IEffectPreview(Protocol):
    """エフェクトプレビューインターフェース"""
    
    def generate_preview(
        self,
        frame: FrameDTO,
        mask: MaskDTO,
        config: EffectConfigDTO,
        preview_size: Tuple[int, int] = (320, 240)
    ) -> np.ndarray:
        """
        エフェクトプレビューを生成
        
        Args:
            frame: 入力フレーム
            mask: 適用マスク
            config: エフェクト設定
            preview_size: プレビューサイズ
            
        Returns:
            プレビュー画像（RGB）
        """
        ...
    
    def generate_thumbnail(
        self,
        effect_type: EffectType,
        parameters: Dict[str, Any],
        size: Tuple[int, int] = (128, 128)
    ) -> np.ndarray:
        """
        エフェクトサムネイルを生成
        
        Args:
            effect_type: エフェクトタイプ
            parameters: エフェクトパラメータ
            size: サムネイルサイズ
            
        Returns:
            サムネイル画像（RGB）
        """
        ...
    
    def create_before_after(
        self,
        frame: FrameDTO,
        mask: MaskDTO,
        config: EffectConfigDTO,
        split_type: str = "vertical"
    ) -> np.ndarray:
        """
        ビフォーアフター比較画像を生成
        
        Args:
            frame: 入力フレーム
            mask: 適用マスク
            config: エフェクト設定
            split_type: 分割タイプ（vertical/horizontal/diagonal）
            
        Returns:
            比較画像（RGB）
        """
        ...


class IEffectPresetManager(Protocol):
    """エフェクトプリセット管理インターフェース"""
    
    def save_preset(self, preset: EffectPresetDTO) -> bool:
        """
        プリセットを保存
        
        Args:
            preset: プリセット
            
        Returns:
            成功した場合True
        """
        ...
    
    def load_preset(self, name: str) -> Optional[EffectPresetDTO]:
        """
        プリセットを読み込み
        
        Args:
            name: プリセット名
            
        Returns:
            プリセット（存在しない場合None）
        """
        ...
    
    def list_presets(
        self, 
        effect_type: Optional[EffectType] = None,
        category: Optional[str] = None
    ) -> List[EffectPresetDTO]:
        """
        プリセット一覧を取得
        
        Args:
            effect_type: フィルタリング用エフェクトタイプ
            category: フィルタリング用カテゴリー
            
        Returns:
            プリセットリスト
        """
        ...
    
    def delete_preset(self, name: str) -> bool:
        """
        プリセットを削除
        
        Args:
            name: プリセット名
            
        Returns:
            成功した場合True
        """
        ...
    
    def export_presets(self, path: str) -> bool:
        """
        プリセットをファイルにエクスポート
        
        Args:
            path: エクスポート先パス
            
        Returns:
            成功した場合True
        """
        ...
    
    def import_presets(self, path: str) -> int:
        """
        プリセットをファイルからインポート
        
        Args:
            path: インポート元パス
            
        Returns:
            インポートしたプリセット数
        """
        ...