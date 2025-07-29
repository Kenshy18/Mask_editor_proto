#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アイコンマネージャー

アプリケーションのアイコンを管理し、
テーマに応じた適切なアイコンを提供する。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import QSize, Qt, QPoint
from PyQt6.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)


@dataclass
class IconSet:
    """アイコンセット定義"""
    # ファイルメニュー
    new_project: str = "file-plus"
    open_project: str = "folder-open"
    save_project: str = "save"
    save_as: str = "save-as"
    import_video: str = "video-plus"
    export_video: str = "video-export"
    exit: str = "exit"
    
    # 編集メニュー
    undo: str = "undo"
    redo: str = "redo"
    cut: str = "scissors"
    copy: str = "copy"
    paste: str = "clipboard"
    delete: str = "trash"
    select_all: str = "select-all"
    settings: str = "settings"
    
    # 表示メニュー
    zoom_in: str = "zoom-in"
    zoom_out: str = "zoom-out"
    zoom_fit: str = "maximize"
    zoom_100: str = "search"
    fullscreen: str = "fullscreen"
    
    # プレイバック
    play: str = "play"
    pause: str = "pause"
    stop: str = "stop"
    next_frame: str = "skip-forward"
    prev_frame: str = "skip-back"
    loop: str = "repeat"
    
    # ツール
    brush: str = "brush"
    eraser: str = "eraser"
    select: str = "cursor"
    hand: str = "hand"
    
    # マスク編集
    dilate: str = "expand"
    erode: str = "compress"
    mask_open: str = "mask-open"
    mask_close: str = "mask-close"
    
    # エフェクト
    mosaic: str = "grid"
    blur: str = "blur"
    pixelate: str = "pixels"
    
    # UI要素
    dock: str = "dock"
    close: str = "x"
    menu: str = "menu"
    more: str = "more-horizontal"
    info: str = "info"
    warning: str = "alert-triangle"
    error: str = "alert-circle"
    success: str = "check-circle"
    
    # その他
    folder: str = "folder"
    file: str = "file"
    video: str = "video"
    image: str = "image"
    audio: str = "volume-2"
    timeline: str = "timeline"
    layers: str = "layers"
    
    # 矢印
    arrow_up: str = "chevron-up"
    arrow_down: str = "chevron-down"
    arrow_left: str = "chevron-left"
    arrow_right: str = "chevron-right"


