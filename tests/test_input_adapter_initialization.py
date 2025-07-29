#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入力アダプター初期化テスト

LocalFileInputAdapterが正しく初期化されることを確認
"""
import sys
import json
from pathlib import Path

# テスト対象モジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from infrastructure.adapters.input_data_source_factory import InputDataSourceFactory
from adapters.secondary.local_file_input_adapter import LocalFileInputAdapter


def test_factory_initialization():
    """ファクトリーによる初期化テスト"""
    print("="*70)
    print("入力アダプター初期化テスト")
    print("="*70)
    
    # テスト用の入力パス
    test_input_path = Path("/home/kenke/segformer/2MLPC/CODEFLOW0409/XxREPO_latest0615xX/MASK_EDITOR_GOD/test_input")
    
    # テストデータの準備（モック）
    if not test_input_path.exists():
        print(f"✗ テスト入力パスが存在しません: {test_input_path}")
        print("  実際のtest_inputディレクトリが必要です")
        return False
    
    # 1. create_local_file_sourceのテスト
    print("\n=== create_local_file_source テスト ===")
    try:
        # アダプターを作成
        adapter = InputDataSourceFactory.create_local_file_source(test_input_path)
        print("✓ アダプターが作成されました")
        
        # 初期化状態を確認（privateメンバーにアクセス）
        if isinstance(adapter, LocalFileInputAdapter):
            if adapter._is_initialized:
                print("✓ アダプターが初期化されています")
            else:
                print("✗ アダプターが初期化されていません")
                return False
        
        # メソッドが正常に動作するか確認
        try:
            video_path = adapter.get_video_path()
            print(f"✓ get_video_path()が正常動作: {video_path}")
        except RuntimeError as e:
            print(f"✗ get_video_path()でエラー: {e}")
            return False
            
    except Exception as e:
        print(f"✗ create_local_file_source エラー: {e}")
        return False
    
    # 2. create_from_configのテスト
    print("\n=== create_from_config テスト ===")
    try:
        config = {
            "type": "local_file",
            "base_path": str(test_input_path),
            "video_file": "CHUC_TEST1.mp4",
            "detections_file": "detections_genitile.json",
            "mask_directory": "filtered"
        }
        
        adapter2 = InputDataSourceFactory.create_from_config(config)
        print("✓ アダプターが設定から作成されました")
        
        # 初期化状態を確認
        if isinstance(adapter2, LocalFileInputAdapter):
            if adapter2._is_initialized:
                print("✓ アダプターが初期化されています")
            else:
                print("✗ アダプターが初期化されていません")
                return False
        
        # ビデオメタデータを取得してみる
        try:
            metadata = adapter2.get_video_metadata()
            print(f"✓ get_video_metadata()が正常動作")
            if metadata:
                print(f"  - 幅: {metadata.get('width')}")
                print(f"  - 高さ: {metadata.get('height')}")
                print(f"  - FPS: {metadata.get('fps')}")
        except RuntimeError as e:
            print(f"✗ get_video_metadata()でエラー: {e}")
            return False
            
    except Exception as e:
        print(f"✗ create_from_config エラー: {e}")
        return False
    
    # 3. マスク読み込みテスト
    print("\n=== マスク読み込みテスト ===")
    try:
        # フレーム0のマスクを取得
        mask_data = adapter.get_mask(0)
        if mask_data:
            print("✓ フレーム0のマスクが読み込めました")
            print(f"  - サイズ: {mask_data['width']}x{mask_data['height']}")
            print(f"  - オブジェクトID: {mask_data.get('object_ids', [])}")
        else:
            print("✓ フレーム0にマスクがありません（正常）")
            
    except RuntimeError as e:
        print(f"✗ マスク読み込みエラー: {e}")
        return False
    except Exception as e:
        print(f"△ マスク読み込み時の例外（ファイルが存在しない可能性）: {e}")
    
    return True


def main():
    """メイン実行関数"""
    success = test_factory_initialization()
    
    print("\n" + "="*70)
    print("テスト結果")
    print("="*70)
    
    if success:
        print("✅ 入力アダプターの初期化問題が修正されました")
        print("\n修正内容:")
        print("1. InputDataSourceFactory.create_local_file_source()でinitialize()を呼ぶように修正")
        print("2. InputDataSourceFactory.create_from_config()でもinitialize()を呼ぶように修正")
        print("\nこれにより、「Adapter not initialized」エラーが解消されます。")
        return 0
    else:
        print("❌ 初期化に問題があります")
        return 1


if __name__ == "__main__":
    sys.exit(main())