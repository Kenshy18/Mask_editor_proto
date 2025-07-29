#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
閾値管理アダプター実装

検出閾値とIDマージ閾値の管理を提供。
"""
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import numpy as np

from domain.dto.mask_dto import MaskDTO
from domain.dto.id_management_dto import (
    ThresholdSettingsDTO, MergeCandidateDTO, ThresholdHistoryDTO
)
from domain.ports.secondary.id_management_ports import IThresholdManager

logger = logging.getLogger(__name__)


class ThresholdManagerAdapter(IThresholdManager):
    """閾値管理アダプター
    
    検出閾値とマージ閾値の管理、履歴記録を実装。
    """
    
    def __init__(self):
        """初期化"""
        self._settings = ThresholdSettingsDTO()
        self._history: List[ThresholdHistoryDTO] = []
        logger.info("ThresholdManager initialized with default settings")
    
    def get_detection_threshold(self) -> float:
        """現在の検出閾値を取得"""
        return self._settings.detection_threshold
    
    def set_detection_threshold(self, threshold: float) -> None:
        """検出閾値を設定"""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Detection threshold must be in [0, 1], got {threshold}")
        
        old_value = self._settings.detection_threshold
        
        # 新しい設定を作成（イミュータブルなので）
        self._settings = ThresholdSettingsDTO(
            detection_threshold=threshold,
            merge_threshold=self._settings.merge_threshold,
            min_pixel_count=self._settings.min_pixel_count,
            max_merge_distance=self._settings.max_merge_distance,
            merge_overlap_ratio=self._settings.merge_overlap_ratio
        )
        
        # 履歴に記録
        history_entry = ThresholdHistoryDTO(
            timestamp=datetime.now(),
            threshold_type="detection",
            old_value=old_value,
            new_value=threshold
        )
        self._history.append(history_entry)
        
        logger.info(f"Detection threshold changed: {old_value} -> {threshold}")
    
    def get_merge_threshold(self) -> float:
        """現在のIDマージ閾値を取得"""
        return self._settings.merge_threshold
    
    def set_merge_threshold(self, threshold: float) -> None:
        """IDマージ閾値を設定"""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Merge threshold must be in [0, 1], got {threshold}")
        
        old_value = self._settings.merge_threshold
        
        # 新しい設定を作成
        self._settings = ThresholdSettingsDTO(
            detection_threshold=self._settings.detection_threshold,
            merge_threshold=threshold,
            min_pixel_count=self._settings.min_pixel_count,
            max_merge_distance=self._settings.max_merge_distance,
            merge_overlap_ratio=self._settings.merge_overlap_ratio
        )
        
        # 履歴に記録
        history_entry = ThresholdHistoryDTO(
            timestamp=datetime.now(),
            threshold_type="merge",
            old_value=old_value,
            new_value=threshold
        )
        self._history.append(history_entry)
        
        logger.info(f"Merge threshold changed: {old_value} -> {threshold}")
    
    def apply_detection_threshold(self, mask_data: Dict[str, any], 
                                confidences: Dict[int, float], 
                                threshold: float) -> Dict[str, any]:
        """検出閾値を適用してマスクをフィルタリング"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # 削除するIDのリストを作成
        ids_to_remove = []
        affected_pixel_count = 0
        
        for obj_id in mask_dto.object_ids:
            confidence = confidences.get(obj_id, 1.0)  # 信頼度がない場合は1.0と仮定
            
            if confidence < threshold:
                ids_to_remove.append(obj_id)
                affected_pixel_count += np.sum(mask_dto.data == obj_id)
        
        if not ids_to_remove:
            logger.info("No IDs removed by threshold")
            return mask_data
        
        # 新しいデータ配列を作成
        new_data = mask_dto.data.copy()
        for obj_id in ids_to_remove:
            new_data[new_data == obj_id] = 0
        
        # 残ったIDのリストを作成
        remaining_ids = [id_ for id_ in mask_dto.object_ids if id_ not in ids_to_remove]
        
        # クラス情報とコンフィデンスを更新
        new_classes = {k: v for k, v in mask_dto.classes.items() if k not in ids_to_remove}
        new_confidences = {k: v for k, v in confidences.items() if k not in ids_to_remove}
        
        logger.info(f"Removed {len(ids_to_remove)} IDs below threshold {threshold}: {ids_to_remove}")
        logger.info(f"Affected pixels: {affected_pixel_count}")
        
        # 履歴を更新（最新のエントリに情報を追加）
        if self._history and self._history[-1].threshold_type == "detection":
            # frozenなので新しいインスタンスを作成
            last_entry = self._history[-1]
            updated_entry = ThresholdHistoryDTO(
                timestamp=last_entry.timestamp,
                threshold_type=last_entry.threshold_type,
                old_value=last_entry.old_value,
                new_value=last_entry.new_value,
                affected_ids=ids_to_remove,
                affected_pixel_count=affected_pixel_count
            )
            self._history[-1] = updated_entry
        
        # 新しいMaskDTOを作成
        new_mask_dto = MaskDTO(
            frame_index=mask_dto.frame_index,
            data=new_data,
            width=mask_dto.width,
            height=mask_dto.height,
            object_ids=remaining_ids,
            classes=new_classes,
            confidences=new_confidences
        )
        
        return new_mask_dto.to_dict()
    
    def suggest_merge_candidates(self, mask_data: Dict[str, any], 
                                threshold: float) -> List[Tuple[int, int, float]]:
        """マージ候補を提案"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        candidates = []
        
        # 全てのIDペアを検討
        for i, id1 in enumerate(mask_dto.object_ids):
            for id2 in mask_dto.object_ids[i+1:]:
                # 各IDのマスクを取得
                mask1 = (mask_dto.data == id1)
                mask2 = (mask_dto.data == id2)
                
                # 重心を計算
                y1, x1 = np.where(mask1)
                y2, x2 = np.where(mask2)
                
                if len(x1) == 0 or len(x2) == 0:
                    continue
                
                center1 = (np.mean(x1), np.mean(y1))
                center2 = (np.mean(x2), np.mean(y2))
                
                # 距離を計算
                distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
                
                # 距離が閾値以内かチェック
                if distance <= self._settings.max_merge_distance:
                    # 重なり比率を計算
                    intersection = np.logical_and(mask1, mask2)
                    union = np.logical_or(mask1, mask2)
                    
                    union_area = np.sum(union)
                    if union_area > 0:
                        overlap_ratio = np.sum(intersection) / union_area
                    else:
                        overlap_ratio = 0.0
                    
                    # サイズ比率を計算
                    size1 = np.sum(mask1)
                    size2 = np.sum(mask2)
                    size_ratio = min(size1, size2) / max(size1, size2) if max(size1, size2) > 0 else 0.0
                    
                    # 類似度スコアを計算（距離と重なりの組み合わせ）
                    normalized_distance = 1.0 - (distance / self._settings.max_merge_distance)
                    similarity_score = (normalized_distance * 0.5 + overlap_ratio * 0.3 + size_ratio * 0.2)
                    
                    # 閾値以上の場合は候補に追加
                    if similarity_score >= threshold:
                        # 詳細な候補DTOを作成
                        candidate_dto = MergeCandidateDTO(
                            id1=id1,
                            id2=id2,
                            similarity_score=similarity_score,
                            distance=distance,
                            overlap_ratio=overlap_ratio,
                            size_ratio=size_ratio,
                            confidence_diff=abs(
                                mask_dto.confidences.get(id1, 0) - 
                                mask_dto.confidences.get(id2, 0)
                            ) if mask_dto.confidences else None,
                            reason=self._determine_merge_reason(distance, overlap_ratio, similarity_score)
                        )
                        
                        candidates.append((id1, id2, similarity_score))
                        
                        logger.debug(f"Merge candidate: ID {id1} and {id2}, score: {similarity_score:.3f}")
        
        # スコアの降順でソート
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Found {len(candidates)} merge candidates with threshold {threshold}")
        
        return candidates
    
    def get_threshold_history(self) -> List[Dict[str, any]]:
        """閾値変更履歴を取得"""
        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "threshold_type": entry.threshold_type,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "affected_ids": entry.affected_ids,
                "affected_pixel_count": entry.affected_pixel_count
            }
            for entry in self._history
        ]
    
    def get_settings(self) -> ThresholdSettingsDTO:
        """現在の設定を取得"""
        return self._settings
    
    def update_settings(self, settings: ThresholdSettingsDTO) -> None:
        """設定を更新"""
        old_detection = self._settings.detection_threshold
        old_merge = self._settings.merge_threshold
        
        self._settings = settings
        
        # 検出閾値が変更された場合
        if old_detection != settings.detection_threshold:
            history_entry = ThresholdHistoryDTO(
                timestamp=datetime.now(),
                threshold_type="detection",
                old_value=old_detection,
                new_value=settings.detection_threshold
            )
            self._history.append(history_entry)
        
        # マージ閾値が変更された場合
        if old_merge != settings.merge_threshold:
            history_entry = ThresholdHistoryDTO(
                timestamp=datetime.now(),
                threshold_type="merge",
                old_value=old_merge,
                new_value=settings.merge_threshold
            )
            self._history.append(history_entry)
        
        logger.info("Threshold settings updated")
    
    def _determine_merge_reason(self, distance: float, overlap_ratio: float, 
                               similarity_score: float) -> str:
        """マージ推奨理由を判定"""
        reasons = []
        
        if distance < 20.0:
            reasons.append("close_proximity")
        
        if overlap_ratio > 0.5:
            reasons.append("high_overlap")
        
        if similarity_score > 0.8:
            reasons.append("high_similarity")
        
        return ", ".join(reasons) if reasons else "general_similarity"