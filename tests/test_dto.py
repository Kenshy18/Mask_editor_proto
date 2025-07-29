#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DTOクラスのテスト
"""
import pytest
import numpy as np
from datetime import datetime

from domain.dto import (
    FrameDTO, MaskDTO, VideoMetadataDTO, BoundingBoxDTO,
    AlertDTO, AlertLevel, AlertType
)


class TestFrameDTO:
    """FrameDTOのテスト"""
    
    def test_frame_dto_creation(self):
        """正常なFrameDTO作成"""
        data = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = FrameDTO(
            index=0,
            pts=0,
            dts=None,
            data=data,
            width=640,
            height=480,
            timecode="00:00:00:00"
        )
        
        assert frame.index == 0
        assert frame.pts == 0
        assert frame.dts is None
        assert frame.width == 640
        assert frame.height == 480
        assert frame.timecode == "00:00:00:00"
    
    def test_frame_dto_validation(self):
        """FrameDTOのバリデーション"""
        # 負のインデックス
        with pytest.raises(ValueError):
            FrameDTO(
                index=-1, pts=0, dts=None,
                data=np.zeros((480, 640, 3), dtype=np.uint8),
                width=640, height=480
            )
        
        # 不正なデータ形状
        with pytest.raises(ValueError):
            FrameDTO(
                index=0, pts=0, dts=None,
                data=np.zeros((480, 640), dtype=np.uint8),  # 2D array
                width=640, height=480
            )
        
        # 不正なデータ型
        with pytest.raises(ValueError):
            FrameDTO(
                index=0, pts=0, dts=None,
                data=np.zeros((480, 640, 3), dtype=np.float32),  # float32
                width=640, height=480
            )
    
    def test_frame_dto_serialization(self):
        """FrameDTOのシリアライズ/デシリアライズ"""
        data = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        frame = FrameDTO(
            index=10, pts=1000, dts=900,
            data=data, width=640, height=480
        )
        
        # 辞書に変換
        frame_dict = frame.to_dict()
        
        # 辞書から復元
        restored = FrameDTO.from_dict(frame_dict)
        
        assert restored.index == frame.index
        assert restored.pts == frame.pts
        assert restored.dts == frame.dts
        assert np.array_equal(restored.data, frame.data)


class TestMaskDTO:
    """MaskDTOのテスト"""
    
    def test_mask_dto_creation(self):
        """正常なMaskDTO作成"""
        data = np.zeros((480, 640), dtype=np.uint8)
        data[100:200, 100:200] = 1  # ID=1の領域
        
        mask = MaskDTO(
            frame_index=0,
            data=data,
            width=640,
            height=480,
            object_ids=[1],
            classes={1: "person"},
            confidences={1: 0.95}
        )
        
        assert mask.frame_index == 0
        assert mask.width == 640
        assert mask.height == 480
        assert mask.object_ids == [1]
        assert mask.classes[1] == "person"
        assert mask.confidences[1] == 0.95
    
    def test_mask_dto_validation(self):
        """MaskDTOのバリデーション"""
        # 信頼度が範囲外
        with pytest.raises(ValueError):
            MaskDTO(
                frame_index=0,
                data=np.zeros((480, 640), dtype=np.uint8),
                width=640, height=480,
                object_ids=[1],
                classes={1: "person"},
                confidences={1: 1.5}  # > 1.0
            )
    
    def test_mask_dto_methods(self):
        """MaskDTOのメソッド"""
        data = np.zeros((480, 640), dtype=np.uint8)
        data[100:200, 100:200] = 1
        data[200:300, 200:300] = 2
        
        mask = MaskDTO(
            frame_index=0,
            data=data,
            width=640, height=480,
            object_ids=[1, 2],
            classes={1: "person", 2: "car"},
            confidences={1: 0.95, 2: 0.85}
        )
        
        # 特定IDのマスク取得
        mask1 = mask.get_mask_for_id(1)
        assert mask1[150, 150] == 255
        assert mask1[250, 250] == 0
        
        # ピクセル数カウント
        assert mask.count_pixels(1) == 10000  # 100x100
        assert mask.count_pixels(2) == 10000  # 100x100
        assert mask.count_pixels() == 20000  # 全体


class TestVideoMetadataDTO:
    """VideoMetadataDTOのテスト"""
    
    def test_video_metadata_dto_creation(self):
        """正常なVideoMetadataDTO作成"""
        metadata = VideoMetadataDTO(
            width=1920,
            height=1080,
            fps=29.97,
            frame_count=1000,
            duration=33.367,
            video_codec="h264",
            audio_codec="aac",
            video_bit_rate=5000000,
            has_audio=True,
            audio_channels=2,
            audio_sample_rate=48000
        )
        
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.fps == 29.97
        assert metadata.resolution_string == "1920x1080"
        assert metadata.aspect_ratio == 16/9
    
    def test_video_metadata_dto_validation(self):
        """VideoMetadataDTOのバリデーション"""
        # 負の幅
        with pytest.raises(ValueError):
            VideoMetadataDTO(
                width=-1920, height=1080, fps=30,
                frame_count=1000, duration=33.33,
                video_codec="h264"
            )
        
        # オーディオ情報の不整合
        with pytest.raises(ValueError):
            VideoMetadataDTO(
                width=1920, height=1080, fps=30,
                frame_count=1000, duration=33.33,
                video_codec="h264",
                has_audio=True,  # オーディオありだが
                audio_channels=None  # チャンネル数がない
            )


class TestBoundingBoxDTO:
    """BoundingBoxDTOのテスト"""
    
    def test_bounding_box_dto_creation(self):
        """正常なBoundingBoxDTO作成"""
        bbox = BoundingBoxDTO(
            x=100, y=200, width=300, height=400,
            object_id=1, frame_index=0,
            class_name="person", confidence=0.95
        )
        
        assert bbox.x == 100
        assert bbox.y == 200
        assert bbox.width == 300
        assert bbox.height == 400
        assert bbox.x2 == 400
        assert bbox.y2 == 600
        assert bbox.center_x == 250
        assert bbox.center_y == 400
        assert bbox.area == 120000
    
    def test_bounding_box_dto_conversions(self):
        """BoundingBoxDTOの形式変換"""
        bbox = BoundingBoxDTO(
            x=100, y=200, width=300, height=400,
            object_id=1, frame_index=0
        )
        
        # xyxy形式
        x1, y1, x2, y2 = bbox.to_xyxy()
        assert (x1, y1, x2, y2) == (100, 200, 400, 600)
        
        # cxcywh形式
        cx, cy, w, h = bbox.to_cxcywh()
        assert (cx, cy, w, h) == (250, 400, 300, 400)
    
    def test_bounding_box_dto_methods(self):
        """BoundingBoxDTOのメソッド"""
        bbox1 = BoundingBoxDTO(
            x=100, y=100, width=200, height=200,
            object_id=1, frame_index=0
        )
        bbox2 = BoundingBoxDTO(
            x=200, y=200, width=200, height=200,
            object_id=2, frame_index=0
        )
        
        # 点の包含判定
        assert bbox1.contains_point(150, 150)
        assert not bbox1.contains_point(350, 350)
        
        # 交差領域
        intersection = bbox1.intersection(bbox2)
        assert intersection is not None
        assert intersection.x == 200
        assert intersection.y == 200
        assert intersection.width == 100
        assert intersection.height == 100
        
        # IoU計算
        iou = bbox1.iou(bbox2)
        assert 0.14 < iou < 0.15  # 約1/7


class TestAlertDTO:
    """AlertDTOのテスト"""
    
    def test_alert_dto_creation(self):
        """正常なAlertDTO作成"""
        alert = AlertDTO(
            alert_id="alert_001",
            alert_type=AlertType.AI_OUTPUT,
            alert_level=AlertLevel.DETAILED,
            frame_start=100,
            frame_end=200,
            object_ids=[1, 2],
            title="マスク品質低下",
            description="フレーム100-200でマスクの品質が低下しています",
            confidence=0.8
        )
        
        assert alert.alert_id == "alert_001"
        assert alert.alert_type == AlertType.AI_OUTPUT
        assert alert.alert_level == AlertLevel.DETAILED
        assert alert.frame_count == 101
        assert alert.severity_score == 0.67
    
    def test_alert_dto_methods(self):
        """AlertDTOのメソッド"""
        alert1 = AlertDTO(
            alert_id="alert_001",
            alert_type=AlertType.AI_OUTPUT,
            alert_level=AlertLevel.NORMAL,
            frame_start=100,
            frame_end=200
        )
        alert2 = AlertDTO(
            alert_id="alert_002",
            alert_type=AlertType.HAZARD_DETECTION,
            alert_level=AlertLevel.CRITICAL,
            frame_start=150,
            frame_end=250
        )
        
        # フレーム範囲判定
        assert alert1.is_in_frame_range(150)
        assert not alert1.is_in_frame_range(250)
        
        # 重複判定
        assert alert1.overlaps_with(alert2)
    
    def test_alert_dto_serialization(self):
        """AlertDTOのシリアライズ/デシリアライズ"""
        alert = AlertDTO(
            alert_id="alert_001",
            alert_type=AlertType.AI_OUTPUT,
            alert_level=AlertLevel.CRITICAL,
            frame_start=100,
            frame_end=200,
            created_at=datetime.now()
        )
        
        # 辞書に変換
        alert_dict = alert.to_dict()
        
        # 辞書から復元
        restored = AlertDTO.from_dict(alert_dict)
        
        assert restored.alert_id == alert.alert_id
        assert restored.alert_type == alert.alert_type
        assert restored.alert_level == alert.alert_level