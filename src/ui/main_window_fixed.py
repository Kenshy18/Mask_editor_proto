#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メインウィンドウ（修正版）

初期化の問題を回避したバージョン
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel

from core.models import Project

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """メインウィンドウクラス（修正版）"""
    
    # シグナル
    project_changed = pyqtSignal(Project)
    
    def __init__(self, di_container=None):
        """初期化（シンプル版）"""
        logger.info("MainWindow.__init__ 開始")
        
        # 親クラスの初期化
        super().__init__()
        logger.info("QMainWindow.__init__ 完了")
        
        # 基本属性のみ設定
        self.di_container = di_container
        self.current_project = None
        self.is_modified = False
        self.input_data_source = None
        
        # 設定
        self.settings = QSettings("MaskEditorGOD", "MainWindow")
        
        # 最小限のUI設定
        self.setWindowTitle("Mask Editor GOD - 診断モード")
        self.resize(1200, 800)
        
        # 中央ウィジェット
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # レイアウト
        layout = QVBoxLayout(central_widget)
        
        # テキストラベル
        label = QLabel(
            "MainWindowの初期化で問題が発生しています。\n"
            "診断モードで起動しました。\n\n"
            "考えられる原因:\n"
            "- UIコンポーネントの初期化エラー\n"
            "- リソースモニタリングの問題\n"
            "- ウィンドウ状態の復元エラー",
            self
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        logger.info("MainWindow.__init__ 完了")
    
    def closeEvent(self, event):
        """終了時の処理（シンプル版）"""
        event.accept()