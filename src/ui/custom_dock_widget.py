#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カスタムドックウィジェット

より洗練されたドックウィジェットのデザインを提供。
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QMouseEvent
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QToolButton, QFrame, QGraphicsDropShadowEffect
)

from .icon_manager import get_icon_manager
from .theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class CustomTitleBar(QWidget):
    """カスタムタイトルバー
    
    ドックウィジェット用のモダンなタイトルバー。
    """
    
    # シグナル
    close_requested = pyqtSignal()
    dock_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._is_active = True
        self._setup_ui()
        self._apply_theme()
        
        # ドラッグ用
        self._drag_pos = None
    
    def _setup_ui(self):
        """UIをセットアップ"""
        self.setFixedHeight(32)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(4)
        
        # タイトルラベル
        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet("font-weight: 500;")
        layout.addWidget(self.title_label)
        
        # スペーサー
        layout.addStretch()
        
        # ボタンサイズ
        button_size = 20
        icon_manager = get_icon_manager()
        
        # 最小化ボタン
        self.minimize_button = QToolButton()
        self.minimize_button.setFixedSize(button_size, button_size)
        self.minimize_button.setIcon(icon_manager.get_icon("minimize", size=QSize(16, 16)))
        self.minimize_button.clicked.connect(self.minimize_requested.emit)
        self.minimize_button.setToolTip("最小化")
        layout.addWidget(self.minimize_button)
        
        # ドックボタン
        self.dock_button = QToolButton()
        self.dock_button.setFixedSize(button_size, button_size)
        self.dock_button.setIcon(icon_manager.get_icon("dock", size=QSize(16, 16)))
        self.dock_button.clicked.connect(self.dock_requested.emit)
        self.dock_button.setToolTip("ドック/フロート切替")
        layout.addWidget(self.dock_button)
        
        # 閉じるボタン
        self.close_button = QToolButton()
        self.close_button.setFixedSize(button_size, button_size)
        self.close_button.setIcon(icon_manager.get_icon("close", size=QSize(16, 16)))
        self.close_button.clicked.connect(self.close_requested.emit)
        self.close_button.setToolTip("閉じる")
        layout.addWidget(self.close_button)
    
    def _apply_theme(self):
        """テーマを適用"""
        theme = get_theme_manager()
        
        # タイトルバーのスタイル
        self.setStyleSheet(f"""
            CustomTitleBar {{
                background-color: {theme.color_scheme.surface_light};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
        """)
        
        # ボタンのスタイル
        button_style = f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 10px;
                padding: 2px;
            }}
            QToolButton:hover {{
                background-color: {theme.color_scheme.hover};
            }}
            QToolButton:pressed {{
                background-color: {theme.color_scheme.selected};
            }}
        """
        
        self.minimize_button.setStyleSheet(button_style)
        self.dock_button.setStyleSheet(button_style)
        
        # 閉じるボタンは特別なスタイル
        close_button_style = f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 10px;
                padding: 2px;
            }}
            QToolButton:hover {{
                background-color: #FA5252;
            }}
            QToolButton:pressed {{
                background-color: #E03131;
            }}
        """
        self.close_button.setStyleSheet(close_button_style)
    
    def set_active(self, active: bool):
        """アクティブ状態を設定"""
        self._is_active = active
        if active:
            self.title_label.setStyleSheet("font-weight: 500; opacity: 1.0;")
        else:
            self.title_label.setStyleSheet("font-weight: 500; opacity: 0.6;")
    
    def set_title(self, title: str):
        """タイトルを設定"""
        self._title = title
        self.title_label.setText(title)
    
    def mousePressEvent(self, event: QMouseEvent):
        """マウス押下イベント"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().pos()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """マウス移動イベント"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            parent_dock = self.parent()
            if isinstance(parent_dock, QDockWidget) and parent_dock.isFloating():
                parent_dock.move(event.globalPosition().toPoint() - self._drag_pos)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """マウスリリースイベント"""
        self._drag_pos = None


