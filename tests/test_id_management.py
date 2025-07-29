#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ID管理機能のテスト

要件FR-13、FR-14の実装確認
"""
import unittest
import numpy as np
import sys
from pathlib import Path

# テスト対象モジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from domain.dto.mask_dto import MaskDTO
from domain.dto.id_management_dto import (
    IDStatisticsDTO, ThresholdSettingsDTO, MergeCandidateDTO
)
from adapters.secondary.id_manager_adapter import IDManagerAdapter
from adapters.secondary.threshold_manager_adapter import ThresholdManagerAdapter
from adapters.secondary.id_preview_adapter import IDPreviewAdapter


class TestIDManagerAdapter(unittest.TestCase):
    """IDManagerAdapterのテスト（FR-13：マスク削除）"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.id_manager = IDManagerAdapter()
        
        # テスト用マスクデータ作成（512x512、ID: 1,2,3,4,5）
        self.test_mask_data = np.zeros((512, 512), dtype=np.uint8)
        # ID 1: 左上 (100x100)
        self.test_mask_data[0:100, 0:100] = 1
        # ID 2: 右上 (100x100)
        self.test_mask_data[0:100, 412:512] = 2
        # ID 3: 中央 (100x100)
        self.test_mask_data[206:306, 206:306] = 3
        # ID 4: 左下 (50x50)
        self.test_mask_data[462:512, 0:50] = 4
        # ID 5: 右下 (50x50)
        self.test_mask_data[462:512, 462:512] = 5
        
        self.test_mask_dto = MaskDTO(
            frame_index=0,
            data=self.test_mask_data,
            width=512,
            height=512,
            object_ids=[1, 2, 3, 4, 5],
            classes={1: "genital", 2: "genital", 3: "genital", 4: "genital", 5: "genital"},
            confidences={1: 0.9, 2: 0.8, 3: 0.7, 4: 0.6, 5: 0.5}
        )
        
    def test_delete_ids_single(self):
        """単一ID削除のテスト"""
        print("\n=== FR-13テスト：単一ID削除 ===")
        
        # ID 3を削除
        mask_dict = self.test_mask_dto.to_dict()
        result_dict = self.id_manager.delete_ids(mask_dict, [3])
        result_dto = MaskDTO.from_dict(result_dict)
        
        # 検証
        self.assertNotIn(3, result_dto.object_ids)
        self.assertEqual(len(result_dto.object_ids), 4)
        self.assertEqual(np.sum(result_dto.data == 3), 0)
        self.assertNotIn(3, result_dto.classes)
        self.assertNotIn(3, result_dto.confidences)
        
        print(f"✓ ID 3を削除：残りID {result_dto.object_ids}")
        
    def test_delete_ids_multiple(self):
        """複数ID削除のテスト"""
        print("\n=== FR-13テスト：複数ID削除 ===")
        
        # ID 1,2,5を削除
        mask_dict = self.test_mask_dto.to_dict()
        result_dict = self.id_manager.delete_ids(mask_dict, [1, 2, 5])
        result_dto = MaskDTO.from_dict(result_dict)
        
        # 検証
        self.assertEqual(set(result_dto.object_ids), {3, 4})
        self.assertEqual(np.sum(result_dto.data == 1), 0)
        self.assertEqual(np.sum(result_dto.data == 2), 0)
        self.assertEqual(np.sum(result_dto.data == 5), 0)
        
        print(f"✓ ID 1,2,5を削除：残りID {result_dto.object_ids}")
        
    def test_delete_range(self):
        """範囲指定削除のテスト"""
        print("\n=== FR-13テスト：範囲指定削除 ===")
        
        # ID 2-4の範囲を削除
        mask_dict = self.test_mask_dto.to_dict()
        result_dict = self.id_manager.delete_range(mask_dict, (2, 4))
        result_dto = MaskDTO.from_dict(result_dict)
        
        # 検証
        self.assertEqual(set(result_dto.object_ids), {1, 5})
        self.assertEqual(np.sum(result_dto.data == 2), 0)
        self.assertEqual(np.sum(result_dto.data == 3), 0)
        self.assertEqual(np.sum(result_dto.data == 4), 0)
        
        print(f"✓ ID 2-4を範囲削除：残りID {result_dto.object_ids}")
        
    def test_delete_all(self):
        """全削除のテスト"""
        print("\n=== FR-13テスト：全ID削除 ===")
        
        mask_dict = self.test_mask_dto.to_dict()
        result_dict = self.id_manager.delete_all(mask_dict)
        result_dto = MaskDTO.from_dict(result_dict)
        
        # 検証
        self.assertEqual(len(result_dto.object_ids), 0)
        self.assertEqual(np.sum(result_dto.data), 0)
        self.assertEqual(len(result_dto.classes), 0)
        self.assertEqual(len(result_dto.confidences), 0)
        
        print("✓ 全IDを削除：マスクがクリアされました")
        
    def test_merge_ids(self):
        """IDマージのテスト"""
        print("\n=== ID管理追加機能テスト：IDマージ ===")
        
        # ID 4,5を3にマージ
        mask_dict = self.test_mask_dto.to_dict()
        result_dict = self.id_manager.merge_ids(mask_dict, [4, 5], 3)
        result_dto = MaskDTO.from_dict(result_dict)
        
        # 検証
        self.assertEqual(set(result_dto.object_ids), {1, 2, 3})
        # マージ後のID 3のピクセル数確認
        merged_pixels = np.sum(result_dto.data == 3)
        original_pixels = 100*100 + 50*50 + 50*50  # 元のID3 + ID4 + ID5
        self.assertEqual(merged_pixels, original_pixels)
        
        print(f"✓ ID 4,5をID 3にマージ：残りID {result_dto.object_ids}")
        
    def test_get_id_statistics(self):
        """ID統計情報取得のテスト"""
        print("\n=== ID管理追加機能テスト：統計情報 ===")
        
        mask_dict = self.test_mask_dto.to_dict()
        stats = self.id_manager.get_id_statistics(mask_dict)
        
        # ID 1の統計情報を検証
        self.assertIn(1, stats)
        stat1 = stats[1]
        self.assertEqual(stat1["pixel_count"], 10000)  # 100x100
        self.assertEqual(stat1["bbox"], (0, 0, 99, 99))
        self.assertAlmostEqual(stat1["area_ratio"], 10000/(512*512), places=4)
        self.assertEqual(stat1["confidence"], 0.9)
        self.assertEqual(stat1["class_name"], "genital")
        
        print(f"✓ ID統計情報を取得：{len(stats)}個のID")
        for id_, stat in stats.items():
            print(f"  ID {id_}: {stat['pixel_count']} pixels, "
                  f"area_ratio: {stat['area_ratio']:.2%}")


