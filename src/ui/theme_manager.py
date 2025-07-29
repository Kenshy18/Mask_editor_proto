#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テーママネージャー

アプリケーションのビジュアルテーマを管理し、
モダンで洗練されたUIを提供する。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from PyQt6.QtGui import QPalette, QColor, QFont, QIcon
from PyQt6.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)


@dataclass
class ColorScheme:
    """カラースキーマ定義"""
    # 基本色
    primary: str = "#2979FF"          # プライマリーブルー
    primary_light: str = "#5393FF"
    primary_dark: str = "#0052CC"
    
    secondary: str = "#FF6B6B"        # セカンダリーレッド
    secondary_light: str = "#FF8787"
    secondary_dark: str = "#FA5252"
    
    # 背景色
    background: str = "#1E1E1E"       # メイン背景（ダーク）
    surface: str = "#252525"          # サーフェス
    surface_light: str = "#2D2D2D"
    
    # テキスト色
    text_primary: str = "#E0E0E0"
    text_secondary: str = "#B0B0B0"
    text_disabled: str = "#606060"
    
    # 機能色
    success: str = "#4CAF50"
    warning: str = "#FF9800"
    error: str = "#F44336"
    info: str = "#2196F3"
    
    # UI要素色
    border: str = "#404040"
    divider: str = "#303030"
    hover: str = "#353535"
    selected: str = "#3F3F3F"
    focus: str = "#5393FF"
    
    # マスクオーバーレイ用
    mask_colors: Dict[str, str] = field(default_factory=lambda: {
        "face": "#FF6B6B",
        "genital": "#2979FF",
        "default": "#4CAF50"
    })


@dataclass
class Typography:
    """タイポグラフィ設定"""
    font_family: str = "Noto Sans CJK JP"
    font_size_base: int = 10
    font_size_h1: int = 24
    font_size_h2: int = 20
    font_size_h3: int = 16
    font_size_h4: int = 14
    font_size_small: int = 8
    
    font_weight_regular: int = 400
    font_weight_medium: int = 500
    font_weight_bold: int = 700


