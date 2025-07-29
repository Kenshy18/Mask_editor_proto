#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コンパクトレイアウト設定

UIをよりコンパクトにするための設定とヘルパー関数
"""
from typing import Dict, Tuple, Optional
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QWidget, QDockWidget, QMainWindow, QTabWidget


class CompactLayoutConfig:
    """コンパクトレイアウトの設定"""
    
    # ウィンドウサイズ
    DEFAULT_WINDOW_SIZE = (960, 540)
    MINIMUM_WINDOW_SIZE = (800, 480)
    
    # ドックウィジェットのサイズ
    DOCK_SIZES = {
        "left": {
            "width": 220,      # 左側ドック幅
            "min_width": 180,
            "max_width": 300
        },
        "right": {
            "width": 280,      # 右側ドック幅
            "min_width": 220,
            "max_width": 400
        },
        "bottom": {
            "height": 120,     # 下側ドック高さ
            "min_height": 80,
            "max_height": 200
        }
    }
    
    # パネルのマージンとスペーシング
    PANEL_MARGINS = (4, 4, 4, 4)  # left, top, right, bottom
    PANEL_SPACING = 4
    
    # フォントサイズ
    COMPACT_FONT_SIZE = 9  # 通常より小さめ
    
    # ボタンサイズ
    COMPACT_BUTTON_SIZE = QSize(24, 24)
    COMPACT_ICON_SIZE = QSize(16, 16)
    
    @staticmethod
    def apply_compact_window_settings(window: QMainWindow) -> None:
        """ウィンドウにコンパクト設定を適用"""
        # ウィンドウサイズ
        window.resize(*CompactLayoutConfig.DEFAULT_WINDOW_SIZE)
        window.setMinimumSize(*CompactLayoutConfig.MINIMUM_WINDOW_SIZE)
        
        # 中央ウィジェットのマージンを削減
        if window.centralWidget():
            window.centralWidget().setContentsMargins(0, 0, 0, 0)
    
    @staticmethod
    def apply_compact_dock_settings(dock: QDockWidget, area: str) -> None:
        """ドックウィジェットにコンパクト設定を適用
        
        Args:
            dock: ドックウィジェット
            area: "left", "right", "bottom"のいずれか
        """
        if area == "left":
            dock.setMaximumWidth(CompactLayoutConfig.DOCK_SIZES["left"]["max_width"])
            dock.setMinimumWidth(CompactLayoutConfig.DOCK_SIZES["left"]["min_width"])
            dock.widget().setMaximumWidth(CompactLayoutConfig.DOCK_SIZES["left"]["max_width"])
        elif area == "right":
            dock.setMaximumWidth(CompactLayoutConfig.DOCK_SIZES["right"]["max_width"])
            dock.setMinimumWidth(CompactLayoutConfig.DOCK_SIZES["right"]["min_width"])
            dock.widget().setMaximumWidth(CompactLayoutConfig.DOCK_SIZES["right"]["max_width"])
        elif area == "bottom":
            dock.setMaximumHeight(CompactLayoutConfig.DOCK_SIZES["bottom"]["max_height"])
            dock.setMinimumHeight(CompactLayoutConfig.DOCK_SIZES["bottom"]["min_height"])
            dock.widget().setMaximumHeight(CompactLayoutConfig.DOCK_SIZES["bottom"]["max_height"])
        
        # ドックのタイトルバーをコンパクトに
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
    
    @staticmethod
    def apply_compact_panel_settings(panel: QWidget) -> None:
        """パネルにコンパクト設定を適用"""
        # マージンとスペーシングを削減
        panel.setContentsMargins(*CompactLayoutConfig.PANEL_MARGINS)
        
        # レイアウトがある場合はスペーシングも調整
        if hasattr(panel, 'layout') and panel.layout():
            panel.layout().setSpacing(CompactLayoutConfig.PANEL_SPACING)
            panel.layout().setContentsMargins(*CompactLayoutConfig.PANEL_MARGINS)
    
    @staticmethod
    def create_tabbed_dock_container(docks: Dict[str, QDockWidget]) -> QTabWidget:
        """複数のドックをタブ化したコンテナを作成
        
        Args:
            docks: タブ名とドックウィジェットの辞書
            
        Returns:
            タブウィジェット
        """
        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)  # よりコンパクトな表示
        tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        
        for title, dock in docks.items():
            if dock.widget():
                tab_widget.addTab(dock.widget(), title)
        
        return tab_widget


def optimize_widget_for_compact_display(widget: QWidget) -> None:
    """ウィジェットをコンパクト表示用に最適化"""
    # フォントサイズを調整
    font = widget.font()
    font.setPointSize(CompactLayoutConfig.COMPACT_FONT_SIZE)
    widget.setFont(font)
    
    # ボタンサイズを調整
    from PyQt6.QtWidgets import QPushButton, QToolButton
    for button in widget.findChildren(QPushButton):
        button.setMaximumHeight(CompactLayoutConfig.COMPACT_BUTTON_SIZE.height())
        if button.icon():
            button.setIconSize(CompactLayoutConfig.COMPACT_ICON_SIZE)
    
    for button in widget.findChildren(QToolButton):
        button.setMaximumSize(CompactLayoutConfig.COMPACT_BUTTON_SIZE)
        button.setIconSize(CompactLayoutConfig.COMPACT_ICON_SIZE)
    
    # スライダーの高さを調整
    from PyQt6.QtWidgets import QSlider
    for slider in widget.findChildren(QSlider):
        if slider.orientation() == Qt.Orientation.Horizontal:
            slider.setMaximumHeight(20)
    
    # コンボボックスの高さを調整
    from PyQt6.QtWidgets import QComboBox
    for combo in widget.findChildren(QComboBox):
        combo.setMaximumHeight(24)
    
    # スピンボックスの高さを調整
    from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox
    for spin in widget.findChildren(QSpinBox):
        spin.setMaximumHeight(24)
    for spin in widget.findChildren(QDoubleSpinBox):
        spin.setMaximumHeight(24)