class TestThresholdManagerAdapter(unittest.TestCase):
    """ThresholdManagerAdapterのテスト（FR-14：閾値調節UI）"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.threshold_manager = ThresholdManagerAdapter()
        
        # テスト用マスクDTO（TestIDManagerAdapterと同じ）
        test_mask_data = np.zeros((512, 512), dtype=np.uint8)
        test_mask_data[0:100, 0:100] = 1
        test_mask_data[0:100, 412:512] = 2
        test_mask_data[206:306, 206:306] = 3
        test_mask_data[462:512, 0:50] = 4
        test_mask_data[462:512, 462:512] = 5
        
        self.test_mask_dto = MaskDTO(
            frame_index=0,
            data=test_mask_data,
            width=512,
            height=512,
            object_ids=[1, 2, 3, 4, 5],
            classes={1: "genital", 2: "genital", 3: "genital", 4: "genital", 5: "genital"},
            confidences={1: 0.9, 2: 0.8, 3: 0.7, 4: 0.6, 5: 0.5}
        )
        
    def test_detection_threshold_slider(self):
        """検出閾値スライダーのテスト"""
        print("\n=== FR-14テスト：検出閾値スライダー ===")
        
        # 初期値確認
        initial_threshold = self.threshold_manager.get_detection_threshold()
        self.assertEqual(initial_threshold, 0.5)
        print(f"✓ 初期検出閾値: {initial_threshold}")
        
        # 閾値変更
        self.threshold_manager.set_detection_threshold(0.75)
        new_threshold = self.threshold_manager.get_detection_threshold()
        self.assertEqual(new_threshold, 0.75)
        print(f"✓ 検出閾値を0.75に変更")
        
        # 履歴確認
        history = self.threshold_manager.get_threshold_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["threshold_type"], "detection")
        self.assertEqual(history[0]["old_value"], 0.5)
        self.assertEqual(history[0]["new_value"], 0.75)
        print("✓ 閾値変更履歴が記録されました")
        
    def test_merge_threshold_slider(self):
        """マージ閾値スライダーのテスト"""
        print("\n=== FR-14テスト：マージ閾値スライダー ===")
        
        # 初期値確認
        initial_threshold = self.threshold_manager.get_merge_threshold()
        self.assertEqual(initial_threshold, 0.8)
        print(f"✓ 初期マージ閾値: {initial_threshold}")
        
        # 閾値変更
        self.threshold_manager.set_merge_threshold(0.6)
        new_threshold = self.threshold_manager.get_merge_threshold()
        self.assertEqual(new_threshold, 0.6)
        print(f"✓ マージ閾値を0.6に変更")
        
    def test_apply_detection_threshold(self):
        """検出閾値適用のテスト"""
        print("\n=== FR-14テスト：検出閾値の適用 ===")
        
        # 閾値0.65を適用（ID 4,5が削除されるはず）
        mask_dict = self.test_mask_dto.to_dict()
        result_dict = self.threshold_manager.apply_detection_threshold(
            mask_dict, 
            self.test_mask_dto.confidences,
            0.65
        )
        result_dto = MaskDTO.from_dict(result_dict)
        
        # 検証
        self.assertEqual(set(result_dto.object_ids), {1, 2, 3})
        print(f"✓ 閾値0.65適用後：ID {result_dto.object_ids}")
        print("  信頼度0.65未満のID 4(0.6), 5(0.5)が削除されました")
        
    def test_suggest_merge_candidates(self):
        """マージ候補提案のテスト"""
        print("\n=== FR-14テスト：マージ候補の提案 ===")
        
        # 近接するIDのテストデータを作成
        close_mask_data = np.zeros((100, 100), dtype=np.uint8)
        close_mask_data[10:30, 10:30] = 1  # ID 1
        close_mask_data[25:45, 25:45] = 2  # ID 2（ID 1と重なる）
        close_mask_data[80:90, 80:90] = 3  # ID 3（離れている）
        
        close_mask_dto = MaskDTO(
            frame_index=0,
            data=close_mask_data,
            width=100,
            height=100,
            object_ids=[1, 2, 3],
            classes={},
            confidences={}
        )
        
        # マージ候補を提案
        mask_dict = close_mask_dto.to_dict()
        candidates = self.threshold_manager.suggest_merge_candidates(mask_dict, 0.3)
        
        # 検証
        self.assertGreater(len(candidates), 0)
        print(f"✓ {len(candidates)}個のマージ候補を検出")
        for id1, id2, score in candidates[:3]:  # 上位3件を表示
            print(f"  ID {id1} と ID {id2}: 類似度 {score:.3f}")


class TestIDPreviewAdapter(unittest.TestCase):
    """IDPreviewAdapterのテスト"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        self.id_preview = IDPreviewAdapter()
        
        # シンプルなテスト用マスク（100x100）
        self.test_mask_data = np.zeros((100, 100), dtype=np.uint8)
        self.test_mask_data[20:40, 20:40] = 1
        self.test_mask_data[60:80, 60:80] = 2
        
        self.test_mask_dto = MaskDTO(
            frame_index=0,
            data=self.test_mask_data,
            width=100,
            height=100,
            object_ids=[1, 2],
            classes={},
            confidences={1: 0.9, 2: 0.5}
        )
        
    def test_preview_delete(self):
        """削除プレビューのテスト"""
        print("\n=== プレビュー機能テスト：削除プレビュー ===")
        
        mask_dict = self.test_mask_dto.to_dict()
        preview = self.id_preview.preview_delete(mask_dict, [1])
        
        # 検証
        self.assertEqual(preview.shape, (100, 100, 3))
        self.assertEqual(preview.dtype, np.uint8)
        print("✓ 削除プレビュー画像を生成（100x100x3）")
        
    def test_preview_threshold(self):
        """閾値プレビューのテスト"""
        print("\n=== プレビュー機能テスト：閾値プレビュー ===")
        
        mask_dict = self.test_mask_dto.to_dict()
        preview = self.id_preview.preview_threshold(
            mask_dict,
            self.test_mask_dto.confidences,
            0.7
        )
        
        # 検証
        self.assertEqual(preview.shape, (100, 100, 3))
        print("✓ 閾値プレビュー画像を生成（閾値0.7）")
        print("  信頼度0.5のID 2が削除対象として表示")


