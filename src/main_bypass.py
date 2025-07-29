#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mask Editor GOD - メインエントリポイント（MainWindowバイパス版）

MainWindowの作成問題を回避するテスト版
"""
import sys
import os

# OpenCV-PyQt6競合を回避（重要：最初に実行）
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '0'
if 'QT_PLUGIN_PATH' in os.environ:
    del os.environ['QT_PLUGIN_PATH']

# OpenCVのスレッドを無効化（PyQt6との競合を防ぐ）
import cv2
cv2.setNumThreads(0)

import argparse
import logging
from pathlib import Path

# バージョン情報
__version__ = "1.0.0"
__author__ = "Mask Editor GOD Development Team"


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """ロギングの設定"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    # PyQt6の過剰なデバッグログを抑制
    logging.getLogger("PyQt6").setLevel(logging.WARNING)


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数のパース"""
    parser = argparse.ArgumentParser(
        description="Mask Editor GOD - AI生成マスクベースの動画編集ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグモードで起動"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="ログレベル（デフォルト: INFO）"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="ログファイルパス"
    )
    
    return parser.parse_args()


def main() -> int:
    """メイン関数（MainWindowバイパス版）"""
    # 引数のパース
    args = parse_arguments()
    
    # ロギング設定
    log_level = "DEBUG" if args.debug else args.log_level
    setup_logging(log_level, args.log_file)
    
    logging.info(f"Mask Editor GOD v{__version__} を起動しています... (バイパス版)")
    logging.info(f"OpenCV threads: {cv2.getNumThreads()}")
    
    # PyQt6アプリケーションの初期化
    try:
        from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
        from PyQt6.QtCore import Qt, QTimer
        
        # 高DPI対応
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        logging.info("QApplication作成中...")
        app = QApplication(sys.argv)
        app.setApplicationName("Mask Editor GOD")
        app.setOrganizationName("MaskEditorGOD")
        logging.info("QApplication作成完了")
        
        # srcディレクトリをパスに追加
        src_dir = Path(__file__).parent
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        
        # DIコンテナの初期化
        logging.info("DIコンテナ作成中...")
        from infrastructure.container_config import create_default_container
        container = create_default_container()
        logging.info("DIコンテナ作成完了")
        
        # i18nの初期化
        logging.info("i18n初期化中...")
        from ui.i18n import init_i18n
        i18n = init_i18n(app)
        i18n.set_locale("ja_JP")
        logging.info("i18n初期化完了")
        
        # MainWindowの代わりに簡単なウィンドウを作成
        logging.info("シンプルなウィンドウを作成中...")
        window = QMainWindow()
        window.setWindowTitle("Mask Editor GOD - 診断モード")
        window.resize(800, 600)
        
        # 中央にラベルを配置
        label = QLabel("MainWindowの作成に問題があります。\n診断モードで起動しました。", window)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        window.setCentralWidget(label)
        
        logging.info("ウィンドウ作成完了")
        
        # ウィンドウを表示
        window.show()
        logging.info("ウィンドウを表示しました")
        
        # 10秒後に終了
        QTimer.singleShot(10000, app.quit)
        logging.info("10秒後に自動終了します")
        
        return app.exec()
        
    except ImportError as e:
        logging.error(f"必要なモジュールのインポートに失敗しました: {e}")
        return 1
    except Exception as e:
        logging.exception(f"予期しないエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())