class CustomDockWidget(QDockWidget):
    """カスタムドックウィジェット
    
    モダンなデザインのドックウィジェット。
    """
    
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self._setup_ui()
        self._apply_theme()
        self._setup_animations()
    
    def _setup_ui(self):
        """UIをセットアップ"""
        # カスタムタイトルバー
        self.custom_title_bar = CustomTitleBar(self.windowTitle())
        self.setTitleBarWidget(self.custom_title_bar)
        
        # シグナル接続
        self.custom_title_bar.close_requested.connect(self.close)
        self.custom_title_bar.dock_requested.connect(self._toggle_floating)
        self.custom_title_bar.minimize_requested.connect(self._minimize)
        
        # コンテンツコンテナ
        self.content_container = QFrame()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(8)
        
        # ドロップシャドウ効果
        if self.isFloating():
            self._add_shadow()
    
    def _apply_theme(self):
        """テーマを適用"""
        theme = get_theme_manager()
        
        # ドックウィジェットのスタイル
        self.setStyleSheet(f"""
            CustomDockWidget {{
                background-color: {theme.color_scheme.surface};
                border: 1px solid {theme.color_scheme.border};
                border-radius: 8px;
            }}
            
            QFrame#content_container {{
                background-color: {theme.color_scheme.surface};
                border: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
        """)
        
        self.content_container.setObjectName("content_container")
    
    def _setup_animations(self):
        """アニメーションをセットアップ"""
        # 表示/非表示アニメーション
        self.show_animation = QPropertyAnimation(self, b"windowOpacity")
        self.show_animation.setDuration(200)
        self.show_animation.setStartValue(0.0)
        self.show_animation.setEndValue(1.0)
        self.show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_animation = QPropertyAnimation(self, b"windowOpacity")
        self.hide_animation.setDuration(200)
        self.hide_animation.setStartValue(1.0)
        self.hide_animation.setEndValue(0.0)
        self.hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.hide_animation.finished.connect(super().hide)
    
    def _add_shadow(self):
        """ドロップシャドウを追加"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
    
    def _remove_shadow(self):
        """ドロップシャドウを削除"""
        self.setGraphicsEffect(None)
    
    def _toggle_floating(self):
        """フローティング状態を切り替え"""
        self.setFloating(not self.isFloating())
        
        # フローティング時はシャドウを追加
        if self.isFloating():
            self._add_shadow()
        else:
            self._remove_shadow()
    
    def _minimize(self):
        """最小化"""
        if self.isFloating():
            self.showMinimized()
        else:
            # ドック状態では非表示にする
            self.hide()
    
    def setWidget(self, widget: QWidget):
        """ウィジェットを設定"""
        # コンテンツコンテナに追加
        self.content_layout.addWidget(widget)
        super().setWidget(self.content_container)
    
    def show(self):
        """表示（アニメーション付き）"""
        self.setWindowOpacity(0.0)
        super().show()
        self.show_animation.start()
    
    def hide(self):
        """非表示（アニメーション付き）"""
        self.hide_animation.start()
    
    def setWindowTitle(self, title: str):
        """ウィンドウタイトルを設定"""
        super().setWindowTitle(title)
        if hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.set_title(title)
    
    def enterEvent(self, event):
        """マウスエンターイベント"""
        super().enterEvent(event)
        if hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.set_active(True)
    
    def leaveEvent(self, event):
        """マウスリーブイベント"""
        super().leaveEvent(event)
        if hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.set_active(False)


class CollapsibleDockWidget(CustomDockWidget):
    """折りたたみ可能なドックウィジェット
    
    セクションごとに折りたたみ可能なドックウィジェット。
    """
    
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self._sections = []
    
    def add_section(self, title: str, widget: QWidget, expanded: bool = True) -> 'CollapsibleSection':
        """セクションを追加
        
        Args:
            title: セクションタイトル
            widget: セクション内のウィジェット
            expanded: 初期展開状態
            
        Returns:
            追加されたセクション
        """
        section = CollapsibleSection(title, widget, expanded)
        self.content_layout.addWidget(section)
        self._sections.append(section)
        return section
    
    def expand_all(self):
        """すべてのセクションを展開"""
        for section in self._sections:
            section.set_expanded(True)
    
    def collapse_all(self):
        """すべてのセクションを折りたたむ"""
        for section in self._sections:
            section.set_expanded(False)


class CollapsibleSection(QWidget):
    """折りたたみ可能なセクション
    
    クリックで展開/折りたたみができるセクション。
    """
    
    # シグナル
    expanded_changed = pyqtSignal(bool)
    
    def __init__(self, title: str, widget: QWidget, expanded: bool = True):
        super().__init__()
        self._title = title
        self._widget = widget
        self._expanded = expanded
        self._setup_ui()
        self._apply_theme()
        self.set_expanded(expanded)
    
    def _setup_ui(self):
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ヘッダー
        self.header = QWidget()
        self.header.setFixedHeight(28)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 0, 8, 0)
        
        # 展開アイコン
        icon_manager = get_icon_manager()
        self.expand_icon = QLabel()
        self.expand_icon.setFixedSize(16, 16)
        header_layout.addWidget(self.expand_icon)
        
        # タイトル
        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet("font-weight: 500;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        layout.addWidget(self.header)
        
        # コンテンツ
        self.content_widget = self._widget
        layout.addWidget(self.content_widget)
        
        # クリックイベント
        self.header.mousePressEvent = self._on_header_clicked
    
    def _apply_theme(self):
        """テーマを適用"""
        theme = get_theme_manager()
        
        self.header.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.color_scheme.surface_light};
                border-radius: 4px;
            }}
            QWidget:hover {{
                background-color: {theme.color_scheme.hover};
            }}
        """)
    
    def _on_header_clicked(self, event):
        """ヘッダークリック時"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_expanded(not self._expanded)
    
    def set_expanded(self, expanded: bool):
        """展開状態を設定"""
        self._expanded = expanded
        
        # アイコン更新
        icon_manager = get_icon_manager()
        if expanded:
            icon = icon_manager.get_icon("arrow_down", size=QSize(16, 16))
            self.content_widget.show()
        else:
            icon = icon_manager.get_icon("arrow_right", size=QSize(16, 16))
            self.content_widget.hide()
        
        self.expand_icon.setPixmap(icon.pixmap(16, 16))
        
        # シグナル発行
        self.expanded_changed.emit(expanded)
    
    def is_expanded(self) -> bool:
        """展開状態を取得"""
        return self._expanded