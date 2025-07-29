#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ID管理アダプター実装

マスクのID管理機能を提供。
"""
import logging
from typing import List, Dict, Set, Tuple, Optional
import numpy as np
from dataclasses import replace

from domain.dto.mask_dto import MaskDTO
from domain.dto.id_management_dto import IDStatisticsDTO
from domain.ports.secondary.id_management_ports import IIDManager

logger = logging.getLogger(__name__)


class IDManagerAdapter(IIDManager):
    """ID管理アダプター
    
    マスクのID削除、マージ、統計情報取得を実装。
    """
    
    def delete_ids(self, mask_data: Dict[str, any], target_ids: List[int]) -> Dict[str, any]:
        """指定IDを削除"""
        # MaskDTOに変換
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # コピーを作成
        new_data = mask_dto.data.copy()
        
        # 指定IDのピクセルを0（背景）に設定
        for target_id in target_ids:
            if target_id in mask_dto.object_ids:
                new_data[new_data == target_id] = 0
                logger.info(f"Deleted ID {target_id} from mask")
        
        # 新しいオブジェクトIDリストを作成
        remaining_ids = np.unique(new_data)
        remaining_ids = remaining_ids[remaining_ids > 0].tolist()
        
        # 削除されたIDの情報も削除
        new_classes = {k: v for k, v in mask_dto.classes.items() if k not in target_ids}
        new_confidences = {k: v for k, v in mask_dto.confidences.items() if k not in target_ids}
        
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
    
    def delete_range(self, mask_data: Dict[str, any], id_range: Tuple[int, int]) -> Dict[str, any]:
        """ID範囲指定で削除"""
        start, end = id_range
        if start > end:
            raise ValueError(f"Invalid range: start ({start}) > end ({end})")
        
        # 範囲内のIDをリスト化
        mask_dto = MaskDTO.from_dict(mask_data)
        target_ids = [id_ for id_ in mask_dto.object_ids if start <= id_ <= end]
        
        logger.info(f"Deleting IDs in range [{start}, {end}]: {target_ids}")
        
        # delete_idsを使用
        return self.delete_ids(mask_data, target_ids)
    
    def delete_all(self, mask_data: Dict[str, any]) -> Dict[str, any]:
        """全IDを削除（マスクをクリア）"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # ゼロで埋めた新しいデータ配列を作成
        new_data = np.zeros_like(mask_dto.data)
        
        logger.info("Cleared all IDs from mask")
        
        # 新しいMaskDTOを作成
        new_mask_dto = MaskDTO(
            frame_index=mask_dto.frame_index,
            data=new_data,
            width=mask_dto.width,
            height=mask_dto.height,
            object_ids=[],
            classes={},
            confidences={}
        )
        
        return new_mask_dto.to_dict()
    
    def merge_ids(self, mask_data: Dict[str, any], source_ids: List[int], target_id: int) -> Dict[str, any]:
        """複数のIDを単一IDにマージ"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # ターゲットIDが存在しない場合はエラー
        if target_id not in mask_dto.object_ids and target_id not in source_ids:
            raise ValueError(f"Target ID {target_id} not found in mask")
        
        # コピーを作成
        new_data = mask_dto.data.copy()
        
        # ソースIDのピクセルをターゲットIDに変更
        for source_id in source_ids:
            if source_id != target_id and source_id in mask_dto.object_ids:
                new_data[new_data == source_id] = target_id
                logger.info(f"Merged ID {source_id} into ID {target_id}")
        
        # 新しいオブジェクトIDリストを作成
        remaining_ids = np.unique(new_data)
        remaining_ids = remaining_ids[remaining_ids > 0].tolist()
        
        # クラス情報とコンフィデンスを更新
        # ターゲットIDの情報を保持し、ソースIDの情報を削除
        new_classes = mask_dto.classes.copy()
        new_confidences = mask_dto.confidences.copy()
        
        for source_id in source_ids:
            if source_id != target_id:
                new_classes.pop(source_id, None)
                new_confidences.pop(source_id, None)
        
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
    
    def renumber_ids(self, mask_data: Dict[str, any]) -> Dict[str, any]:
        """IDを連番に振り直し"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        # 現在のユニークIDを取得（0を除く）
        unique_ids = np.unique(mask_dto.data)
        unique_ids = unique_ids[unique_ids > 0]
        
        if len(unique_ids) == 0:
            # IDがない場合はそのまま返す
            return mask_data
        
        # ID変換マップを作成（古いID -> 新しいID）
        id_map = {old_id: new_id for new_id, old_id in enumerate(unique_ids, start=1)}
        id_map[0] = 0  # 背景は0のまま
        
        # 新しいデータ配列を作成
        new_data = np.zeros_like(mask_dto.data)
        for old_id, new_id in id_map.items():
            new_data[mask_dto.data == old_id] = new_id
        
        # クラス情報とコンフィデンスも更新
        new_classes = {}
        new_confidences = {}
        
        for old_id, new_id in id_map.items():
            if old_id > 0 and old_id in mask_dto.classes:
                new_classes[new_id] = mask_dto.classes[old_id]
            if old_id > 0 and old_id in mask_dto.confidences:
                new_confidences[new_id] = mask_dto.confidences[old_id]
        
        logger.info(f"Renumbered IDs: {dict(id_map)}")
        
        # 新しいMaskDTOを作成
        new_mask_dto = MaskDTO(
            frame_index=mask_dto.frame_index,
            data=new_data,
            width=mask_dto.width,
            height=mask_dto.height,
            object_ids=list(range(1, len(unique_ids) + 1)),
            classes=new_classes,
            confidences=new_confidences
        )
        
        return new_mask_dto.to_dict()
    
    def get_id_statistics(self, mask_data: Dict[str, any]) -> Dict[int, Dict[str, any]]:
        """ID別の統計情報を取得"""
        mask_dto = MaskDTO.from_dict(mask_data)
        
        stats = {}
        total_pixels = mask_dto.width * mask_dto.height
        
        for obj_id in mask_dto.object_ids:
            # IDのマスクを取得
            id_mask = (mask_dto.data == obj_id)
            
            if not np.any(id_mask):
                continue
            
            # ピクセル数
            pixel_count = np.sum(id_mask)
            
            # バウンディングボックス
            y_indices, x_indices = np.where(id_mask)
            x1, y1 = int(np.min(x_indices)), int(np.min(y_indices))
            x2, y2 = int(np.max(x_indices)), int(np.max(y_indices))
            
            # 重心
            center_x = float(np.mean(x_indices))
            center_y = float(np.mean(y_indices))
            
            # 統計情報DTOを作成
            stat_dto = IDStatisticsDTO(
                id=obj_id,
                pixel_count=pixel_count,
                bbox=(x1, y1, x2, y2),
                center=(center_x, center_y),
                area_ratio=pixel_count / total_pixels,
                confidence=mask_dto.confidences.get(obj_id),
                class_name=mask_dto.classes.get(obj_id)
            )
            
            stats[obj_id] = {
                "id": stat_dto.id,
                "pixel_count": stat_dto.pixel_count,
                "bbox": stat_dto.bbox,
                "center": stat_dto.center,
                "area_ratio": stat_dto.area_ratio,
                "confidence": stat_dto.confidence,
                "class_name": stat_dto.class_name
            }
        
        return stats
    
    def _calculate_overlap(self, mask1: np.ndarray, mask2: np.ndarray) -> float:
        """2つのマスクの重なり比率を計算"""
        intersection = np.logical_and(mask1, mask2)
        union = np.logical_or(mask1, mask2)
        
        union_area = np.sum(union)
        if union_area == 0:
            return 0.0
        
        return np.sum(intersection) / union_area
    
    def _calculate_distance(self, center1: Tuple[float, float], center2: Tuple[float, float]) -> float:
        """2点間の距離を計算"""
        return np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)