class IconManager:
    """アイコンマネージャー
    
    アイコンの読み込み、キャッシュ、テーマ対応を管理。
    SVGアイコンをベースに、動的な色変更をサポート。
    """
    
    def __init__(self):
        self.icon_set = IconSet()
        self.icon_cache: Dict[str, QIcon] = {}
        self.icon_dir = Path(__file__).parent.parent.parent / "resources" / "icons"
        self.fallback_icon_dir = self.icon_dir / "fallback"
        
        # デフォルトアイコンカラー
        self.default_color = QColor("#E0E0E0")
        self.hover_color = QColor("#FFFFFF")
        self.disabled_color = QColor("#606060")
        self.primary_color = QColor("#2979FF")
        
        # アイコンが存在しない場合のフォールバック
        self._ensure_icon_directory()
    
    def _ensure_icon_directory(self) -> None:
        """アイコンディレクトリを確保"""
        self.icon_dir.mkdir(parents=True, exist_ok=True)
        self.fallback_icon_dir.mkdir(parents=True, exist_ok=True)
        
        # フォールバックアイコンを生成
        self._generate_fallback_icons()
    
    def _generate_fallback_icons(self) -> None:
        """フォールバックアイコンを生成"""
        # ここでは基本的な図形でアイコンを生成
        basic_icons = {
            "default": self._create_default_icon,
            "play": self._create_play_icon,
            "pause": self._create_pause_icon,
            "stop": self._create_stop_icon,
            "folder": self._create_folder_icon,
            "file": self._create_file_icon,
        }
        
        for name, creator in basic_icons.items():
            icon_path = self.fallback_icon_dir / f"{name}.png"
            if not icon_path.exists():
                pixmap = creator()
                pixmap.save(str(icon_path))
    
    def get_icon(self, icon_name: str, color: Optional[QColor] = None, size: QSize = QSize(24, 24)) -> QIcon:
        """アイコンを取得
        
        Args:
            icon_name: アイコン名
            color: アイコンの色（Noneの場合はデフォルト色）
            size: アイコンサイズ
            
        Returns:
            QIcon
        """
        if color is None:
            color = self.default_color
        
        # キャッシュキー
        cache_key = f"{icon_name}_{color.name()}_{size.width()}x{size.height()}"
        
        # キャッシュチェック
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        # アイコンの読み込み
        icon = self._load_icon(icon_name, color, size)
        
        # キャッシュに保存
        self.icon_cache[cache_key] = icon
        
        return icon
    
    def _load_icon(self, icon_name: str, color: QColor, size: QSize) -> QIcon:
        """アイコンを読み込み
        
        SVGファイルを優先し、なければPNGを探す。
        見つからない場合はフォールバックアイコンを使用。
        """
        # SVGファイルを探す
        svg_path = self.icon_dir / f"{icon_name}.svg"
        if svg_path.exists():
            return self._load_svg_icon(svg_path, color, size)
        
        # PNGファイルを探す
        png_path = self.icon_dir / f"{icon_name}.png"
        if png_path.exists():
            return self._load_png_icon(png_path, color, size)
        
        # フォールバックアイコンを探す
        fallback_path = self.fallback_icon_dir / f"{icon_name}.png"
        if fallback_path.exists():
            return self._load_png_icon(fallback_path, color, size)
        
        # デフォルトアイコンを返す
        default_path = self.fallback_icon_dir / "default.png"
        if default_path.exists():
            return self._load_png_icon(default_path, color, size)
        
        # 何もない場合は空のアイコン
        return QIcon()
    
    def _load_svg_icon(self, path: Path, color: QColor, size: QSize) -> QIcon:
        """SVGアイコンを読み込み、色を適用"""
        renderer = QSvgRenderer(str(path))
        
        # 通常状態のピクスマップ
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # SVGの色を変更（単色の場合）
        renderer.render(painter)
        painter.end()
        
        # 色を適用
        colored_pixmap = self._apply_color_to_pixmap(pixmap, color)
        
        # アイコンを作成
        icon = QIcon()
        icon.addPixmap(colored_pixmap, QIcon.Mode.Normal, QIcon.State.Off)
        
        # ホバー状態
        hover_pixmap = self._apply_color_to_pixmap(pixmap, self.hover_color)
        icon.addPixmap(hover_pixmap, QIcon.Mode.Active, QIcon.State.Off)
        
        # 無効状態
        disabled_pixmap = self._apply_color_to_pixmap(pixmap, self.disabled_color)
        icon.addPixmap(disabled_pixmap, QIcon.Mode.Disabled, QIcon.State.Off)
        
        return icon
    
    def _load_png_icon(self, path: Path, color: QColor, size: QSize) -> QIcon:
        """PNGアイコンを読み込み"""
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            # 色を適用
            colored_pixmap = self._apply_color_to_pixmap(pixmap, color)
            
            icon = QIcon()
            icon.addPixmap(colored_pixmap)
            return icon
        
        return QIcon()
    
    def _apply_color_to_pixmap(self, pixmap: QPixmap, color: QColor) -> QPixmap:
        """ピクスマップに色を適用"""
        colored = QPixmap(pixmap.size())
        colored.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(colored)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.drawPixmap(0, 0, pixmap)
        
        # 色をオーバーレイ
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(colored.rect(), color)
        painter.end()
        
        return colored
    
    # フォールバックアイコン生成メソッド
    def _create_default_icon(self) -> QPixmap:
        """デフォルトアイコンを生成"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.default_color)
        painter.drawRect(4, 4, 16, 16)
        painter.end()
        
        return pixmap
    
    def _create_play_icon(self) -> QPixmap:
        """再生アイコンを生成"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.default_color)
        
        # 三角形を描画
        points = [
            (8, 6),
            (8, 18),
            (18, 12)
        ]
        painter.drawPolygon([QPoint(x, y) for x, y in points])
        painter.end()
        
        return pixmap
    
    def _create_pause_icon(self) -> QPixmap:
        """一時停止アイコンを生成"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.default_color)
        
        # 2本の縦線
        painter.drawRect(7, 6, 3, 12)
        painter.drawRect(14, 6, 3, 12)
        painter.end()
        
        return pixmap
    
    def _create_stop_icon(self) -> QPixmap:
        """停止アイコンを生成"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.default_color)
        
        # 正方形
        painter.drawRect(6, 6, 12, 12)
        painter.end()
        
        return pixmap
    
    def _create_folder_icon(self) -> QPixmap:
        """フォルダアイコンを生成"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.default_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # フォルダの形
        painter.drawRect(4, 8, 16, 12)
        painter.drawRect(4, 6, 8, 2)
        painter.end()
        
        return pixmap
    
    def _create_file_icon(self) -> QPixmap:
        """ファイルアイコンを生成"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.default_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # ドキュメントの形
        painter.drawRect(6, 4, 12, 16)
        painter.drawLine(14, 4, 18, 8)
        painter.drawLine(18, 8, 18, 20)
        painter.end()
        
        return pixmap
    
    def update_theme_colors(self, primary: str, text_primary: str, text_disabled: str) -> None:
        """テーマカラーを更新
        
        Args:
            primary: プライマリーカラー
            text_primary: 通常テキストカラー
            text_disabled: 無効状態のテキストカラー
        """
        self.primary_color = QColor(primary)
        self.default_color = QColor(text_primary)
        self.disabled_color = QColor(text_disabled)
        self.hover_color = QColor(text_primary).lighter(120)
        
        # キャッシュをクリア
        self.icon_cache.clear()


# グローバルインスタンス
_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> IconManager:
    """アイコンマネージャーのシングルトンインスタンスを取得"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager