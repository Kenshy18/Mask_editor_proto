#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media I/Oのテスト

要件定義書のMedia I/O要件（FR-28〜FR-42）の動作を検証します。
"""
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.core.media_io import (
    JsonIO,
    MaskIO,
    MediaReader,
    MediaWriter,
    check_sync_accuracy,
    convert_timecode,
    probe_video,
)
from src.core.models import (
    AlertLevel,
    AlertTag,
    BoundingBox,
    ChromaSubsampling,
    ColorSpace,
    FieldOrder,
    Frame,
    Mask,
    TransferCharacteristic,
)


# === テスト用動画生成 ===

def create_test_video(output_path: Path, 
                     width: int = 640,
                     height: int = 480,
                     fps: float = 30.0,
                     duration: float = 1.0,
                     codec: str = 'mp4v') -> None:
    """テスト用の動画を生成
    
    Args:
        output_path: 出力パス
        width: 幅
        height: 高さ
        fps: フレームレート
        duration: 長さ（秒）
        codec: コーデック
    """
    # OpenCVを使用した簡単な動画生成
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    frame_count = int(fps * duration)
    for i in range(frame_count):
        # グラデーションパターン
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 青成分：時間で変化
        img[:, :, 0] = int(255 * i / frame_count)
        
        # 緑成分：上から下へ
        img[:, :, 1] = np.linspace(0, 255, height, dtype=np.uint8)[:, np.newaxis]
        
        # 赤成分：左から右へ
        img[:, :, 2] = np.linspace(0, 255, width, dtype=np.uint8)
        
        out.write(img)
    
    out.release()


def create_test_mask(width: int = 640, height: int = 480) -> np.ndarray:
    """テスト用のマスクを生成"""
    mask = np.zeros((height, width), dtype=np.uint8)
    # 中央に円を描画
    center = (width // 2, height // 2)
    radius = min(width, height) // 4
    cv2.circle(mask, center, radius, 1, -1)
    return mask


# === MediaReaderのテスト ===

class TestMediaReader:
    """MediaReaderクラスのテスト"""
    
    @pytest.fixture
    def test_video_path(self):
        """テスト用動画を作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            create_test_video(video_path)
            yield video_path
    
    def test_media_reader_creation(self, test_video_path):
        """MediaReader作成の基本テスト"""
        with MediaReader(test_video_path) as reader:
            assert reader.width == 640
            assert reader.height == 480
            assert reader.fps == 30.0
            assert reader.frame_count == 30
            assert abs(reader.duration - 1.0) < 0.1
    
    def test_media_reader_metadata(self, test_video_path):
        """メタデータ抽出のテスト（FR-31, FR-34）"""
        with MediaReader(test_video_path) as reader:
            # 色空間情報
            assert reader.colorspace == ColorSpace.BT709
            assert reader.bit_depth == 8
            assert reader.chroma_subsampling == ChromaSubsampling.YUV420
            assert reader.transfer == TransferCharacteristic.GAMMA22
            
            # コーデック情報（テスト動画に依存するため確認のみ）
            assert reader.codec_name in ['h264', 'mpeg4', 'libx264', 'libx265']
            assert reader.pix_fmt in ['yuv420p', 'yuvj420p']
            
            # インターレース情報（FR-37）
            assert reader.field_order == FieldOrder.PROGRESSIVE
            assert not reader.is_interlaced
            
            # メタデータ辞書
            metadata = reader.get_metadata()
            assert metadata['width'] == 640
            assert metadata['height'] == 480
            assert metadata['fps'] == 30.0
    
    def test_media_reader_frame_access(self, test_video_path):
        """フレームアクセスのテスト"""
        with MediaReader(test_video_path) as reader:
            # 単一フレーム取得
            frame = reader.get_frame(0)
            assert frame is not None
            assert frame.shape == (480, 640, 3)
            assert frame.frame_number == 0
            assert frame.pts >= 0
            
            # 最後のフレーム
            last_frame = reader.get_frame(29)
            assert last_frame is not None
            assert last_frame.frame_number == 29
            
            # 範囲外
            assert reader.get_frame(-1) is None
            assert reader.get_frame(30) is None
    
    def test_media_reader_frame_iteration(self, test_video_path):
        """フレーム反復のテスト"""
        with MediaReader(test_video_path) as reader:
            # 全フレーム読み込み
            frames = list(reader.read_frames())
            assert len(frames) == 30
            
            # 部分読み込み
            partial_frames = list(reader.read_frames(start=10, end=20))
            assert len(partial_frames) == 10
            assert partial_frames[0].frame_number == 10
    
    def test_media_reader_timecode(self, test_video_path):
        """タイムコード関連のテスト（FR-34）"""
        with MediaReader(test_video_path) as reader:
            frame = reader.get_frame(0)
            assert frame.timecode == "00:00:00:00"
            
            # 15フレーム目（0.5秒）
            frame15 = reader.get_frame(15)
            assert frame15.timecode == "00:00:00:15"
    
    def test_media_reader_nonexistent_file(self):
        """存在しないファイルのテスト"""
        with pytest.raises(FileNotFoundError):
            MediaReader("nonexistent.mp4")


