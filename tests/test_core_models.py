#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コアデータモデルのテスト

要件定義書の仕様に基づいてデータモデルの動作を検証します。
"""
import json
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from src.core.models import (
    AlertLevel,
    AlertTag,
    BoundingBox,
    ChromaSubsampling,
    ColorSpace,
    EditHistory,
    FieldOrder,
    Frame,
    Mask,
    OpticalFlow,
    Project,
    Timeline,
    TransferCharacteristic,
    create_test_frame,
    create_test_mask,
)


class TestEnums:
    """Enum定義のテスト"""
    
    def test_color_space_from_string(self):
        """文字列からColorSpaceへの変換テスト"""
        assert ColorSpace.from_string("bt709") == ColorSpace.BT709
        assert ColorSpace.from_string("BT709") == ColorSpace.BT709
        assert ColorSpace.from_string("bt2020") == ColorSpace.BT2020
        assert ColorSpace.from_string("unknown") == ColorSpace.BT709  # デフォルト
    
    def test_chroma_subsampling_properties(self):
        """ChromaSubsamplingのプロパティテスト"""
        assert ChromaSubsampling.YUV420.chroma_width_divisor == 2
        assert ChromaSubsampling.YUV420.chroma_height_divisor == 2
        assert ChromaSubsampling.YUV422.chroma_width_divisor == 2
        assert ChromaSubsampling.YUV422.chroma_height_divisor == 1
        assert ChromaSubsampling.YUV444.chroma_width_divisor == 1
        assert ChromaSubsampling.YUV444.chroma_height_divisor == 1
    
    def test_alert_level_properties(self):
        """AlertLevelのプロパティテスト"""
        assert AlertLevel.PERFECT.priority == 0
        assert AlertLevel.REQUIRED.priority == 3
        assert AlertLevel.PERFECT.color == "#00FF00"
        assert AlertLevel.REQUIRED.color == "#FF0000"


class TestFrame:
    """Frameクラスのテスト"""
    
    def test_frame_creation(self):
        """Frame作成の基本テスト"""
        data = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame = Frame(
            data=data,
            pts=1000000,
            timecode="00:00:01:00"
        )
        
        assert frame.pts == 1000000
        assert frame.timecode == "00:00:01:00"
        assert frame.colorspace == ColorSpace.BT709
        assert frame.bit_depth == 8
        assert frame.width == 1920
        assert frame.height == 1080
        assert frame.channels == 3
    
    def test_frame_validation(self):
        """Frame検証のテスト"""
        # 不正な次元数
        with pytest.raises(ValueError, match="Frame data must be 2D or 3D"):
            Frame(data=np.zeros((10,)), pts=0)
        
        # 不正なビット深度
        with pytest.raises(ValueError, match="Unsupported bit depth"):
            Frame(data=np.zeros((100, 100)), pts=0, bit_depth=7)
        
        # DTS > PTS
        with pytest.raises(ValueError, match="DTS cannot be greater than PTS"):
            Frame(data=np.zeros((100, 100)), pts=1000, dts=2000)
    
    def test_frame_properties(self):
        """Frameプロパティのテスト"""
        frame = create_test_frame()
        
        assert frame.shape == (1080, 1920, 3)
        assert frame.pts_seconds == 0.0
        
        # 2Dフレーム
        frame_2d = Frame(data=np.zeros((480, 640), dtype=np.uint8), pts=1_000_000)
        assert frame_2d.shape == (480, 640, 1)
        assert frame_2d.pts_seconds == 1.0
    
    def test_frame_serialization(self):
        """Frameシリアライズのテスト"""
        frame = create_test_frame()
        data = frame.to_dict()
        
        assert data["pts"] == frame.pts
        assert data["colorspace"] == "bt709"
        assert data["shape"] == (1080, 1920, 3)
        
        # JSONシリアライズ可能か確認
        json_str = json.dumps(data)
        assert isinstance(json_str, str)
    
    def test_frame_hash(self):
        """Frameハッシュ計算のテスト"""
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        # 同じデータは同じハッシュ
        assert frame1.calculate_hash() == frame2.calculate_hash()
        
        # データ変更でハッシュ変更
        frame2.data[0, 0, 0] = 255
        assert frame1.calculate_hash() != frame2.calculate_hash()


class TestMask:
    """Maskクラスのテスト"""
    
    def test_mask_creation(self):
        """Mask作成の基本テスト"""
        data = np.zeros((1080, 1920), dtype=np.uint8)
        mask = Mask(
            data=data,
            id=1,
            class_name="genital",
            confidence=0.95,
            frame_index=0
        )
        
        assert mask.id == 1
        assert mask.class_name == "genital"
        assert mask.confidence == 0.95
        assert mask.shape == (1080, 1920)
        assert mask.area == 0
    
    def test_mask_validation(self):
        """Mask検証のテスト"""
        # 不正な次元数
        with pytest.raises(ValueError, match="Mask data must be 2D"):
            Mask(data=np.zeros((10, 10, 3)), id=1, class_name="test", 
                 confidence=0.5, frame_index=0)
        
        # 不正な信頼度
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            Mask(data=np.zeros((10, 10)), id=1, class_name="test",
                 confidence=1.5, frame_index=0)
    
    def test_mask_properties(self):
        """Maskプロパティのテスト"""
        mask = create_test_mask(width=100, height=100)
        
        # 面積計算
        expected_area = 50 * 50  # 中央の矩形
        assert mask.area == expected_area
        
        # バウンディングボックス
        bbox = mask.bbox
        assert bbox == (25, 25, 74, 74)  # 0-indexedなので74
        
        # 空のマスク
        empty_mask = Mask(
            data=np.zeros((100, 100), dtype=np.uint8),
            id=2, class_name="empty", confidence=0.5, frame_index=0
        )
        assert empty_mask.area == 0
        assert empty_mask.bbox is None
    
    def test_mask_io(self):
        """MaskのI/Oテスト"""
        mask = create_test_mask()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # NPY保存/読み込み
            npy_path = tmpdir / "mask.npy"
            mask.to_npy(npy_path)
            loaded_mask = Mask.from_npy(
                npy_path, id=mask.id, class_name=mask.class_name,
                confidence=mask.confidence, frame_index=mask.frame_index
            )
            np.testing.assert_array_equal(mask.data, loaded_mask.data)
            
            # PNG保存/読み込み
            png_path = tmpdir / "mask.png"
            mask.to_png(png_path)
            loaded_mask_png = Mask.from_png(
                png_path, id=mask.id, class_name=mask.class_name,
                confidence=mask.confidence, frame_index=mask.frame_index
            )
            # PNGは2値化されるので完全一致はしない可能性がある
            assert loaded_mask_png.shape == mask.shape
    
    def test_mask_serialization(self):
        """Maskシリアライズのテスト"""
        mask = create_test_mask(width=100, height=100)
        data = mask.to_dict()
        
        assert data["id"] == mask.id
        assert data["area"] == mask.area
        assert data["bbox"] == (25, 25, 74, 74)
        
        # JSONシリアライズ可能か確認
        json_str = json.dumps(data)
        assert isinstance(json_str, str)


class TestBoundingBox:
    """BoundingBoxクラスのテスト"""
    
    def test_bbox_creation(self):
        """BoundingBox作成の基本テスト"""
        bbox = BoundingBox(
            x=100, y=200, width=50, height=80,
            id=1, score=0.95, class_name="genital", frame_index=0
        )
        
        assert bbox.x == 100
        assert bbox.y == 200
        assert bbox.width == 50
        assert bbox.height == 80
        assert bbox.score == 0.95
    
    def test_bbox_validation(self):
        """BoundingBox検証のテスト"""
        # 不正な幅/高さ
        with pytest.raises(ValueError, match="Width and height must be positive"):
            BoundingBox(x=0, y=0, width=0, height=10, id=1, score=0.5,
                       class_name="test", frame_index=0)
        
        # 不正なスコア
        with pytest.raises(ValueError, match="Score must be between 0 and 1"):
            BoundingBox(x=0, y=0, width=10, height=10, id=1, score=1.5,
                       class_name="test", frame_index=0)
    
    def test_bbox_properties(self):
        """BoundingBoxプロパティのテスト"""
        bbox = BoundingBox(
            x=100, y=200, width=50, height=80,
            id=1, score=0.95, class_name="test", frame_index=0
        )
        
        assert bbox.x2 == 150
        assert bbox.y2 == 280
        assert bbox.center_x == 125
        assert bbox.center_y == 240
        assert bbox.area == 4000
    
    def test_bbox_conversions(self):
        """BoundingBox形式変換のテスト"""
        bbox = BoundingBox(
            x=100, y=200, width=50, height=80,
            id=1, score=0.95, class_name="test", frame_index=0
        )
        
        # 各種形式への変換
        assert bbox.to_xyxy() == (100, 200, 150, 280)
        assert bbox.to_xywh() == (100, 200, 50, 80)
        assert bbox.to_cxcywh() == (125, 240, 50, 80)
        
        # xyxyからの作成
        bbox2 = BoundingBox.from_xyxy(
            100, 200, 150, 280,
            id=2, score=0.9, class_name="test2", frame_index=1
        )
        assert bbox2.width == 50
        assert bbox2.height == 80
    
    def test_bbox_iou(self):
        """IoU計算のテスト"""
        bbox1 = BoundingBox(x=0, y=0, width=100, height=100,
                           id=1, score=0.9, class_name="test", frame_index=0)
        bbox2 = BoundingBox(x=50, y=50, width=100, height=100,
                           id=2, score=0.9, class_name="test", frame_index=0)
        
        # 部分的な重なり
        iou = bbox1.iou(bbox2)
        expected_iou = (50 * 50) / (100 * 100 + 100 * 100 - 50 * 50)
        assert abs(iou - expected_iou) < 0.001
        
        # 完全一致
        assert bbox1.iou(bbox1) == 1.0
        
        # 重なりなし
        bbox3 = BoundingBox(x=200, y=200, width=100, height=100,
                           id=3, score=0.9, class_name="test", frame_index=0)
        assert bbox1.iou(bbox3) == 0.0


class TestAlertTag:
    """AlertTagクラスのテスト"""
    
    def test_alert_creation(self):
        """AlertTag作成の基本テスト"""
        alert = AlertTag(
            level=AlertLevel.DETAILED,
            reason="Low confidence detection",
            frame_range=(100, 200),
            confidence=0.7
        )
        
        assert alert.level == AlertLevel.DETAILED
        assert alert.frame_range == (100, 200)
        assert alert.duration_frames == 101
    
    def test_alert_validation(self):
        """AlertTag検証のテスト"""
        # 不正なフレーム範囲
        with pytest.raises(ValueError, match="Invalid frame range"):
            AlertTag(
                level=AlertLevel.NORMAL,
                reason="test",
                frame_range=(200, 100),
                confidence=0.5
            )
        
        # 不正な信頼度
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            AlertTag(
                level=AlertLevel.NORMAL,
                reason="test",
                frame_range=(0, 100),
                confidence=1.5
            )
    
    def test_alert_methods(self):
        """AlertTagメソッドのテスト"""
        alert = AlertTag(
            level=AlertLevel.REQUIRED,
            reason="Missing detection",
            frame_range=(50, 150),
            confidence=0.9,
            object_ids=[1, 2, 3]
        )
        
        # フレーム範囲チェック
        assert alert.contains_frame(50)
        assert alert.contains_frame(100)
        assert alert.contains_frame(150)
        assert not alert.contains_frame(49)
        assert not alert.contains_frame(151)
        
        # シリアライズ
        data = alert.to_dict()
        assert data["level"] == "required"
        assert data["object_ids"] == [1, 2, 3]
        assert "created_at" in data


class TestOpticalFlow:
    """OpticalFlowクラスのテスト"""
    
    def test_optical_flow_creation(self):
        """OpticalFlow作成の基本テスト"""
        flow_data = np.random.randn(480, 640, 2).astype(np.float32)
        flow = OpticalFlow(
            flow=flow_data,
            frame_pair=(0, 1),
            method="liteflownet"
        )
        
        assert flow.shape == (480, 640)
        assert flow.frame_pair == (0, 1)
    
    def test_optical_flow_validation(self):
        """OpticalFlow検証のテスト"""
        # 不正な形状
        with pytest.raises(ValueError, match="Flow must be HxWx2"):
            OpticalFlow(
                flow=np.zeros((100, 100, 3)),
                frame_pair=(0, 1)
            )
    
    def test_optical_flow_properties(self):
        """OpticalFlowプロパティのテスト"""
        # 既知のフローでテスト
        flow_data = np.zeros((100, 100, 2), dtype=np.float32)
        flow_data[:, :, 0] = 3.0  # dx = 3
        flow_data[:, :, 1] = 4.0  # dy = 4
        
        flow = OpticalFlow(flow=flow_data, frame_pair=(0, 1))
        
        # 大きさ（3-4-5の三角形）
        magnitude = flow.magnitude
        np.testing.assert_almost_equal(magnitude, 5.0)
        
        # 角度
        angle = flow.angle
        expected_angle = np.arctan2(4.0, 3.0)
        np.testing.assert_almost_equal(angle, expected_angle)
    
    def test_optical_flow_io(self):
        """OpticalFlowのI/Oテスト"""
        flow_data = np.random.randn(240, 320, 2).astype(np.float32)
        confidence = np.random.rand(240, 320).astype(np.float32)
        
        flow = OpticalFlow(
            flow=flow_data,
            frame_pair=(10, 11),
            method="custom",
            confidence=confidence
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            npz_path = Path(tmpdir) / "flow.npz"
            
            # 保存
            flow.to_npz(npz_path)
            
            # 読み込み
            loaded_flow = OpticalFlow.from_npz(npz_path)
            
            np.testing.assert_array_equal(flow.flow, loaded_flow.flow)
            assert flow.frame_pair == loaded_flow.frame_pair
            assert flow.method == loaded_flow.method
            np.testing.assert_array_equal(flow.confidence, loaded_flow.confidence)


class TestProjectClasses:
    """プロジェクト関連クラスのテスト"""
    
    def test_edit_history(self):
        """EditHistoryのテスト"""
        history = EditHistory(
            timestamp=datetime.now(),
            action="add_mask",
            target_type="mask",
            target_id="mask_001",
            parameters={"confidence": 0.95},
            description="Added mask for frame 100"
        )
        
        data = history.to_dict()
        assert data["action"] == "add_mask"
        assert data["parameters"]["confidence"] == 0.95
    
    def test_timeline(self):
        """Timelineのテスト"""
        timeline = Timeline(
            total_frames=1800,
            fps=30.0,
            duration_seconds=60.0
        )
        
        assert timeline.working_duration_frames == 1800
        assert timeline.working_duration_seconds == 60.0
        
        # タイムコード変換（Non-Drop Frame）
        tc = timeline.frame_to_timecode(90)  # 3秒
        assert tc == "00:00:03:00"
        
        # Drop Frame（簡略版のテスト）
        timeline_df = Timeline(total_frames=1800, fps=29.97, duration_seconds=60.0)
        tc_df = timeline_df.frame_to_timecode(90, drop_frame=True)
        # Drop Frameの正確な実装は複雑なので、フォーマットのみ確認
        assert ";" in tc_df  # Drop Frameはセミコロンを使用
    
    def test_project_basic(self):
        """Project基本機能のテスト"""
        project = Project(
            name="Test Project",
            description="Test description",
            source_video_path="/path/to/video.mp4"
        )
        
        assert project.name == "Test Project"
        assert len(project.history) == 0
        assert not project.can_undo()
        assert not project.can_redo()
    
    def test_project_history(self):
        """Project履歴管理のテスト"""
        project = Project()
        
        # 履歴追加
        history1 = EditHistory(
            timestamp=datetime.now(),
            action="action1",
            target_type="test"
        )
        project.add_history(history1)
        
        assert len(project.history) == 1
        assert project.can_undo()
        assert not project.can_redo()
        
        # Undo
        undone = project.undo()
        assert undone == history1
        assert not project.can_undo()
        assert project.can_redo()
        
        # Redo
        redone = project.redo()
        assert redone == history1
        assert project.can_undo()
        assert not project.can_redo()
        
        # 新しい履歴追加（Redo履歴クリア）
        project.undo()
        history2 = EditHistory(
            timestamp=datetime.now(),
            action="action2",
            target_type="test"
        )
        project.add_history(history2)
        
        assert len(project.history) == 1
        assert project.history[0] == history2
    
    def test_project_io(self):
        """ProjectのI/Oテスト"""
        project = Project(
            name="IO Test Project",
            description="Testing save/load"
        )
        
        # タイムライン追加
        project.timeline = Timeline(
            total_frames=3000,
            fps=25.0,
            duration_seconds=120.0
        )
        
        # 履歴追加
        history = EditHistory(
            timestamp=datetime.now(),
            action="test_action",
            target_type="test"
        )
        project.add_history(history)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test.mosaicproj"
            
            # 保存
            project.save(project_path)
            assert project_path.exists()
            
            # 読み込み
            loaded_project = Project.load(project_path)
            
            assert loaded_project.name == project.name
            assert loaded_project.timeline.total_frames == 3000
            assert len(loaded_project.history) == 1
            assert loaded_project.history[0].action == "test_action"


class TestHelperFunctions:
    """ヘルパー関数のテスト"""
    
    def test_create_test_frame(self):
        """create_test_frameのテスト"""
        frame = create_test_frame()
        assert frame.shape == (1080, 1920, 3)
        assert frame.pts == 0
        
        # カスタムサイズ
        frame_custom = create_test_frame(width=640, height=480)
        assert frame_custom.shape == (480, 640, 3)
    
    def test_create_test_mask(self):
        """create_test_maskのテスト"""
        mask = create_test_mask()
        assert mask.shape == (1080, 1920)
        assert mask.area > 0  # 中央に矩形があるはず
        
        # カスタムサイズ
        mask_custom = create_test_mask(width=200, height=200)
        assert mask_custom.shape == (200, 200)
        # 中央の矩形は全体の1/4
        expected_area = 100 * 100
        assert mask_custom.area == expected_area