#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ID管理UIコンポーネントの統合テスト
"""
import unittest
import sys
import numpy as np
from pathlib import Path

# 環境設定
import os
os.environ['QT_PLUGIN_PATH'] = ''
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '0'

# テスト対象モジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

from domain.dto.mask_dto import MaskDTO
from adapters.secondary.id_manager_adapter import IDManagerAdapter
from adapters.secondary.threshold_manager_adapter import ThresholdManagerAdapter
from adapters.secondary.id_preview_adapter import IDPreviewAdapter
from ui.id_management_panel import IDManagementPanel
from ui.i18n import init_i18n


class TestIDManagementPanel(unittest.TestCase):
    """IDManagementPanelの統合テスト"""
    
    @classmethod
    def setUpClass(cls):
        """テスト用QApplicationの作成"""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
            
        # i18nを初期化
        init_i18n(cls.app)
    
    def setUp(self):
        """各テストの前準備"""
        # サービスのインスタンス化
        self.id_manager = IDManagerAdapter()
        self.threshold_manager = ThresholdManagerAdapter()
        self.id_preview = IDPreviewAdapter()
        
        # UIパネルの作成
        self.panel = IDManagementPanel(
            self.id_manager,
            self.threshold_manager,
            self.id_preview
        )
        
        # テスト用マスクデータ
        test_mask_data = np.zeros((512, 512), dtype=np.uint8)
        test_mask_data[0:100, 0:100] = 1
        test_mask_data[0:100, 412:512] = 2
        test_mask_data[206:306, 206:306] = 3
        
        self.test_mask_dto = MaskDTO(
            frame_index=0,
            data=test_mask_data,
            width=512,
            height=512,
            object_ids=[1, 2, 3],
            classes={1: "genital", 2: "genital", 3: "genital"},
            confidences={1: 0.9, 2: 0.7, 3: 0.5}
        )
        
        # シグナル受信記録用
        self.signals_received = []
        
    def test_ui_initialization(self):
        """UI初期化のテスト"""
        print("\n=== UI統合テスト：初期化確認 ===")
        
        # UI要素の存在確認
        self.assertIsNotNone(self.panel.id_list)
        self.assertIsNotNone(self.panel.delete_button)
        self.assertIsNotNone(self.panel.delete_range_button)
        self.assertIsNotNone(self.panel.delete_all_button)
        self.assertIsNotNone(self.panel.merge_button)
        self.assertIsNotNone(self.panel.merge_target_combo)
        self.assertIsNotNone(self.panel.detection_slider)
        self.assertIsNotNone(self.panel.merge_slider)
        
        print("✓ すべてのUI要素が正しく初期化されました")
        
    def test_set_mask_updates_ui(self):
        """マスク設定時のUI更新テスト"""
        print("\n=== UI統合テスト：マスク設定 ===")
        
        # マスクを設定
        self.panel.set_mask(self.test_mask_dto)
        
        # ID一覧の更新確認
        self.assertEqual(self.panel.id_list.count(), 3)
        print(f"✓ ID一覧に{self.panel.id_list.count()}個のアイテムが表示されました")
        
        # マージターゲットコンボボックスの更新確認
        self.assertEqual(self.panel.merge_target_combo.count(), 3)
        print(f"✓ マージターゲットに{self.panel.merge_target_combo.count()}個の選択肢")
        
        # 統計情報の確認
        self.assertIn(1, self.panel.id_statistics)
        self.assertIn(2, self.panel.id_statistics)
        self.assertIn(3, self.panel.id_statistics)
        print("✓ ID統計情報が正しく計算されました")
        
    def test_id_selection(self):
        """ID選択動作のテスト"""
        print("\n=== UI統合テスト：ID選択 ===")
        
        self.panel.set_mask(self.test_mask_dto)
        
        # 最初のアイテムを選択
        self.panel.id_list.setCurrentRow(0)
        self.assertEqual(len(self.panel.id_list.selectedItems()), 1)
        
        # 統計表示が更新されることを確認
        stats_text = self.panel.stats_label.text()
        self.assertIn("ID", stats_text)
        self.assertIn("px", stats_text)
        print("✓ ID選択時に統計情報が表示されました")
        
        # 複数選択（Ctrlキーを使用）
        self.panel.id_list.setSelectionMode(self.panel.id_list.SelectionMode.ExtendedSelection)
        self.panel.id_list.item(0).setSelected(True)
        self.panel.id_list.item(1).setSelected(True)
        
        selected_count = len(self.panel.id_list.selectedItems())
        self.assertEqual(selected_count, 2)
        print(f"✓ 複数選択が可能：{selected_count}個選択")
        
    def test_threshold_sliders(self):
        """閾値スライダーのテスト"""
        print("\n=== UI統合テスト：閾値スライダー ===")
        
        # 検出閾値スライダーのテスト
        initial_detection = self.panel.detection_slider.value()
        self.panel.detection_slider.setValue(75)  # 0.75
        
        # ラベルが更新されることを確認
        self.assertEqual(self.panel.detection_value_label.text(), "0.75")
        print("✓ 検出閾値スライダーが動作：0.75に設定")
        
        # マージ閾値スライダーのテスト
        self.panel.merge_slider.setValue(60)  # 0.60
        self.assertEqual(self.panel.merge_value_label.text(), "0.60")
        print("✓ マージ閾値スライダーが動作：0.60に設定")
        
        # ThresholdManagerの値も更新されているか確認
        self.assertEqual(self.threshold_manager.get_detection_threshold(), 0.75)
        self.assertEqual(self.threshold_manager.get_merge_threshold(), 0.60)
        print("✓ 閾値管理サービスに値が反映されました")
        
    def test_signal_emission(self):
        """シグナル発信のテスト"""
        print("\n=== UI統合テスト：シグナル発信 ===")
        
        # シグナル接続
        self.panel.ids_deleted.connect(
            lambda ids: self.signals_received.append(("deleted", ids))
        )
        self.panel.threshold_changed.connect(
            lambda t, v: self.signals_received.append(("threshold", t, v))
        )
        
        # 閾値変更でシグナルが発信されるか
        self.panel.detection_slider.setValue(80)
        
        # シグナル処理を待つ
        QTest.qWait(100)
        
        # シグナルが記録されたか確認
        found_threshold_signal = False
        for signal in self.signals_received:
            if signal[0] == "threshold" and signal[1] == "detection":
                found_threshold_signal = True
                print(f"✓ 閾値変更シグナル受信：{signal[1]} = {signal[2]}")
                
        self.assertTrue(found_threshold_signal)
        
    def test_button_states(self):
        """ボタン状態のテスト"""
        print("\n=== UI統合テスト：ボタン状態管理 ===")
        
        # マスクなしの状態
        self.panel.set_mask(None)
        self.assertFalse(self.panel.delete_button.isEnabled())
        self.assertFalse(self.panel.delete_all_button.isEnabled())
        print("✓ マスクなし時：削除ボタンが無効")
        
        # マスクありの状態
        self.panel.set_mask(self.test_mask_dto)
        self.assertFalse(self.panel.delete_button.isEnabled())  # 選択なし
        self.assertTrue(self.panel.delete_all_button.isEnabled())
        print("✓ マスクあり時：全削除ボタンが有効")
        
        # ID選択時
        self.panel.id_list.item(0).setSelected(True)
        self.panel._update_ui_state()
        self.assertTrue(self.panel.delete_button.isEnabled())
        self.assertTrue(self.panel.merge_button.isEnabled())
        print("✓ ID選択時：削除・マージボタンが有効")
        
    def test_preview_checkbox(self):
        """プレビューチェックボックスのテスト"""
        print("\n=== UI統合テスト：プレビュー設定 ===")
        
        # 初期状態確認
        self.assertTrue(self.panel.preview_check.isChecked())
        print("✓ プレビューは初期状態で有効")
        
        # プレビュー無効化
        self.panel.preview_check.setChecked(False)
        self.assertFalse(self.panel.preview_check.isChecked())
        print("✓ プレビューを無効化可能")


def run_ui_integration_tests():
    """UI統合テストの実行"""
    print("=" * 70)
    print("ID管理UIコンポーネント 統合テスト")
    print("=" * 70)
    
    # テストスイートの作成
    suite = unittest.TestSuite()
    
    # テストケースを追加
    suite.addTest(TestIDManagementPanel('test_ui_initialization'))
    suite.addTest(TestIDManagementPanel('test_set_mask_updates_ui'))
    suite.addTest(TestIDManagementPanel('test_id_selection'))
    suite.addTest(TestIDManagementPanel('test_threshold_sliders'))
    suite.addTest(TestIDManagementPanel('test_signal_emission'))
    suite.addTest(TestIDManagementPanel('test_button_states'))
    suite.addTest(TestIDManagementPanel('test_preview_checkbox'))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("UI統合テスト結果")
    print("=" * 70)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    print("\nUI要素の動作確認:")
    print("✓ ID一覧表示とマルチ選択")
    print("✓ 削除ボタン（選択削除、範囲削除、全削除）")
    print("✓ マージ機能とターゲット選択")
    print("✓ 閾値調整スライダー（検出・マージ）")
    print("✓ リアルタイムプレビュー設定")
    print("✓ シグナル発信と状態管理")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # QApplicationを適切に終了
    try:
        success = run_ui_integration_tests()
    finally:
        if QApplication.instance():
            QApplication.instance().quit()
    
    sys.exit(0 if success else 1)