# === MediaWriterのテスト ===

class TestMediaWriter:
    """MediaWriterクラスのテスト"""
    
    @pytest.fixture
    def test_reader(self):
        """テスト用のMediaReaderを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_input.mp4"
            create_test_video(video_path)
            with MediaReader(video_path) as reader:
                yield reader
    
    def test_media_writer_basic(self, test_reader):
        """MediaWriter基本機能のテスト"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            # 書き込み
            with MediaWriter(output_path, test_reader) as writer:
                # 最初の5フレームを書き込み
                for frame in test_reader.read_frames(end=5):
                    writer.write_frame(frame)
            
            # 検証
            with MediaReader(output_path) as reader:
                assert reader.frame_count == 5
                assert reader.width == test_reader.width
                assert reader.height == test_reader.height
        finally:
            output_path.unlink()
    
    def test_media_writer_stream_copy(self, test_reader):
        """ストリームコピーのテスト（FR-28, FR-40）"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            with MediaWriter(output_path, test_reader) as writer:
                # ストリームコピー実行
                writer.copy_stream(test_reader.filepath)
            
            # 検証
            with MediaReader(output_path) as reader:
                # メタデータが保持されているか
                assert reader.width == test_reader.width
                assert reader.height == test_reader.height
                assert reader.fps == test_reader.fps
                assert reader.codec_name == test_reader.codec_name
        finally:
            output_path.unlink()
    
    def test_media_writer_metadata_preservation(self, test_reader):
        """メタデータ保持のテスト（FR-31）"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            with MediaWriter(output_path, test_reader) as writer:
                # いくつかのフレームを書き込み
                frames = list(test_reader.read_frames(end=10))
                writer.write_frames(iter(frames))
            
            # メタデータ検証
            with MediaReader(output_path) as reader:
                assert reader.colorspace == test_reader.colorspace
                assert reader.bit_depth == test_reader.bit_depth
                assert reader.chroma_subsampling == test_reader.chroma_subsampling
        finally:
            output_path.unlink()


# === MaskIOのテスト ===

