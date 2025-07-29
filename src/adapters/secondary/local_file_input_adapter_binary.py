#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バイナリマスク対応のローカルファイル入力アダプター

test_inputディレクトリのバイナリマスク（0と255）形式に対応
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
import numpy as np
from PIL import Image

from domain.ports.secondary.input_data_ports import IInputDataSource
from domain.dto.detection_dto import DetectionDTO
from domain.dto.mask_dto import MaskDTO


logger = logging.getLogger(__name__)


class BinaryMaskLocalFileInputAdapter(IInputDataSource):
    """
    バイナリマスク対応のローカルファイル入力アダプター
    
    マスクファイルが0と255の二値画像の場合に使用。
    255の領域を検出オブジェクトとして扱い、track_idと対応付ける。
    """
    
    def __init__(self):
        self.base_path: Optional[Path] = None
        self.video_path: Optional[Path] = None
        self.detections_path: Optional[Path] = None
        self.mask_dir: Optional[Path] = None
        self.detections_data: Optional[Dict[str, Any]] = None
        self._is_initialized = False
    
    def set_base_path(self, base_path: str) -> None:
        """ベースパスを設定"""
        self.base_path = Path(base_path)
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """データソースを初期化"""
        # ベースパス設定
        self.base_path = Path(config.get("base_path", "test_input"))
        
        # 各ファイルパス設定
        video_file = config.get("video_file", "CHUC_TEST1.mp4")
        self.video_path = self.base_path / video_file
        
        detections_file = config.get("detections_file", "detections_genitile.json")
        self.detections_path = self.base_path / detections_file
        
        mask_dir = config.get("mask_directory", "filtered")
        self.mask_dir = self.base_path / mask_dir
        
        # 検証
        self._validate_paths()
        
        # 検出情報読み込み
        self._load_detections()
        
        self._is_initialized = True
        logger.info(f"BinaryMaskLocalFileInputAdapter initialized with base_path: {self.base_path}")
    
    def _validate_paths(self) -> None:
        """パスの存在を検証"""
        if not self.base_path.exists():
            raise FileNotFoundError(f"Base path not found: {self.base_path}")
        
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        
        if not self.detections_path.exists():
            raise FileNotFoundError(f"Detections file not found: {self.detections_path}")
        
        if not self.mask_dir.exists():
            raise FileNotFoundError(f"Mask directory not found: {self.mask_dir}")
    
    def _load_detections(self) -> None:
        """検出情報JSONを読み込む"""
        with open(self.detections_path, 'r', encoding='utf-8') as f:
            self.detections_data = json.load(f)
        
        logger.info(f"Loaded detections: {len(self.detections_data.get('frames', {}))} frames")
    
    def get_video_path(self) -> Path:
        """動画ファイルパスを取得"""
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        return self.video_path
    
    def get_video_metadata(self) -> Dict[str, Any]:
        """動画メタデータを取得"""
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        metadata = self.detections_data.get("metadata", {})
        return {
            "width": metadata.get("video_width", 1920),
            "height": metadata.get("video_height", 1080),
            "fps": metadata.get("fps", 30.0),
            "total_frames": metadata.get("total_frames", 0),
            "input_video": str(self.video_path),
            "confidence_threshold": metadata.get("confidence_threshold", 0.4),
            "id_mappings": metadata.get("id_mappings", {})
        }
    
    def get_detections(self, frame_index: int) -> List[Dict[str, Any]]:
        """指定フレームの検出情報を取得"""
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        # フレーム番号を文字列キーに変換
        frame_key = str(frame_index)
        frame_detections = self.detections_data.get("frames", {}).get(frame_key, [])
        
        # DetectionDTOのリストに変換
        detections = []
        for det in frame_detections:
            try:
                detection = DetectionDTO(
                    frame_index=frame_index,
                    track_id=det["track_id"],
                    class_id=det["class"]["id"],
                    class_name=det["class"]["name"],
                    confidence=det["confidence"],
                    x1=det["bounding_box"]["x1"],
                    y1=det["bounding_box"]["y1"],
                    x2=det["bounding_box"]["x2"],
                    y2=det["bounding_box"]["y2"],
                    attributes=det.get("attributes", {})
                )
                detections.append(detection.to_dict())
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid detection data at frame {frame_index}: {e}")
                continue
        
        return detections
    
    def get_mask(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """指定フレームのマスクを取得（バイナリマスク対応）"""
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        # マスクファイルパス
        mask_filename = f"mask_filtered_{frame_index:06d}.png"
        mask_path = self.mask_dir / mask_filename
        
        if not mask_path.exists():
            return None
        
        try:
            # マスク画像読み込み（グレースケール）
            mask_image = Image.open(mask_path).convert('L')
            mask_data = np.array(mask_image, dtype=np.uint8)
            
            # バイナリマスクの処理
            # 255の値を持つピクセルがある場合、それを対応するtrack_idに変換
            has_mask = np.any(mask_data > 0)
            
            if has_mask:
                # このフレームの検出情報を取得
                detections = self.get_detections(frame_index)
                
                if detections:
                    # 最初の検出のtrack_idを使用（通常は1つの検出のみ）
                    track_id = detections[0]["track_id"]
                    
                    # 255の値をtrack_idに変換（0は背景のまま）
                    converted_mask = np.where(mask_data > 0, track_id + 1, 0).astype(np.uint8)
                    
                    # オブジェクトIDリスト
                    object_ids = [track_id + 1]  # マスク内では1から始まるIDを使用
                    
                    # クラス名と信頼度のマッピング
                    classes = {track_id + 1: detections[0]["class"]["name"]}
                    confidences = {track_id + 1: detections[0]["confidence"]}
                else:
                    # 検出がない場合は、マスクをそのまま使用（255を1に変換）
                    converted_mask = np.where(mask_data > 0, 1, 0).astype(np.uint8)
                    object_ids = [1]
                    classes = {1: "unknown"}
                    confidences = {1: 1.0}
            else:
                # マスクが空の場合
                converted_mask = mask_data
                object_ids = []
                classes = {}
                confidences = {}
            
            # MaskDTOを作成
            mask_dto = MaskDTO(
                frame_index=frame_index,
                data=converted_mask,
                width=mask_data.shape[1],
                height=mask_data.shape[0],
                object_ids=object_ids,
                classes=classes,
                confidences=confidences
            )
            
            return mask_dto.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to load mask for frame {frame_index}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_frame_indices(self) -> List[int]:
        """利用可能なフレームインデックスのリストを取得"""
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        # 検出情報のフレーム番号を取得
        frame_keys = self.detections_data.get("frames", {}).keys()
        return sorted([int(key) for key in frame_keys])
    
    def iterate_frames(self, start: int = 0, end: Optional[int] = None) -> Iterator[tuple[int, List[Dict[str, Any]], Optional[Dict[str, Any]]]]:
        """フレームを順次イテレート"""
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        frame_indices = self.get_frame_indices()
        
        # 範囲を限定
        if end is not None:
            frame_indices = [idx for idx in frame_indices if start <= idx < end]
        else:
            frame_indices = [idx for idx in frame_indices if idx >= start]
        
        for frame_index in frame_indices:
            detections = self.get_detections(frame_index)
            mask = self.get_mask(frame_index)
            yield frame_index, detections, mask
    
    def get_frame_count(self) -> int:
        """総フレーム数を取得"""
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        metadata = self.detections_data.get("metadata", {})
        return metadata.get("total_frames", 0)