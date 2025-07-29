#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスク編集パネル

モルフォロジー操作などのマスク編集UIを提供。
"""
from __future__ import annotations

import logging
from typing import Optional, Dict
from enum import Enum

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QSlider, QLabel, QComboBox,
    QSpinBox, QCheckBox, QGridLayout
)

from ui.i18n import tr

logger = logging.getLogger(__name__)


class MorphologyOperation(Enum):
    """モルフォロジー操作の種類"""
    DILATE = "dilate"
    ERODE = "erode"
    OPEN = "open"
    CLOSE = "close"


class MaskEditPanel(QWidget):
    """マスク編集パネル
    
    モルフォロジー操作のUI提供。
    リアルタイムプレビュー機能付き。
    """
    
    # シグナル
    morphology_requested = pyqtSignal(str, int, bool)  # 操作種別、カーネルサイズ、プレビューフラグ
    morphology_applied = pyqtSignal(str, int)  # 操作種別、カーネルサイズ
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 現在の設定
        self.current_operation = MorphologyOperation.DILATE
        self.kernel_size = 3
        self.preview_enabled = True
        
        # UI初期化
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # タイトル
        title_label = QLabel(tr("mask_edit.title"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # モルフォロジー操作グループ
        morph_group = self._create_morphology_group()
        layout.addWidget(morph_group)
        
        # 編集履歴グループ
        history_group = self._create_history_group()
        layout.addWidget(history_group)
        
        # ストレッチを追加
        layout.addStretch()
    
    def _create_morphology_group(self) -> QGroupBox:
        """モルフォロジー操作グループを作成"""
        group = QGroupBox(tr("mask_edit.morphology"))
        layout = QVBoxLayout(group)
        
        # 操作選択
        operation_layout = QHBoxLayout()
        operation_label = QLabel(tr("mask_edit.operation"))
        self.operation_combo = QComboBox()
        self.operation_combo.addItems([
            tr("mask_edit.dilate"),
            tr("mask_edit.erode"),
            tr("mask_edit.open"),
            tr("mask_edit.close")
        ])
        self.operation_combo.setCurrentIndex(0)
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)
        
        operation_layout.addWidget(operation_label)
        operation_layout.addWidget(self.operation_combo)
        operation_layout.addStretch()
        layout.addLayout(operation_layout)
        
        # カーネルサイズ
        kernel_layout = QHBoxLayout()
        kernel_label = QLabel(tr("mask_edit.kernel_size"))
        self.kernel_slider = QSlider(Qt.Orientation.Horizontal)
        self.kernel_slider.setRange(1, 21)
        self.kernel_slider.setSingleStep(2)
        self.kernel_slider.setPageStep(2)
        self.kernel_slider.setValue(3)
        self.kernel_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.kernel_slider.setTickInterval(2)
        
        self.kernel_spinbox = QSpinBox()
        self.kernel_spinbox.setRange(1, 21)
        self.kernel_spinbox.setSingleStep(2)
        self.kernel_spinbox.setValue(3)
        
        # スライダーとスピンボックスを同期
        self.kernel_slider.valueChanged.connect(self._on_kernel_slider_changed)
        self.kernel_spinbox.valueChanged.connect(self._on_kernel_spinbox_changed)
        
        kernel_layout.addWidget(kernel_label)
        kernel_layout.addWidget(self.kernel_slider, 1)
        kernel_layout.addWidget(self.kernel_spinbox)
        layout.addLayout(kernel_layout)
        
        # プレビューチェックボックス
        self.preview_checkbox = QCheckBox(tr("mask_edit.preview"))
        self.preview_checkbox.setChecked(True)
        self.preview_checkbox.toggled.connect(self._on_preview_toggled)
        layout.addWidget(self.preview_checkbox)
        
        # 適用ボタン
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton(tr("mask_edit.apply"))
        self.apply_button.clicked.connect(self._on_apply_clicked)
        self.reset_button = QPushButton(tr("mask_edit.reset"))
        self.reset_button.clicked.connect(self._on_reset_clicked)
        
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)
        
        return group
    
    def _create_history_group(self) -> QGroupBox:
        """編集履歴グループを作成"""
        group = QGroupBox(tr("mask_edit.history"))
        layout = QHBoxLayout(group)
        
        self.undo_button = QPushButton(tr("mask_edit.undo"))
        self.undo_button.clicked.connect(self.undo_requested)
        
        self.redo_button = QPushButton(tr("mask_edit.redo"))
        self.redo_button.clicked.connect(self.redo_requested)
        
        layout.addWidget(self.undo_button)
        layout.addWidget(self.redo_button)
        layout.addStretch()
        
        return group
    
    def _on_operation_changed(self, index: int) -> None:
        """操作種別が変更された"""
        operations = list(MorphologyOperation)
        self.current_operation = operations[index]
        
        if self.preview_enabled:
            self._request_preview()
    
    def _on_kernel_slider_changed(self, value: int) -> None:
        """カーネルスライダーが変更された"""
        # 奇数値に調整
        if value % 2 == 0:
            value += 1
            self.kernel_slider.setValue(value)
        
        self.kernel_size = value
        self.kernel_spinbox.setValue(value)
        
        if self.preview_enabled:
            self._request_preview()
    
    def _on_kernel_spinbox_changed(self, value: int) -> None:
        """カーネルスピンボックスが変更された"""
        # 奇数値に調整
        if value % 2 == 0:
            value += 1
            self.kernel_spinbox.setValue(value)
        
        self.kernel_size = value
        self.kernel_slider.setValue(value)
        
        if self.preview_enabled:
            self._request_preview()
    
    def _on_preview_toggled(self, checked: bool) -> None:
        """プレビューが切り替えられた"""
        self.preview_enabled = checked
        
        if checked:
            self._request_preview()
        else:
            # プレビューをリセット
            self.morphology_requested.emit("reset", 0, False)
    
    def _on_apply_clicked(self) -> None:
        """適用ボタンがクリックされた"""
        self.morphology_applied.emit(
            self.current_operation.value,
            self.kernel_size
        )
    
    def _on_reset_clicked(self) -> None:
        """リセットボタンがクリックされた"""
        # デフォルト値に戻す
        self.operation_combo.setCurrentIndex(0)
        self.kernel_slider.setValue(3)
        self.preview_checkbox.setChecked(True)
        
        # プレビューをリセット
        self.morphology_requested.emit("reset", 0, False)
    
    def _request_preview(self) -> None:
        """プレビューをリクエスト"""
        self.morphology_requested.emit(
            self.current_operation.value,
            self.kernel_size,
            True
        )
    
    def set_undo_enabled(self, enabled: bool) -> None:
        """Undoボタンの有効/無効を設定"""
        self.undo_button.setEnabled(enabled)
    
    def set_redo_enabled(self, enabled: bool) -> None:
        """Redoボタンの有効/無効を設定"""
        self.redo_button.setEnabled(enabled)
    
    def get_current_settings(self) -> Dict[str, any]:
        """現在の設定を取得"""
        return {
            "operation": self.current_operation.value,
            "kernel_size": self.kernel_size,
            "preview_enabled": self.preview_enabled
        }