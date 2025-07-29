#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenCV Mask Processor Adapter

OpenCVを使用したマスク処理アダプター実装。
IMaskProcessorポートの実装を提供。
"""
from typing import Dict, List, Any, Optional
import numpy as np
import cv2

from domain.ports.secondary import IMaskProcessor
from domain.dto import MaskDTO, BoundingBoxDTO


class OpenCVMaskProcessorAdapter:
    """
    OpenCVを使用したマスク処理アダプター
    
    IMaskProcessorインターフェースの実装。
    モルフォロジー操作やマスク処理をOpenCVで実行。
    """
    
    def dilate(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """膨張処理"""
        # DTOから作成またはdictから作成
        if isinstance(mask_data, dict):
            mask_dto = MaskDTO.from_dict(mask_data)
        else:
            mask_dto = mask_data
        
        # カーネルを作成
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (kernel_size, kernel_size)
        )
        
        # 膨張処理
        dilated = cv2.dilate(mask_dto.data, kernel, iterations=1)
        
        # 新しいDTOを作成
        new_dto = MaskDTO(
            frame_index=mask_dto.frame_index,
            data=dilated,
            width=mask_dto.width,
            height=mask_dto.height,
            object_ids=mask_dto.object_ids,
            classes=mask_dto.classes,
            confidences=mask_dto.confidences,
        )
        
        return new_dto.to_dict()
    
    def erode(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """収縮処理"""
        if isinstance(mask_data, dict):
            mask_dto = MaskDTO.from_dict(mask_data)
        else:
            mask_dto = mask_data
        
        # カーネルを作成
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (kernel_size, kernel_size)
        )
        
        # 収縮処理
        eroded = cv2.erode(mask_dto.data, kernel, iterations=1)
        
        # 新しいDTOを作成
        new_dto = MaskDTO(
            frame_index=mask_dto.frame_index,
            data=eroded,
            width=mask_dto.width,
            height=mask_dto.height,
            object_ids=mask_dto.object_ids,
            classes=mask_dto.classes,
            confidences=mask_dto.confidences,
        )
        
        return new_dto.to_dict()
    
    def open(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """オープン処理（収縮→膨張）"""
        if isinstance(mask_data, dict):
            mask_dto = MaskDTO.from_dict(mask_data)
        else:
            mask_dto = mask_data
        
        # カーネルを作成
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (kernel_size, kernel_size)
        )
        
        # オープン処理
        opened = cv2.morphologyEx(mask_dto.data, cv2.MORPH_OPEN, kernel)
        
        # 新しいDTOを作成
        new_dto = MaskDTO(
            frame_index=mask_dto.frame_index,
            data=opened,
            width=mask_dto.width,
            height=mask_dto.height,
            object_ids=mask_dto.object_ids,
            classes=mask_dto.classes,
            confidences=mask_dto.confidences,
        )
        
        return new_dto.to_dict()
    
    def close(self, mask_data: Dict[str, Any], kernel_size: int) -> Dict[str, Any]:
        """クローズ処理（膨張→収縮）"""
        if isinstance(mask_data, dict):
            mask_dto = MaskDTO.from_dict(mask_data)
        else:
            mask_dto = mask_data
        
        # カーネルを作成
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (kernel_size, kernel_size)
        )
        
        # クローズ処理
        closed = cv2.morphologyEx(mask_dto.data, cv2.MORPH_CLOSE, kernel)
        
        # 新しいDTOを作成
        new_dto = MaskDTO(
            frame_index=mask_dto.frame_index,
            data=closed,
            width=mask_dto.width,
            height=mask_dto.height,
            object_ids=mask_dto.object_ids,
            classes=mask_dto.classes,
            confidences=mask_dto.confidences,
        )
        
        return new_dto.to_dict()
    
    def merge_masks(self, masks: List[Dict[str, Any]], method: str = "union") -> Dict[str, Any]:
        """複数マスクのマージ"""
        if not masks:
            raise ValueError("No masks to merge")
        
        # DTOに変換
        mask_dtos = []
        for mask_data in masks:
            if isinstance(mask_data, dict):
                mask_dtos.append(MaskDTO.from_dict(mask_data))
            else:
                mask_dtos.append(mask_data)
        
        # 最初のマスクを基準にする
        base_dto = mask_dtos[0]
        result = np.zeros_like(base_dto.data)
        
        # マージ処理
        if method == "union":
            # 和集合
            for mask_dto in mask_dtos:
                result = np.maximum(result, mask_dto.data)
        
        elif method == "intersection":
            # 積集合
            result = mask_dtos[0].data.copy()
            for mask_dto in mask_dtos[1:]:
                result = np.minimum(result, mask_dto.data)
        
        elif method == "difference":
            # 差集合（最初のマスクから残りを引く）
            result = mask_dtos[0].data.copy()
            for mask_dto in mask_dtos[1:]:
                result[mask_dto.data > 0] = 0
        
        else:
            raise ValueError(f"Unknown merge method: {method}")
        
        # 全オブジェクトIDとクラスを統合
        all_ids = []
        all_classes = {}
        all_confidences = {}
        
        for mask_dto in mask_dtos:
            all_ids.extend(mask_dto.object_ids)
            all_classes.update(mask_dto.classes)
            all_confidences.update(mask_dto.confidences)
        
        # 重複を除去
        all_ids = list(set(all_ids))
        
        # 新しいDTOを作成
        new_dto = MaskDTO(
            frame_index=base_dto.frame_index,
            data=result.astype(np.uint8),
            width=base_dto.width,
            height=base_dto.height,
            object_ids=all_ids,
            classes=all_classes,
            confidences=all_confidences,
        )
        
        return new_dto.to_dict()
    
    def split_by_id(self, mask_data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """IDごとにマスクを分割"""
        if isinstance(mask_data, dict):
            mask_dto = MaskDTO.from_dict(mask_data)
        else:
            mask_dto = mask_data
        
        result = {}
        
        for obj_id in mask_dto.object_ids:
            # 特定IDのマスクを抽出
            id_mask = (mask_dto.data == obj_id).astype(np.uint8) * obj_id
            
            # 新しいDTOを作成
            id_dto = MaskDTO(
                frame_index=mask_dto.frame_index,
                data=id_mask,
                width=mask_dto.width,
                height=mask_dto.height,
                object_ids=[obj_id],
                classes={obj_id: mask_dto.classes.get(obj_id, "unknown")},
                confidences={obj_id: mask_dto.confidences.get(obj_id, 0.0)},
            )
            
            result[obj_id] = id_dto.to_dict()
        
        return result
    
    def calculate_bbox(self, mask_data: Dict[str, Any], object_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """バウンディングボックスを計算"""
        if isinstance(mask_data, dict):
            mask_dto = MaskDTO.from_dict(mask_data)
        else:
            mask_dto = mask_data
        
        result = []
        
        if object_id is not None:
            # 特定IDのバウンディングボックス
            id_mask = (mask_dto.data == object_id).astype(np.uint8)
            bbox = self._calculate_single_bbox(
                id_mask, object_id, mask_dto.frame_index,
                mask_dto.classes.get(object_id),
                mask_dto.confidences.get(object_id)
            )
            if bbox:
                result.append(bbox)
        else:
            # 全IDのバウンディングボックス
            for obj_id in mask_dto.object_ids:
                id_mask = (mask_dto.data == obj_id).astype(np.uint8)
                bbox = self._calculate_single_bbox(
                    id_mask, obj_id, mask_dto.frame_index,
                    mask_dto.classes.get(obj_id),
                    mask_dto.confidences.get(obj_id)
                )
                if bbox:
                    result.append(bbox)
        
        return result
    
    def _calculate_single_bbox(
        self,
        mask: np.ndarray,
        object_id: int,
        frame_index: int,
        class_name: Optional[str],
        confidence: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """単一マスクのバウンディングボックスを計算"""
        # 輪郭を検出
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return None
        
        # 最大の輪郭を使用
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # BoundingBoxDTOを作成
        bbox_dto = BoundingBoxDTO(
            x=x,
            y=y,
            width=w,
            height=h,
            object_id=object_id,
            frame_index=frame_index,
            class_name=class_name,
            confidence=confidence,
        )
        
        return bbox_dto.to_dict()