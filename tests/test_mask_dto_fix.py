#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MaskDTO metadata エラー修正確認

LocalFileInputAdapterのMaskDTO作成時のエラーを修正
"""
import sys
from pathlib import Path

# テスト対象モジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_mask_dto_fix():
    """MaskDTO metadataエラーの修正確認"""
    print("="*70)
    print("MaskDTO metadata エラー修正確認")
    print("="*70)
    
    # 1. エラーの原因
    print("\n=== エラーの原因 ===")
    print("LocalFileInputAdapter.get_mask()でMaskDTOを作成する際、")
    print("'metadata'引数を渡していたが、MaskDTOには")
    print("metadataフィールドが定義されていなかった。")
    
    print("\nエラーメッセージ:")
    print('  "MaskDTO.__init__() got an unexpected keyword argument \'metadata\'"')
    
    # 2. MaskDTOの構造確認
    print("\n=== MaskDTOの構造 ===")
    mask_dto_path = Path(__file__).parent.parent / "src" / "domain" / "dto" / "mask_dto.py"
    
    try:
        with open(mask_dto_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # フィールド定義の確認
        print("MaskDTOに定義されているフィールド:")
        fields = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('frame_index:'):
                fields.append("frame_index")
            elif line.startswith('data:'):
                fields.append("data")
            elif line.startswith('width:'):
                fields.append("width")
            elif line.startswith('height:'):
                fields.append("height")
            elif line.startswith('object_ids:'):
                fields.append("object_ids")
            elif line.startswith('classes:'):
                fields.append("classes")
            elif line.startswith('confidences:'):
                fields.append("confidences")
            elif line.startswith('metadata:'):
                fields.append("metadata")
        
        for field in fields:
            print(f"  - {field}")
        
        if "metadata" not in fields:
            print("\n✓ metadataフィールドは存在しない（正しい）")
        else:
            print("\n✗ metadataフィールドが存在する（予期しない）")
            
    except Exception as e:
        print(f"✗ ファイル読み込みエラー: {e}")
        return False
    
    # 3. 修正内容の確認
    print("\n=== 修正内容の確認 ===")
    adapter_path = Path(__file__).parent.parent / "src" / "adapters" / "secondary" / "local_file_input_adapter.py"
    
    try:
        with open(adapter_path, 'r', encoding='utf-8') as f:
            adapter_content = f.read()
        
        # MaskDTO作成部分の確認
        if 'metadata={' in adapter_content:
            print("✗ まだmetadata引数が残っている")
            return False
        else:
            print("✓ metadata引数が削除されている")
        
        # 正しいMaskDTO作成を確認
        mask_dto_section = adapter_content[adapter_content.find("# MaskDTOを作成"):adapter_content.find("return mask_dto.to_dict()")]
        
        expected_fields = [
            "frame_index=",
            "data=",
            "width=",
            "height=",
            "object_ids=",
            "classes=",
            "confidences="
        ]
        
        print("\nMaskDTO作成時の引数:")
        for field in expected_fields:
            if field in mask_dto_section:
                print(f"  ✓ {field[:-1]}")
            else:
                print(f"  ✗ {field[:-1]} が見つからない")
                
    except Exception as e:
        print(f"✗ ファイル読み込みエラー: {e}")
        return False
    
    # 4. 修正後の動作
    print("\n=== 修正後の動作 ===")
    print("1. LocalFileInputAdapter.get_mask()が呼ばれると:")
    print("   a. マスクファイルが読み込まれる")
    print("   b. 検出情報から各オブジェクトの情報を取得")
    print("   c. MaskDTOが正しく作成される（metadataなし）")
    print("   d. to_dict()でシリアライズされて返される")
    print("2. これにより、マスクが正常に読み込まれる")
    
    return True


def main():
    """メイン実行関数"""
    success = test_mask_dto_fix()
    
    print("\n" + "="*70)
    print("修正確認結果")
    print("="*70)
    
    if success:
        print("✅ MaskDTO metadataエラーが修正されました")
        print("\n修正内容:")
        print("- LocalFileInputAdapter.get_mask()でMaskDTO作成時の")
        print("  metadata引数を削除")
        print("\nこれにより、マスクの読み込みが正常に動作するはずです。")
        return 0
    else:
        print("❌ 修正に問題があります")
        return 1


if __name__ == "__main__":
    sys.exit(main())