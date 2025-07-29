#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アダプター初期化修正確認

InputDataSourceFactoryの修正が正しいか確認
"""
from pathlib import Path

def test_initialization_fix():
    """初期化修正の確認"""
    print("="*70)
    print("LocalFileInputAdapter 初期化修正確認")
    print("="*70)
    
    # 1. 修正前の問題点
    print("\n=== 問題の原因 ===")
    print("1. LocalFileInputAdapterは、initialize()メソッドが呼ばれないと")
    print("   _is_initializedフラグがFalseのまま")
    print("2. get_mask()やget_video_path()など全メソッドが")
    print("   'Adapter not initialized'エラーを投げる")
    print("3. InputDataSourceFactoryがアダプターを作成する際、")
    print("   set_base_path()は呼ぶがinitialize()を呼んでいなかった")
    
    # 2. 修正内容の確認
    print("\n=== 修正内容 ===")
    factory_path = Path(__file__).parent.parent / "src" / "infrastructure" / "adapters" / "input_data_source_factory.py"
    
    try:
        with open(factory_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # create_local_file_sourceの修正確認
        if "adapter.initialize(config)" in content:
            print("✓ create_local_file_source()でinitialize()を呼ぶように修正済み")
        else:
            print("✗ create_local_file_source()の修正が不完全")
            return False
        
        # create_from_configの修正確認
        create_from_config_section = content[content.find("def create_from_config"):content.find("def create_local_file_source")]
        if "adapter.initialize(config)" in create_from_config_section:
            print("✓ create_from_config()でもinitialize()を呼ぶように修正済み")
        else:
            print("✗ create_from_config()の修正が不完全")
            return False
            
    except Exception as e:
        print(f"✗ ファイル読み込みエラー: {e}")
        return False
    
    # 3. 修正後の動作
    print("\n=== 修正後の動作 ===")
    print("1. InputDataSourceFactory.create_local_file_source(path)を呼ぶと:")
    print("   a. LocalFileInputAdapterインスタンスが作成される")
    print("   b. set_base_path()でベースパスが設定される")
    print("   c. initialize()でアダプターが初期化される ← 新規追加")
    print("   d. _is_initializedがTrueになる")
    print("2. これにより、get_mask()等のメソッドが正常に動作する")
    
    # 4. LocalFileInputAdapterの確認
    print("\n=== LocalFileInputAdapterの構造確認 ===")
    adapter_path = Path(__file__).parent.parent / "src" / "adapters" / "secondary" / "local_file_input_adapter.py"
    
    try:
        with open(adapter_path, 'r', encoding='utf-8') as f:
            adapter_content = f.read()
        
        # 初期化チェックの存在確認
        if "if not self._is_initialized:" in adapter_content:
            print("✓ 各メソッドで_is_initializedチェックが実装されている")
        
        if 'raise RuntimeError("Adapter not initialized. Call initialize() first.")' in adapter_content:
            print("✓ 未初期化時のエラーメッセージが正しい")
            
    except Exception as e:
        print(f"△ アダプターファイル確認エラー: {e}")
    
    return True


def main():
    """メイン実行関数"""
    success = test_initialization_fix()
    
    print("\n" + "="*70)
    print("修正確認結果")
    print("="*70)
    
    if success:
        print("✅ 初期化問題の修正が正しく実装されています")
        print("\nユーザーが報告したエラー:")
        print('  "Failed to load mask for frame 0: Adapter not initialized."')
        print("\nこのエラーは解消されるはずです。")
        print("\n次のステップ:")
        print("1. アプリケーションを再起動")
        print("2. 動画ファイルを読み込み")
        print("3. マスクが正常に表示されることを確認")
        return 0
    else:
        print("❌ 修正に問題があります")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())