class TestMaskIO:
    """MaskIOクラスのテスト"""
    
    def test_mask_npy_io(self):
        """NPY形式のマスクI/Oテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # テストマスク作成
            mask_data = create_test_mask()
            mask = Mask(
                data=mask_data,
                id=1,
                class_name="test",
                confidence=0.95,
                frame_index=0
            )
            
            # NPY保存
            npy_path = Path(tmpdir) / "mask.npy"
            MaskIO.save_mask(mask, npy_path)
            assert npy_path.exists()
            
            # NPY読み込み
            loaded_mask = MaskIO.load_mask(
                npy_path,
                frame_index=0,
                mask_id=1,
                class_name="test",
                confidence=0.95
            )
            
            np.testing.assert_array_equal(mask.data, loaded_mask.data)
            assert loaded_mask.id == 1
            assert loaded_mask.class_name == "test"
    
    def test_mask_png_io(self):
        """PNG形式のマスクI/Oテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # テストマスク作成
            mask_data = create_test_mask()
            mask = Mask(
                data=mask_data,
                id=2,
                class_name="genital",
                confidence=0.85,
                frame_index=10
            )
            
            # PNG保存
            png_path = Path(tmpdir) / "mask.png"
            MaskIO.save_mask(mask, png_path)
            assert png_path.exists()
            
            # PNG読み込み
            loaded_mask = MaskIO.load_mask(
                png_path,
                frame_index=10,
                mask_id=2,
                class_name="genital",
                confidence=0.85
            )
            
            # PNG保存では2値化されるため、形状のみ確認
            assert loaded_mask.shape == mask.shape
            # マスクの元の面積が大きいことを確認してから比較
            assert mask.area > 0, f"Original mask area: {mask.area}"
            assert loaded_mask.area > 0, f"Loaded mask area: {loaded_mask.area}"
    
    def test_mask_sequence_loading(self):
        """マスクシーケンス読み込みのテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 10枚のマスクを作成
            for i in range(10):
                mask_data = create_test_mask(width=320, height=240)
                mask_path = tmpdir / f"mask_{i:06d}.png"
                cv2.imwrite(str(mask_path), mask_data * 255)
            
            # シーケンス読み込み
            masks = MaskIO.load_mask_sequence(
                tmpdir,
                pattern="mask_{:06d}.png",
                start_frame=0,
                end_frame=10
            )
            
            assert len(masks) == 10
            assert all(m is not None for m in masks)
            assert masks[0].shape == (240, 320)
    
    def test_mask_unsupported_format(self):
        """サポートされないフォーマットのテスト"""
        with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
            with pytest.raises(ValueError, match="Unsupported mask format"):
                MaskIO.load_mask(tmp.name, frame_index=0)


# === JsonIOのテスト ===

class TestJsonIO:
    """JsonIOクラスのテスト"""
    
    def test_bounding_box_io_list_format(self):
        """バウンディングボックスI/O（リスト形式）のテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json_path = Path(tmp.name)
        
        try:
            # テストデータ作成
            boxes = [
                BoundingBox(x=10, y=20, width=100, height=200,
                           id=1, score=0.9, class_name="genital", frame_index=0),
                BoundingBox(x=50, y=60, width=150, height=250,
                           id=2, score=0.85, class_name="genital", frame_index=1),
            ]
            
            # 保存
            JsonIO.save_bounding_boxes(boxes, json_path, format='list')
            
            # 読み込み
            loaded_boxes = JsonIO.load_bounding_boxes(json_path)
            
            assert len(loaded_boxes) == 2
            assert loaded_boxes[0].x == 10
            assert loaded_boxes[0].y == 20
            assert loaded_boxes[0].score == 0.9
            assert loaded_boxes[1].frame_index == 1
        finally:
            json_path.unlink()
    
    def test_bounding_box_io_frame_dict_format(self):
        """バウンディングボックスI/O（フレーム辞書形式）のテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json_path = Path(tmp.name)
        
        try:
            # テストデータ作成
            boxes = [
                BoundingBox(x=10, y=20, width=100, height=200,
                           id=1, score=0.9, class_name="genital", frame_index=0),
                BoundingBox(x=15, y=25, width=105, height=205,
                           id=1, score=0.91, class_name="genital", frame_index=1),
            ]
            
            # フレーム辞書形式で保存
            JsonIO.save_bounding_boxes(boxes, json_path, format='frame_dict')
            
            # 読み込み確認
            with open(json_path) as f:
                data = json.load(f)
            
            assert "0" in data
            assert "1" in data
            assert len(data["0"]) == 1
            assert data["0"][0]["x"] == 10
        finally:
            json_path.unlink()
    
    def test_mask_attributes_io(self):
        """マスク属性情報I/Oのテスト（IN-3）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json_path = Path(tmp.name)
        
        try:
            # テスト属性
            attributes = {
                "version": "1.0",
                "created_at": "2024-07-28T10:00:00",
                "classes": ["genital", "face"],
                "thresholds": {
                    "detection": 0.5,
                    "merge": 0.3
                }
            }
            
            # 保存
            JsonIO.save_mask_attributes(attributes, json_path)
            
            # 読み込み
            loaded_attrs = JsonIO.load_mask_attributes(json_path)
            
            assert loaded_attrs["version"] == "1.0"
            assert loaded_attrs["classes"] == ["genital", "face"]
            assert loaded_attrs["thresholds"]["detection"] == 0.5
        finally:
            json_path.unlink()
    
    def test_alerts_io(self):
        """アラート情報I/Oのテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json_path = Path(tmp.name)
        
        try:
            # テストアラート
            alerts = [
                AlertTag(
                    level=AlertLevel.DETAILED,
                    reason="Low confidence detection",
                    frame_range=(10, 20),
                    confidence=0.7,
                    object_ids=[1, 2]
                ),
                AlertTag(
                    level=AlertLevel.REQUIRED,
                    reason="Missing detection",
                    frame_range=(30, 35),
                    confidence=0.9,
                    object_ids=[3]
                ),
            ]
            
            # 保存
            JsonIO.save_alerts(alerts, json_path)
            
            # 読み込み
            loaded_alerts = JsonIO.load_alerts(json_path)
            
            assert len(loaded_alerts) == 2
            assert loaded_alerts[0].level == AlertLevel.DETAILED
            assert loaded_alerts[0].frame_range == (10, 20)
            assert loaded_alerts[1].object_ids == [3]
        finally:
            json_path.unlink()


# === ユーティリティ関数のテスト ===

class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""
    
    def test_probe_video(self):
        """probe_video関数のテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test.mp4"
            create_test_video(video_path)
            
            # プローブ実行
            info = probe_video(video_path)
            
            assert 'streams' in info
            assert len(info['streams']) > 0
            
            # ビデオストリーム情報
            video_stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
            assert video_stream['width'] == 640
            assert video_stream['height'] == 480
    
    def test_check_sync_accuracy(self):
        """音声同期精度チェックのテスト（FR-29）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test.mp4"
            create_test_video(video_path)
            
            # 同期精度チェック
            sync_error = check_sync_accuracy(video_path)
            
            # 音声なしの動画なので0
            assert sync_error == 0.0
    
    def test_convert_timecode(self):
        """タイムコード変換のテスト"""
        # 30fps → 25fps
        tc = convert_timecode("00:01:00:00", 30.0, 25.0)
        # 30fpsの60秒 = 1800フレーム
        # 25fpsでは1800フレーム = 72秒 = 1:12:00
        assert tc == "00:01:12:00"
        
        # 25fps → 30fps
        tc = convert_timecode("00:01:00:00", 25.0, 30.0)
        # 25fpsの60秒 = 1500フレーム
        # 30fpsでは1500フレーム = 50秒 = 0:50:00
        assert tc == "00:00:50:00"
        
        # Drop Frame形式
        tc = convert_timecode("00:01:00:00", 30.0, 29.97, drop_frame=True)
        assert ";" in tc  # Drop Frameはセミコロンを使用


# === 統合テスト ===

class TestIntegration:
    """統合テスト"""
    
    def test_video_processing_pipeline(self):
        """動画処理パイプラインの統合テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 1. テスト動画作成
            input_path = tmpdir / "input.mp4"
            create_test_video(input_path, fps=25.0, duration=2.0)
            
            # 2. 動画読み込み
            with MediaReader(input_path) as reader:
                metadata = reader.get_metadata()
                assert metadata['fps'] == 25.0
                assert metadata['frame_count'] == 50
                
                # 3. マスク作成
                masks = []
                for i in range(10):
                    mask_data = create_test_mask(
                        width=reader.width,
                        height=reader.height
                    )
                    mask = Mask(
                        data=mask_data,
                        id=1,
                        class_name="test",
                        confidence=0.9,
                        frame_index=i
                    )
                    masks.append(mask)
                
                # 4. マスク保存
                mask_dir = tmpdir / "masks"
                mask_dir.mkdir()
                for mask in masks:
                    mask_path = mask_dir / f"mask_{mask.frame_index:06d}.npy"
                    MaskIO.save_mask(mask, mask_path)
                
                # 5. バウンディングボックス作成・保存
                boxes = []
                for i in range(10):
                    bbox = BoundingBox(
                        x=100 + i * 10,
                        y=100 + i * 10,
                        width=200,
                        height=200,
                        id=1,
                        score=0.9 - i * 0.01,
                        class_name="test",
                        frame_index=i
                    )
                    boxes.append(bbox)
                
                bbox_path = tmpdir / "detections.json"
                JsonIO.save_bounding_boxes(boxes, bbox_path)
                
                # 6. 動画書き出し
                output_path = tmpdir / "output.mp4"
                with MediaWriter(output_path, reader) as writer:
                    # 最初の10フレームを処理
                    for frame in reader.read_frames(end=10):
                        writer.write_frame(frame)
                
                # 7. 結果検証
                assert output_path.exists()
                
                with MediaReader(output_path) as out_reader:
                    assert out_reader.frame_count == 10
                    assert out_reader.width == reader.width
                    assert out_reader.height == reader.height
                
                # 8. マスクシーケンス読み込み確認
                loaded_masks = MaskIO.load_mask_sequence(
                    mask_dir,
                    pattern="mask_{:06d}.npy",
                    end_frame=10
                )
                assert len(loaded_masks) == 10
                
                # 9. バウンディングボックス読み込み確認
                loaded_boxes = JsonIO.load_bounding_boxes(bbox_path)
                assert len(loaded_boxes) == 10
                assert loaded_boxes[0].x == 100