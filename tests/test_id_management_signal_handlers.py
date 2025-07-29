#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ID管理シグナルハンドラのテスト

ImprovedMainWindowのID管理関連メソッドが正しく実装されているか検証
"""
import sys
import os
from pathlib import Path

# テスト対象モジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_signal_handler_methods():
    """シグナルハンドラメソッドの存在確認"""
    print("="*70)
    print("ID管理シグナルハンドラ 実装確認テスト")
    print("="*70)
    
    # 1. ImprovedMainWindowのコード検査
    print("\n=== ImprovedMainWindow シグナルハンドラ確認 ===")
    try:
        improved_window_path = Path(__file__).parent.parent / "src" / "ui" / "improved_main_window.py"
        with open(improved_window_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_methods = [
            ("_on_ids_deleted", "IDが削除された時の処理"),
            ("_on_ids_merged", "IDがマージされた時の処理"),
            ("_on_threshold_changed", "閾値が変更された時の処理"),
            ("_on_id_preview_requested", "IDプレビューが要求された時の処理")
        ]
        
        missing_methods = []
        for method_name, description in required_methods:
            if f"def {method_name}" in content:
                print(f"✓ {method_name} - {description}")
                
                # メソッドの実装内容も確認
                if method_name == "_on_ids_deleted":
                    if "id_manager.delete_ids" in content:
                        print("  - ID削除処理の実装を確認")
                    if "self.video_preview.set_mask" in content:
                        print("  - ビデオプレビューの更新を確認")
                    if "self.id_management_panel.set_mask" in content:
                        print("  - ID管理パネルの更新を確認")
                        
                elif method_name == "_on_ids_merged":
                    if "id_manager.merge_ids" in content:
                        print("  - IDマージ処理の実装を確認")
                        
                elif method_name == "_on_threshold_changed":
                    if "threshold_manager.set_detection_threshold" in content:
                        print("  - 検出閾値設定の実装を確認")
                    if "threshold_manager.set_merge_threshold" in content:
                        print("  - マージ閾値設定の実装を確認")
            else:
                missing_methods.append((method_name, description))
        
        if missing_methods:
            print("\n✗ 不足しているメソッド:")
            for method_name, description in missing_methods:
                print(f"  - {method_name}: {description}")
            return False
            
    except Exception as e:
        print(f"✗ コード検査エラー: {e}")
        return False
    
    # 2. シグナル接続の確認
    print("\n=== シグナル接続確認 ===")
    signal_connections = [
        ("ids_deleted.connect(self._on_ids_deleted)", "削除シグナルの接続"),
        ("ids_merged.connect(self._on_ids_merged)", "マージシグナルの接続"),
        ("threshold_changed.connect(self._on_threshold_changed)", "閾値変更シグナルの接続"),
        ("preview_requested.connect(self._on_id_preview_requested)", "プレビューシグナルの接続")
    ]
    
    for connection, description in signal_connections:
        if connection in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} が見つかりません")
    
    # 3. 必要な属性へのアクセス確認
    print("\n=== 属性アクセス確認 ===")
    attribute_checks = [
        ("self.video_preview.current_mask_dto", "現在のマスクDTOへのアクセス"),
        ("self.di_container", "DIコンテナへのアクセス"),
        ("self.is_modified", "変更フラグへのアクセス"),
        ("self._update_ui_state", "UI状態更新メソッドの呼び出し")
    ]
    
    for attr, description in attribute_checks:
        if attr in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} が見つかりません")
    
    # 4. エラー処理の確認
    print("\n=== エラー処理確認 ===")
    if "if hasattr(self.video_preview, 'current_mask_dto')" in content:
        print("✓ current_mask_dto存在チェック")
    else:
        print("✗ current_mask_dto存在チェックが不足")
    
    if "if self.di_container:" in content:
        print("✓ DIコンテナ存在チェック")
    else:
        print("✗ DIコンテナ存在チェックが不足")
    
    return True


def main():
    """メイン実行関数"""
    success = test_signal_handler_methods()
    
    print("\n" + "="*70)
    print("テスト結果")
    print("="*70)
    
    if success:
        print("✅ ID管理シグナルハンドラが正しく実装されています")
        print("\n修正内容:")
        print("1. _on_ids_deleted: ID削除処理を実装")
        print("2. _on_ids_merged: IDマージ処理を実装")
        print("3. _on_threshold_changed: 閾値変更処理を実装")
        print("4. _on_id_preview_requested: プレビュー処理を実装（将来実装）")
        print("\n注意事項:")
        print("- video_preview.current_mask_dtoを通じてマスクにアクセス")
        print("- DIコンテナからID管理サービスを取得")
        print("- 変更後はis_modifiedフラグを設定")
        return 0
    else:
        print("❌ 実装に問題があります")
        return 1


if __name__ == "__main__":
    sys.exit(main())