class ThemeManager(QObject):
    """テーママネージャー
    
    アプリケーション全体のビジュアルテーマを管理。
    ダークテーマをベースにした映像編集ソフト向けのデザイン。
    """
    
    # シグナル
    theme_changed = pyqtSignal(str)  # テーマ名
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MaskEditorGOD", "Theme")
        self.current_theme = "dark"
        self.color_scheme = ColorScheme()
        self.typography = Typography()
        self.custom_themes: Dict[str, Dict[str, Any]] = {}
        
        # カスタムテーマの読み込み
        self._load_custom_themes()
    
    def apply_theme(self, app: QApplication, theme_name: str = "dark") -> None:
        """テーマを適用
        
        Args:
            app: アプリケーションインスタンス
            theme_name: テーマ名（"dark", "light", "custom"等）
        """
        self.current_theme = theme_name
        
        # カラースキームの更新
        if theme_name in self.custom_themes:
            self._apply_custom_theme(theme_name)
        elif theme_name == "dark":
            self._apply_dark_theme()
        elif theme_name == "light":
            self._apply_light_theme()
        else:
            logger.warning(f"Unknown theme: {theme_name}, using dark theme")
            self._apply_dark_theme()
        
        # スタイルシートの適用
        stylesheet = self._generate_stylesheet()
        app.setStyleSheet(stylesheet)
        
        # パレットの設定
        palette = self._generate_palette()
        app.setPalette(palette)
        
        # フォントの設定
        font = self._generate_font()
        app.setFont(font)
        
        # 設定の保存
        self.settings.setValue("current_theme", theme_name)
        
        # シグナルの発行
        self.theme_changed.emit(theme_name)
    
    def _apply_dark_theme(self) -> None:
        """ダークテーマを適用"""
        self.color_scheme = ColorScheme()  # デフォルトがダークテーマ
    
    def _apply_light_theme(self) -> None:
        """ライトテーマを適用"""
        self.color_scheme = ColorScheme(
            primary="#1976D2",
            primary_light="#42A5F5",
            primary_dark="#0D47A1",
            
            secondary="#D32F2F",
            secondary_light="#EF5350",
            secondary_dark="#C62828",
            
            background="#FAFAFA",
            surface="#FFFFFF",
            surface_light="#F5F5F5",
            
            text_primary="#212121",
            text_secondary="#757575",
            text_disabled="#BDBDBD",
            
            border="#E0E0E0",
            divider="#EEEEEE",
            hover="#F5F5F5",
            selected="#E3F2FD",
            focus="#1976D2"
        )
    
    def _apply_custom_theme(self, theme_name: str) -> None:
        """カスタムテーマを適用"""
        theme_data = self.custom_themes.get(theme_name, {})
        colors = theme_data.get("colors", {})
        
        # カラースキームの更新
        for attr, value in colors.items():
            if hasattr(self.color_scheme, attr):
                setattr(self.color_scheme, attr, value)
    
    def _generate_stylesheet(self) -> str:
        """スタイルシートを生成"""
        c = self.color_scheme
        t = self.typography
        
        return f"""
        /* グローバル設定 */
        * {{
            font-family: "{t.font_family}";
            font-size: {t.font_size_base}pt;
            color: {c.text_primary};
            background-color: transparent;
        }}
        
        /* メインウィンドウ */
        QMainWindow {{
            background-color: {c.background};
        }}
        
        /* メニューバー */
        QMenuBar {{
            background-color: {c.surface};
            border-bottom: 1px solid {c.border};
            padding: 4px;
        }}
        
        QMenuBar::item {{
            padding: 4px 12px;
            background-color: transparent;
            border-radius: 4px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {c.hover};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {c.selected};
        }}
        
        /* メニュー */
        QMenu {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 6px 20px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {c.hover};
            color: {c.text_primary};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {c.divider};
            margin: 4px 10px;
        }}
        
        /* ツールバー */
        QToolBar {{
            background-color: {c.surface};
            border: none;
            padding: 4px;
            spacing: 4px;
        }}
        
        QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 6px;
            margin: 2px;
        }}
        
        QToolButton:hover {{
            background-color: {c.hover};
            border-color: {c.border};
        }}
        
        QToolButton:pressed {{
            background-color: {c.selected};
        }}
        
        QToolButton:checked {{
            background-color: {c.selected};
            border-color: {c.primary};
        }}
        
        /* ステータスバー */
        QStatusBar {{
            background-color: {c.surface};
            border-top: 1px solid {c.border};
            color: {c.text_secondary};
        }}
        
        /* ドックウィジェット */
        QDockWidget {{
            color: {c.text_primary};
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
            /* titlebar-close-icon: url(:/icons/close.svg); */
            /* titlebar-normal-icon: url(:/icons/dock.svg); */
        }}
        
        QDockWidget::title {{
            background-color: {c.surface_light};
            padding: 8px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
        
        /* タブ */
        QTabWidget::pane {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
        }}
        
        QTabBar::tab {{
            background-color: {c.surface_light};
            color: {c.text_secondary};
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {c.surface};
            color: {c.text_primary};
        }}
        
        QTabBar::tab:hover {{
            background-color: {c.hover};
        }}
        
        /* ボタン */
        QPushButton {{
            background-color: {c.surface_light};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: {t.font_weight_medium};
        }}
        
        QPushButton:hover {{
            background-color: {c.hover};
            border-color: {c.primary};
        }}
        
        QPushButton:pressed {{
            background-color: {c.selected};
        }}
        
        QPushButton:disabled {{
            background-color: {c.surface};
            color: {c.text_disabled};
            border-color: {c.border};
        }}
        
        QPushButton[primary="true"] {{
            background-color: {c.primary};
            border-color: {c.primary};
            color: white;
        }}
        
        QPushButton[primary="true"]:hover {{
            background-color: {c.primary_light};
        }}
        
        QPushButton[primary="true"]:pressed {{
            background-color: {c.primary_dark};
        }}
        
        /* スライダー */
        QSlider::groove:horizontal {{
            background-color: {c.surface_light};
            height: 6px;
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background-color: {c.primary};
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background-color: {c.primary_light};
        }}
        
        /* スピンボックス */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.surface_light};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c.focus};
        }}
        
        /* コンボボックス */
        QComboBox {{
            background-color: {c.surface_light};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        
        QComboBox:hover {{
            border-color: {c.primary};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            /* image: url(:/icons/arrow-down.svg); */
            width: 12px;
            height: 12px;
        }}
        
        /* スクロールバー */
        QScrollBar:vertical {{
            background-color: {c.background};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c.surface_light};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c.hover};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        /* プログレスバー */
        QProgressBar {{
            background-color: {c.surface_light};
            border: 1px solid {c.border};
            border-radius: 4px;
            text-align: center;
            height: 20px;
        }}
        
        QProgressBar::chunk {{
            background-color: {c.primary};
            border-radius: 3px;
        }}
        
        /* グループボックス */
        QGroupBox {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
            margin-top: 8px;
            padding-top: 16px;
            font-weight: {t.font_weight_medium};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            background-color: {c.surface};
            color: {c.text_primary};
        }}
        
        /* ツールチップ */
        QToolTip {{
            background-color: {c.surface_light};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        
        /* 特殊ウィジェット用カスタムスタイル */
        
        /* タイムライン */
        TimelineWidget {{
            background-color: {c.background};
            border: 1px solid {c.border};
        }}
        
        /* ビデオプレビュー */
        VideoWithMaskWidget {{
            background-color: black;
            border: 2px solid {c.border};
            border-radius: 8px;
        }}
        
        /* マスクエディタパネル */
        MaskEditPanel {{
            background-color: {c.surface};
        }}
        
        /* エフェクトパネル */
        EffectPanel {{
            background-color: {c.surface};
        }}
        """
    
    def _generate_palette(self) -> QPalette:
        """パレットを生成"""
        palette = QPalette()
        c = self.color_scheme
        
        # ウィンドウ
        palette.setColor(QPalette.ColorRole.Window, QColor(c.background))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(c.text_primary))
        
        # ベース
        palette.setColor(QPalette.ColorRole.Base, QColor(c.surface))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(c.surface_light))
        
        # テキスト
        palette.setColor(QPalette.ColorRole.Text, QColor(c.text_primary))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(c.text_primary))
        
        # ボタン
        palette.setColor(QPalette.ColorRole.Button, QColor(c.surface_light))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(c.text_primary))
        
        # ハイライト
        palette.setColor(QPalette.ColorRole.Highlight, QColor(c.primary))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        
        # リンク
        palette.setColor(QPalette.ColorRole.Link, QColor(c.primary))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(c.primary_dark))
        
        return palette
    
    def _generate_font(self) -> QFont:
        """フォントを生成"""
        font = QFont(self.typography.font_family)
        font.setPointSize(self.typography.font_size_base)
        font.setWeight(self.typography.font_weight_regular)
        return font
    
    def _load_custom_themes(self) -> None:
        """カスタムテーマを読み込み"""
        themes_dir = Path(__file__).parent.parent.parent / "resources" / "themes"
        if not themes_dir.exists():
            return
        
        for theme_file in themes_dir.glob("*.json"):
            try:
                with open(theme_file, "r", encoding="utf-8") as f:
                    theme_data = json.load(f)
                    theme_name = theme_file.stem
                    self.custom_themes[theme_name] = theme_data
                    logger.info(f"Loaded custom theme: {theme_name}")
            except Exception as e:
                logger.error(f"Failed to load theme {theme_file}: {e}")
    
    def get_color(self, color_name: str) -> str:
        """色を取得
        
        Args:
            color_name: 色名（"primary", "background"等）
            
        Returns:
            16進数カラーコード
        """
        return getattr(self.color_scheme, color_name, "#000000")
    
    def get_mask_color(self, mask_type: str) -> str:
        """マスクタイプ別の色を取得
        
        Args:
            mask_type: マスクタイプ（"face", "genital"等）
            
        Returns:
            16進数カラーコード
        """
        return self.color_scheme.mask_colors.get(mask_type, self.color_scheme.mask_colors["default"])
    
    def save_theme_preference(self, theme_name: str) -> None:
        """テーマ設定を保存"""
        self.settings.setValue("current_theme", theme_name)
    
    def load_theme_preference(self) -> str:
        """保存されたテーマ設定を読み込み"""
        return self.settings.value("current_theme", "dark", type=str)


# グローバルインスタンス
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """テーママネージャーのシングルトンインスタンスを取得"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager