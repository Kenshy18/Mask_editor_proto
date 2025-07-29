#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDプレビューアダプター実装

ID操作のプレビュー生成機能を提供。
"""
import logging
from typing import List, Dict, Optional
import numpy as np
import cv2

from domain.dto.mask_dto import MaskDTO
from domain.ports.secondary.id_management_ports import IIDPreview

logger = logging.getLogger(__name__)


class IDPreviewAdapter(IIDPreview):
    """IDプレビューアダプター
    
    ID操作のプレビュー画像生成を実装。
    """
    
    def __init__(self):
        """初期化"""
        # カラーパレット（プレビュー用）
        self.delete_color = (255, 0, 0)  # 赤（削除部分）
        self.merge_source_color = (255, 165, 0)  # オレンジ（マージ元）
        self.merge_target_color = (0, 255, 0)  # 緑（マージ先）
        self.affected_color = (255, 255, 0)  # 黄色（影響部分）
        self.outline_color = (255, 255, 255)  # 白（輪郭）
        
    def preview_delete(self, mask_data: Dict[str, any], target_ids: List[int]) -> np.ndarray:
        """ID削除のプレビュー画像を生成"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # ベース画像を作成（グレースケール）
        base_image = self._create_base_image(mask_dto)
        
        # カラー画像に変換
        preview = cv2.cvtColor(base_image, cv2.COLOR_GRAY2BGR)
        
        # 削除対象IDをハイライト
        for target_id in target_ids:
            if target_id in mask_dto.object_ids:
                # 削除対象のマスクを取得
                delete_mask = (mask_dto.data == target_id)
                
                # 赤色でオーバーレイ
                preview[delete_mask] = self.delete_color
                
                # 輪郭を追加
                contours, _ = cv2.findContours(
                    delete_mask.astype(np.uint8),
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                cv2.drawContours(preview, contours, -1, self.outline_color, 2)
        
        # 情報をオーバーレイ
        self._add_text_overlay(
            preview, 
            f"Delete Preview: {len(target_ids)} IDs",
            f"IDs: {target_ids[:5]}{'...' if len(target_ids) > 5 else ''}"
        )
        
        return preview
    
    def preview_merge(self, mask_data: Dict[str, any], 
                     source_ids: List[int], 
                     target_id: int) -> np.ndarray:
        """IDマージのプレビュー画像を生成"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # ベース画像を作成
        base_image = self._create_base_image(mask_dto)
        preview = cv2.cvtColor(base_image, cv2.COLOR_GRAY2BGR)
        
        # ターゲットIDをハイライト（緑）
        if target_id in mask_dto.object_ids:
            target_mask = (mask_dto.data == target_id)
            preview[target_mask] = self.merge_target_color
            
            # 輪郭を追加
            contours, _ = cv2.findContours(
                target_mask.astype(np.uint8),
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(preview, contours, -1, self.outline_color, 2)
        
        # ソースIDをハイライト（オレンジ）
        merged_mask = np.zeros_like(mask_dto.data, dtype=bool)
        for source_id in source_ids:
            if source_id != target_id and source_id in mask_dto.object_ids:
                source_mask = (mask_dto.data == source_id)
                merged_mask |= source_mask
        
        # オレンジでオーバーレイ（半透明）
        overlay = preview.copy()
        overlay[merged_mask] = self.merge_source_color
        cv2.addWeighted(preview, 0.7, overlay, 0.3, 0, preview)
        
        # マージ後の輪郭を表示
        result_mask = (mask_dto.data == target_id) | merged_mask
        contours, _ = cv2.findContours(
            result_mask.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(preview, contours, -1, (0, 255, 255), 3)  # シアンで結果輪郭
        
        # 情報をオーバーレイ
        self._add_text_overlay(
            preview,
            f"Merge Preview: {len(source_ids)} → ID {target_id}",
            f"Source IDs: {source_ids[:3]}{'...' if len(source_ids) > 3 else ''}"
        )
        
        return preview
    
    def preview_threshold(self, mask_data: Dict[str, any], 
                         confidences: Dict[int, float], 
                         threshold: float) -> np.ndarray:
        """閾値適用のプレビュー画像を生成"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # ベース画像を作成
        base_image = self._create_base_image(mask_dto)
        preview = cv2.cvtColor(base_image, cv2.COLOR_GRAY2BGR)
        
        # 削除されるIDを特定
        ids_to_remove = []
        for obj_id in mask_dto.object_ids:
            confidence = confidences.get(obj_id, 1.0)
            if confidence < threshold:
                ids_to_remove.append(obj_id)
        
        # 削除対象をハイライト
        for obj_id in ids_to_remove:
            remove_mask = (mask_dto.data == obj_id)
            
            # 半透明の赤でオーバーレイ
            overlay = preview.copy()
            overlay[remove_mask] = self.delete_color
            cv2.addWeighted(preview, 0.7, overlay, 0.3, 0, preview)
            
            # 輪郭を追加
            contours, _ = cv2.findContours(
                remove_mask.astype(np.uint8),
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(preview, contours, -1, self.outline_color, 1)
            
            # 信頼度を表示
            if obj_id in confidences:
                y_indices, x_indices = np.where(remove_mask)
                if len(x_indices) > 0:
                    center_x = int(np.mean(x_indices))
                    center_y = int(np.mean(y_indices))
                    conf_text = f"{confidences[obj_id]:.2f}"
                    cv2.putText(preview, conf_text, (center_x-15, center_y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # 情報をオーバーレイ
        self._add_text_overlay(
            preview,
            f"Threshold Preview: {threshold:.2f}",
            f"Remove: {len(ids_to_remove)} IDs"
        )
        
        return preview
    
    def generate_diff_visualization(self, before_mask: Dict[str, any], 
                                   after_mask: Dict[str, any]) -> np.ndarray:
        """変更前後の差分を可視化"""
        before_dto = MaskDTO.from_dict(before_mask)
        after_dto = MaskDTO.from_dict(after_mask)
        
        # サイズチェック
        if before_dto.data.shape != after_dto.data.shape:
            raise ValueError("Mask dimensions must match for diff visualization")
        
        # 差分画像を作成
        height, width = before_dto.data.shape
        diff_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 背景色（グレー）
        diff_image[:, :] = (128, 128, 128)
        
        # 削除された部分（赤）
        removed_mask = (before_dto.data > 0) & (after_dto.data == 0)
        diff_image[removed_mask] = (255, 0, 0)
        
        # 追加された部分（緑）
        added_mask = (before_dto.data == 0) & (after_dto.data > 0)
        diff_image[added_mask] = (0, 255, 0)
        
        # 変更された部分（青）
        changed_mask = (before_dto.data > 0) & (after_dto.data > 0) & (before_dto.data != after_dto.data)
        diff_image[changed_mask] = (0, 0, 255)
        
        # 変更なしの部分（薄いグレー）
        unchanged_mask = (before_dto.data == after_dto.data) & (before_dto.data > 0)
        diff_image[unchanged_mask] = (200, 200, 200)
        
        # 統計情報を計算
        removed_pixels = np.sum(removed_mask)
        added_pixels = np.sum(added_mask)
        changed_pixels = np.sum(changed_mask)
        
        # 凡例と統計を追加
        legend_height = 120
        full_image = np.zeros((height + legend_height, width, 3), dtype=np.uint8)
        full_image[:height, :] = diff_image
        full_image[height:, :] = (255, 255, 255)  # 白背景
        
        # 凡例
        y_pos = height + 20
        cv2.rectangle(full_image, (20, y_pos), (40, y_pos + 15), (255, 0, 0), -1)
        cv2.putText(full_image, f"Removed: {removed_pixels} px", (50, y_pos + 12),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        
        y_pos += 25
        cv2.rectangle(full_image, (20, y_pos), (40, y_pos + 15), (0, 255, 0), -1)
        cv2.putText(full_image, f"Added: {added_pixels} px", (50, y_pos + 12),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        
        y_pos += 25
        cv2.rectangle(full_image, (20, y_pos), (40, y_pos + 15), (0, 0, 255), -1)
        cv2.putText(full_image, f"Changed: {changed_pixels} px", (50, y_pos + 12),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        
        return full_image
    
    def _create_base_image(self, mask_dto: MaskDTO) -> np.ndarray:
        """ベースのグレースケール画像を作成"""
        # 各IDに異なるグレー値を割り当て
        base_image = np.zeros_like(mask_dto.data, dtype=np.uint8)
        
        for i, obj_id in enumerate(mask_dto.object_ids):
            # 50-200の範囲でグレー値を割り当て
            gray_value = 50 + (i * 150 // max(len(mask_dto.object_ids), 1))
            base_image[mask_dto.data == obj_id] = min(gray_value, 200)
        
        return base_image
    
    def _add_text_overlay(self, image: np.ndarray, title: str, subtitle: str = "") -> None:
        """画像にテキストオーバーレイを追加"""
        height, width = image.shape[:2]
        
        # 半透明の黒背景
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (width, 60), (0, 0, 0), -1)
        cv2.addWeighted(image, 0.7, overlay, 0.3, 0, image)
        
        # タイトル
        cv2.putText(image, title, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        # サブタイトル
        if subtitle:
            cv2.putText(image, subtitle, (10, 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)