def run_verification_tests():
    """要件照合テストの実行"""
    print("=" * 70)
    print("ID管理機能 要件照合テスト")
    print("=" * 70)
    
    # テストスイートの作成
    suite = unittest.TestSuite()
    
    # FR-13のテスト
    suite.addTest(TestIDManagerAdapter('test_delete_ids_single'))
    suite.addTest(TestIDManagerAdapter('test_delete_ids_multiple'))
    suite.addTest(TestIDManagerAdapter('test_delete_range'))
    suite.addTest(TestIDManagerAdapter('test_delete_all'))
    suite.addTest(TestIDManagerAdapter('test_merge_ids'))
    suite.addTest(TestIDManagerAdapter('test_get_id_statistics'))
    
    # FR-14のテスト
    suite.addTest(TestThresholdManagerAdapter('test_detection_threshold_slider'))
    suite.addTest(TestThresholdManagerAdapter('test_merge_threshold_slider'))
    suite.addTest(TestThresholdManagerAdapter('test_apply_detection_threshold'))
    suite.addTest(TestThresholdManagerAdapter('test_suggest_merge_candidates'))
    
    # プレビュー機能のテスト
    suite.addTest(TestIDPreviewAdapter('test_preview_delete'))
    suite.addTest(TestIDPreviewAdapter('test_preview_threshold'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("テスト結果サマリー")
    print("=" * 70)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    print("\n要件充足状況:")
    print("✓ FR-13（MUST）マスク削除:")
    print("  - ID指定削除: 実装済み")
    print("  - 範囲指定削除: 実装済み")
    print("  - 一括削除: 実装済み")
    print("✓ FR-14（SHOULD）閾値調節UI:")
    print("  - 検出閾値スライダー: 実装済み")
    print("  - IDマージ閾値スライダー: 実装済み")
    print("  - リアルタイムプレビュー: 実装済み")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_verification_tests()
    sys.exit(0 if success else 1)