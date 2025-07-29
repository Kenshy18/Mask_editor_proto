#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mask Editor Prototype - メインエントリポイント（修正版）

AI生成マスクを基に動画編集を支援するGUIツールのメインモジュール
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
__author__ = "Mask Editor Prototype Development Team"


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """ロギングの設定
    
    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: ログファイルパス（Noneの場合はコンソールのみ）
    """
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
    """コマンドライン引数のパース
    
    Returns:
        パース済みの引数
    """
    parser = argparse.ArgumentParser(
        description="Mask Editor Prototype - AI生成マスクベースの動画編集ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "--project",
        type=str,
        help="開くプロジェクトファイル（.mosaicproj）"
    )
    
    parser.add_argument(
        "--compact",
        action="store_true",
        help="コンパクトレイアウトモードを使用"
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
    
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="GPU高速化を無効化"
    )
    
    parser.add_argument(
        "--lang",
        type=str,
        default="ja",
        choices=["ja", "en", "zh"],
        help="UI言語（デフォルト: ja）"
    )
    
    return parser.parse_args()


def check_requirements() -> bool:
    """必要な環境のチェック
    
    Returns:
        すべての要件を満たしている場合True
    """
    import subprocess
    
    # FFmpegの確認
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logging.error("FFmpegが見つかりません。インストールしてください。")
            return False
    except FileNotFoundError:
        logging.error("FFmpegが見つかりません。インストールしてください。")
        return False
    
    # フォントの確認
    font_path = Path(__file__).parent.parent / "resources" / "fonts" / "NotoSansCJKjp-Regular.otf"
    if not font_path.exists():
        logging.warning(
            f"日本語フォントが見つかりません: {font_path}\n"
            "scripts/download_fonts.sh を実行してダウンロードしてください。"
        )
    
    return True


def main() -> int:
    """メイン関数
    
    Returns:
        終了コード（0: 正常終了、1: エラー）
    """
    # 引数のパース
    args = parse_arguments()
    
    # ロギング設定
    log_level = "DEBUG" if args.debug else args.log_level
    setup_logging(log_level, args.log_file)
    
    logging.info(f"Mask Editor Prototype v{__version__} を起動しています...")
    logging.info(f"OpenCV threads: {cv2.getNumThreads()}")
    
    # 環境チェック
    if not check_requirements():
        return 1
    
    # PyQt6アプリケーションの初期化
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QFontDatabase
        
        # 高DPI対応
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        app = QApplication(sys.argv)
        app.setApplicationName("Mask Editor Prototype")
        app.setOrganizationName("MaskEditorPrototype")
        
        # 日本語フォントの読み込みと設定
        font_path = Path(__file__).parent.parent / "resources" / "fonts" / "NotoSansCJKjp-Regular.otf"
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    # 日本語フォントをアプリケーション全体に設定
                    japanese_font = QFont(font_families[0], 10)
                    app.setFont(japanese_font)
                    logging.info(f"日本語フォントを設定しました: {font_families[0]}")
                    
                    # スタイルシートでもフォントを指定（より確実な適用のため）
                    app.setStyleSheet(f"""
                        * {{
                            font-family: "{font_families[0]}";
                            font-size: 10pt;
                        }}
                        QMenu {{
                            font-family: "{font_families[0]}";
                            font-size: 10pt;
                        }}
                        QMenuBar {{
                            font-family: "{font_families[0]}";
                            font-size: 10pt;
                        }}
                    """)
                else:
                    logging.warning("フォントファミリーの取得に失敗しました")
            else:
                logging.error(f"フォントの読み込みに失敗しました: {font_path}")
        else:
            logging.warning(f"日本語フォントが見つかりません: {font_path}")
        
        # srcディレクトリをパスに追加
        src_dir = Path(__file__).parent
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        
        # DIコンテナの初期化
        from infrastructure.container_config import create_default_container
        from infrastructure.di_container import set_container
        
        # 設定ファイルパスを決定
        config_file = None
        config_dir = Path.home() / ".config" / "mask_editor_god"
        if (config_dir / "config.yaml").exists():
            config_file = config_dir / "config.yaml"
        elif (config_dir / "config.json").exists():
            config_file = config_dir / "config.json"
        
        # コンテナを作成して設定
        logging.debug("Creating default container...")
        container = create_default_container(config_file)
        logging.debug("Container created successfully")
        
        # コマンドライン引数に基づく設定の上書き
        if args.no_gpu:
            logging.debug("Disabling GPU...")
            container.set_config("performance.gpu_enabled", False)
        
        # グローバルコンテナとして設定
        logging.debug("Setting global container...")
        set_container(container)
        logging.debug("Global container set")
        
        # i18nの初期化
        logging.debug("Importing i18n module...")
        from ui.i18n import init_i18n
        logging.debug("i18n module imported")
        logging.debug("Initializing i18n...")
        i18n = init_i18n(app)
        logging.debug("i18n initialized")
        
        # 言語設定
        locale_map = {
            "ja": "ja_JP",
            "en": "en_US",
            "zh": "zh_CN"
        }
        logging.debug(f"Setting locale to {locale_map.get(args.lang, 'ja_JP')}...")
        i18n.set_locale(locale_map.get(args.lang, "ja_JP"))
        logging.debug("Locale set")
        
        # テーマの初期化と適用
        logging.debug("Initializing theme manager...")
        from ui.theme_manager import get_theme_manager
        theme_manager = get_theme_manager()
        
        # 保存されたテーマを読み込むか、デフォルトのダークテーマを使用
        saved_theme = theme_manager.load_theme_preference()
        logging.debug(f"Applying theme: {saved_theme}")
        theme_manager.apply_theme(app, saved_theme)
        logging.debug("Theme applied")
        
        # アイコンマネージャーの初期化
        logging.debug("Initializing icon manager...")
        from ui.icon_manager import get_icon_manager
        icon_manager = get_icon_manager()
        # テーマカラーをアイコンマネージャーに反映
        icon_manager.update_theme_colors(
            theme_manager.color_scheme.primary,
            theme_manager.color_scheme.text_primary,
            theme_manager.color_scheme.text_disabled
        )
        logging.debug("Icon manager initialized")
        
        # メインウィンドウの起動
        try:
            # コンパクトモードの確認
            if args.compact:
                logging.debug("About to import CompactMainWindow...")
                from ui.main_window_compact import CompactMainWindow as MainWindow
                logging.info("コンパクトレイアウトモードを使用します")
            else:
                logging.debug("About to import MainWindow...")
                from ui.main_window_with_import import MainWindowWithImport as MainWindow
                logging.info("インポート機能付きメインウィンドウを使用します")
            
            logging.debug("MainWindow import successful")
            logging.debug("Creating MainWindow instance...")
            window = MainWindow(container)
            logging.debug("MainWindow instance created successfully")
        except Exception as window_error:
            logging.error(f"MainWindow creation failed: {window_error}")
            import traceback
            traceback.print_exc()
            raise
        
        # コマンドライン引数の処理
        if args.project:
            # TODO: プロジェクトファイルを直接開く実装
            pass
        
        logging.debug("About to call window.show()...")
        window.show()
        logging.debug("window.show() called")
        
        logging.info("アプリケーションを起動しました")
        
        logging.debug("About to call app.exec()...")
        result = app.exec()
        logging.debug(f"app.exec() returned {result}")
        return result
        
    except ImportError as e:
        logging.error(f"必要なモジュールのインポートに失敗しました: {e}")
        logging.error("pip install -r requirements.txt を実行してください")
        return 1
    except Exception as e:
        logging.exception(f"予期しないエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())