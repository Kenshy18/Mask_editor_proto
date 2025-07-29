#!/bin/bash

# フォントダウンロードスクリプト
# Noto Sans CJK JPフォントをダウンロード

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FONTS_DIR="$PROJECT_ROOT/resources/fonts"

echo "Noto Sans CJK JP フォントをダウンロードしています..."

# フォントディレクトリが存在しない場合は作成
mkdir -p "$FONTS_DIR"

# Noto Sans CJK JPをダウンロード
FONT_URL="https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
FONT_FILE="$FONTS_DIR/NotoSansCJKjp-Regular.otf"

if [ -f "$FONT_FILE" ]; then
    echo "フォントは既に存在します: $FONT_FILE"
else
    echo "フォントをダウンロード中: $FONT_FILE"
    curl -L -o "$FONT_FILE" "$FONT_URL"
    echo "ダウンロード完了！"
fi

# 権限を設定
chmod 644 "$FONT_FILE" 2>/dev/null || true

echo "フォントのセットアップが完了しました！"