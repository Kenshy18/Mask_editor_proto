#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクトプレビュー実装

エフェクトのプレビュー生成機能を提供。
"""
from typing import Tuple, Dict, Any
import numpy as np
import cv2
import logging

from domain.dto.effect_dto import EffectType, EffectConfigDTO
from domain.dto.frame_dto import FrameDTO
from domain.dto.mask_dto import MaskDTO
from domain.ports.secondary.effect_ports import IEffectPreview, IEffectEngine

logger = logging.getLogger(__name__)


class EffectPreview:
    """エフェクトプレビュー実装"""
    
    def __init__(self, effect_engine: IEffectEngine):
        """
        初期化
        
        Args:
            effect_engine: エフェクトエンジン
        """
        self._effect_engine = effect_engine
    
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
        # プレビューサイズに縮小
        scale_x = preview_size[0] / frame.width
        scale_y = preview_size[1] / frame.height
        scale = min(scale_x, scale_y)
        
        new_width = int(frame.width * scale)
        new_height = int(frame.height * scale)
        
        # フレームをリサイズ
        resized_frame = cv2.resize(
            frame.data, 
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )
        
        # マスクをリサイズ
        resized_mask = cv2.resize(
            mask.data,
            (new_width, new_height),
            interpolation=cv2.INTER_NEAREST
        )
        
        # プレビュー用のフレームDTOを作成
        preview_frame = FrameDTO(
            data=resized_frame,
            width=new_width,
            height=new_height,
            frame_number=frame.frame_number,
            timestamp_ms=frame.timestamp_ms,
            pts=frame.pts,
            dts=frame.dts,
            duration_ms=frame.duration_ms,
            is_keyframe=frame.is_keyframe,
            colorspace=frame.colorspace,
            metadata=frame.metadata
        )
        
        # プレビュー用のマスクDTOを作成
        preview_mask = MaskDTO(
            data=resized_mask,
            mask_id=mask.mask_id,
            class_name=mask.class_name,
            confidence=mask.confidence,
            frame_index=mask.frame_index,
            source=mask.source,
            metadata=mask.metadata
        )
        
        # エフェクトを適用（プレビューモード）
        processed_frame, results = self._effect_engine.apply_effects(
            preview_frame,
            [preview_mask],
            [config],
            preview_mode=True
        )
        
        # 結果をプレビューサイズにパディング
        preview = np.zeros(
            (preview_size[1], preview_size[0], 3),
            dtype=np.uint8
        )
        
        # 中央に配置
        y_offset = (preview_size[1] - new_height) // 2
        x_offset = (preview_size[0] - new_width) // 2
        
        preview[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = processed_frame.data
        
        # エフェクト情報をオーバーレイ
        self._add_effect_info_overlay(preview, config, results.get(config.effect_id))
        
        return preview
    
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
        # グラデーションパターンを作成
        pattern = self._create_test_pattern(size)
        
        # エフェクトタイプごとのサムネイル生成
        if effect_type == EffectType.MOSAIC:
            thumbnail = self._create_mosaic_thumbnail(pattern, parameters)
        elif effect_type == EffectType.BLUR:
            thumbnail = self._create_blur_thumbnail(pattern, parameters)
        elif effect_type == EffectType.PIXELATE:
            thumbnail = self._create_pixelate_thumbnail(pattern, parameters)
        else:
            thumbnail = pattern
        
        # エフェクト名を追加
        self._add_effect_name(thumbnail, effect_type)
        
        return thumbnail
    
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
        # エフェクトを適用
        processed_frame, _ = self._effect_engine.apply_effects(
            frame,
            [mask],
            [config],
            preview_mode=False
        )
        
        # 比較画像を作成
        original = frame.data
        processed = processed_frame.data
        
        h, w = original.shape[:2]
        result = np.zeros_like(original)
        
        if split_type == "vertical":
            # 垂直分割（左が元画像、右が処理済み）
            mid_x = w // 2
            result[:, :mid_x] = original[:, :mid_x]
            result[:, mid_x:] = processed[:, mid_x:]
            
            # 分割線を描画
            cv2.line(result, (mid_x, 0), (mid_x, h), (255, 255, 255), 2)
            
        elif split_type == "horizontal":
            # 水平分割（上が元画像、下が処理済み）
            mid_y = h // 2
            result[:mid_y, :] = original[:mid_y, :]
            result[mid_y:, :] = processed[mid_y:, :]
            
            # 分割線を描画
            cv2.line(result, (0, mid_y), (w, mid_y), (255, 255, 255), 2)
            
        elif split_type == "diagonal":
            # 対角分割
            for y in range(h):
                for x in range(w):
                    if x < (y * w / h):
                        result[y, x] = original[y, x]
                    else:
                        result[y, x] = processed[y, x]
            
            # 対角線を描画
            cv2.line(result, (0, 0), (w, h), (255, 255, 255), 2)
        
        else:
            # デフォルトは垂直分割
            return self.create_before_after(frame, mask, config, "vertical")
        
        # ラベルを追加
        self._add_before_after_labels(result, split_type)
        
        return result
    
    def _create_test_pattern(self, size: Tuple[int, int]) -> np.ndarray:
        """テストパターンを生成"""
        width, height = size
        pattern = np.zeros((height, width, 3), dtype=np.uint8)
        
        # カラフルなグラデーション
        for y in range(height):
            for x in range(width):
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(255 * (1 - x / width) * (1 - y / height))
                pattern[y, x] = [r, g, b]
        
        # グリッドラインを追加
        grid_size = 16
        for i in range(0, width, grid_size):
            cv2.line(pattern, (i, 0), (i, height), (128, 128, 128), 1)
        for i in range(0, height, grid_size):
            cv2.line(pattern, (0, i), (width, i), (128, 128, 128), 1)
        
        return pattern
    
    def _create_mosaic_thumbnail(
        self, 
        pattern: np.ndarray,
        parameters: Dict[str, Any]
    ) -> np.ndarray:
        """モザイクサムネイルを生成"""
        block_size = parameters.get("block_size", 16)
        h, w = pattern.shape[:2]
        result = pattern.copy()
        
        # 中央部分にモザイクを適用
        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 3
        
        for y in range(center_y - radius, center_y + radius, block_size):
            for x in range(center_x - radius, center_x + radius, block_size):
                if 0 <= y < h and 0 <= x < w:
                    y_end = min(y + block_size, h)
                    x_end = min(x + block_size, w)
                    
                    block = pattern[y:y_end, x:x_end]
                    avg_color = np.mean(block, axis=(0, 1))
                    result[y:y_end, x:x_end] = avg_color
        
        return result
    
    def _create_blur_thumbnail(
        self, 
        pattern: np.ndarray,
        parameters: Dict[str, Any]
    ) -> np.ndarray:
        """ブラーサムネイルを生成"""
        radius = parameters.get("radius", 10.0)
        h, w = pattern.shape[:2]
        result = pattern.copy()
        
        # 中央部分にブラーを適用
        center_x, center_y = w // 2, h // 2
        mask_radius = min(w, h) // 3
        
        # 円形マスクを作成
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), mask_radius, 255, -1)
        
        # ブラーを適用
        blurred = cv2.GaussianBlur(pattern, (0, 0), sigmaX=radius, sigmaY=radius)
        
        # マスクでブレンド
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        mask_norm = mask_3ch.astype(np.float32) / 255.0
        result = (blurred * mask_norm + pattern * (1 - mask_norm)).astype(np.uint8)
        
        return result
    
    def _create_pixelate_thumbnail(
        self, 
        pattern: np.ndarray,
        parameters: Dict[str, Any]
    ) -> np.ndarray:
        """ピクセレートサムネイルを生成"""
        pixel_size = parameters.get("pixel_size", 8)
        h, w = pattern.shape[:2]
        result = pattern.copy()
        
        # 中央部分にピクセレートを適用
        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 3
        
        # 対象領域を抽出
        y_start = max(0, center_y - radius)
        y_end = min(h, center_y + radius)
        x_start = max(0, center_x - radius)
        x_end = min(w, center_x + radius)
        
        roi = pattern[y_start:y_end, x_start:x_end]
        
        # ピクセレート処理
        roi_h, roi_w = roi.shape[:2]
        new_h = max(1, roi_h // pixel_size)
        new_w = max(1, roi_w // pixel_size)
        
        small = cv2.resize(roi, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small, (roi_w, roi_h), interpolation=cv2.INTER_NEAREST)
        
        result[y_start:y_end, x_start:x_end] = pixelated
        
        return result
    
    def _add_effect_name(self, image: np.ndarray, effect_type: EffectType):
        """エフェクト名を画像に追加"""
        h, w = image.shape[:2]
        
        # 背景を少し暗くする
        overlay = image.copy()
        cv2.rectangle(overlay, (0, h-25), (w, h), (0, 0, 0), -1)
        image[:] = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)
        
        # テキストを追加
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = effect_type.value.upper()
        text_size = cv2.getTextSize(text, font, 0.5, 1)[0]
        text_x = (w - text_size[0]) // 2
        text_y = h - 8
        
        cv2.putText(
            image, text, (text_x, text_y),
            font, 0.5, (255, 255, 255), 1, cv2.LINE_AA
        )
    
    def _add_effect_info_overlay(
        self, 
        image: np.ndarray,
        config: EffectConfigDTO,
        result: Any
    ):
        """エフェクト情報をオーバーレイ"""
        h, w = image.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # エフェクト名
        text = f"{config.effect_type.value.upper()}"
        cv2.putText(
            image, text, (10, 20),
            font, 0.5, (255, 255, 255), 1, cv2.LINE_AA
        )
        
        # 処理時間（結果がある場合）
        if result and hasattr(result, 'processing_time_ms'):
            time_text = f"{result.processing_time_ms:.1f}ms"
            cv2.putText(
                image, time_text, (w - 60, 20),
                font, 0.4, (0, 255, 0), 1, cv2.LINE_AA
            )
    
    def _add_before_after_labels(self, image: np.ndarray, split_type: str):
        """ビフォーアフターラベルを追加"""
        h, w = image.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        if split_type == "vertical":
            # 左側に"BEFORE"
            cv2.putText(
                image, "BEFORE", (10, 30),
                font, 0.8, (255, 255, 255), 2, cv2.LINE_AA
            )
            # 右側に"AFTER"
            cv2.putText(
                image, "AFTER", (w // 2 + 10, 30),
                font, 0.8, (255, 255, 255), 2, cv2.LINE_AA
            )
            
        elif split_type == "horizontal":
            # 上側に"BEFORE"
            cv2.putText(
                image, "BEFORE", (10, 30),
                font, 0.8, (255, 255, 255), 2, cv2.LINE_AA
            )
            # 下側に"AFTER"
            cv2.putText(
                image, "AFTER", (10, h // 2 + 30),
                font, 0.8, (255, 255, 255), 2, cv2.LINE_AA
            )
            
        elif split_type == "diagonal":
            # 左上に"BEFORE"
            cv2.putText(
                image, "BEFORE", (10, 30),
                font, 0.8, (255, 255, 255), 2, cv2.LINE_AA
            )
            # 右下に"AFTER"
            cv2.putText(
                image, "AFTER", (w - 100, h - 10),
                font, 0.8, (255, 255, 255), 2, cv2.LINE_AA
            )