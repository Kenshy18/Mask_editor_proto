# フォントディレクトリ

このディレクトリには日本語フォントファイルを配置してください。

## 必要なフォント

- `NotoSansCJKjp-Regular.otf` - Noto Sans CJK JP Regular

## フォントの入手方法

1. Google Fontsから無料でダウンロード可能：
   https://fonts.google.com/noto/specimen/Noto+Sans+JP

2. または、以下のスクリプトを実行：
   ```bash
   cd scripts
   ./download_fonts.sh
   ```

## 注意事項

- フォントファイルはライセンスの関係でリポジトリには含まれていません
- 初回実行時にフォントがない場合は、システムフォントにフォールバックします
- フォントファイルは.gitignoreで除外されています