#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コンパクトブラシツールパネル

画面スペースを節約したコンパクトなブラシツールパネル
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QSpinBox, QComboBox,
    QPushButton, QButtonGroup, QRadioButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon

from ui.i18n import tr
from ui.icon_manager import get_icon_manager
from domain.dto.brush_dto import BrushConfigDTO, BrushModeDTO


class CompactBrushPanel(QWidget):
    """コンパクトブラシツールパネル"""
    
    # シグナル
    config_changed = pyqtSignal(BrushConfigDTO)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_config = BrushConfigDTO(mode=BrushModeDTO.ERASE)
        self._setup_ui()
        self._update_ui_from_config()
        
    def _setup_ui(self) -> None:
        """UIをセットアップ（コンパクト版）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # モード選択（横並び）
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(2)
        
        # モードコンボボックス（ラジオボタンの代わり）
        mode_label = QLabel(tr("brush.mode"))
        mode_label.setFixedWidth(40)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            tr("brush.mode.add_new"),
            tr("brush.mode.add_existing"),
            tr("brush.mode.erase")
        ])
        self.mode_combo.setCurrentIndex(2)  # デフォルトは消しゴム
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo, 1)
        layout.addLayout(mode_layout)
        
        # ID設定（モードに応じて表示）
        id_layout = QHBoxLayout()
        id_layout.setSpacing(2)
        
        self.id_label = QLabel(tr("brush.new_id"))
        self.id_label.setFixedWidth(40)
        self.id_spinbox = QSpinBox()
        self.id_spinbox.setRange(1, 255)
        self.id_spinbox.setValue(1)
        self.id_spinbox.setMaximumWidth(60)
        self.id_spinbox.valueChanged.connect(self._on_config_changed)
        
        id_layout.addWidget(self.id_label)
        id_layout.addWidget(self.id_spinbox)
        id_layout.addStretch()
        layout.addLayout(id_layout)
        
        # 区切り線
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line1)
        
        # ブラシ設定（グリッドレイアウト）
        settings_grid = QGridLayout()
        settings_grid.setSpacing(2)
        
        # サイズ
        size_label = QLabel(tr("brush.size"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(10)
        self.size_slider.setMaximumHeight(20)
        self.size_value = QLabel("10")
        self.size_value.setFixedWidth(30)
        self.size_slider.valueChanged.connect(
            lambda v: (self.size_value.setText(str(v)), self._on_config_changed())
        )
        
        settings_grid.addWidget(size_label, 0, 0)
        settings_grid.addWidget(self.size_slider, 0, 1)
        settings_grid.addWidget(self.size_value, 0, 2)
        
        # 硬さ
        hardness_label = QLabel(tr("brush.hardness"))
        self.hardness_slider = QSlider(Qt.Orientation.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(80)
        self.hardness_slider.setMaximumHeight(20)
        self.hardness_value = QLabel("80%")
        self.hardness_value.setFixedWidth(30)
        self.hardness_slider.valueChanged.connect(
            lambda v: (self.hardness_value.setText(f"{v}%"), self._on_config_changed())
        )
        
        settings_grid.addWidget(hardness_label, 1, 0)
        settings_grid.addWidget(self.hardness_slider, 1, 1)
        settings_grid.addWidget(self.hardness_value, 1, 2)
        
        # 不透明度
        opacity_label = QLabel(tr("brush.opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMaximumHeight(20)
        self.opacity_value = QLabel("100%")
        self.opacity_value.setFixedWidth(30)
        self.opacity_slider.valueChanged.connect(
            lambda v: (self.opacity_value.setText(f"{v}%"), self._on_config_changed())
        )
        
        settings_grid.addWidget(opacity_label, 2, 0)
        settings_grid.addWidget(self.opacity_slider, 2, 1)
        settings_grid.addWidget(self.opacity_value, 2, 2)
        
        layout.addLayout(settings_grid)
        
        # 区切り線
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line2)
        
        # アクションボタン（横並び）
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(2)
        
        icon_manager = get_icon_manager()
        
        # Undo/Redo
        self.undo_btn = QPushButton()
        self.undo_btn.setIcon(icon_manager.get_icon("edit-undo"))
        self.undo_btn.setToolTip(tr("brush.undo"))
        self.undo_btn.setMaximumSize(QSize(28, 28))
        self.undo_btn.clicked.connect(self.undo_requested)
        
        self.redo_btn = QPushButton()
        self.redo_btn.setIcon(icon_manager.get_icon("edit-redo"))
        self.redo_btn.setToolTip(tr("brush.redo"))
        self.redo_btn.setMaximumSize(QSize(28, 28))
        self.redo_btn.clicked.connect(self.redo_requested)
        
        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(icon_manager.get_icon("edit-clear"))
        self.clear_btn.setToolTip(tr("brush.clear"))
        self.clear_btn.setMaximumSize(QSize(28, 28))
        self.clear_btn.clicked.connect(self.clear_requested)
        
        actions_layout.addWidget(self.undo_btn)
        actions_layout.addWidget(self.redo_btn)
        actions_layout.addWidget(self.clear_btn)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        # ストレッチ
        layout.addStretch()
        
    def _on_mode_changed(self, index: int) -> None:
        """モード変更時の処理"""
        if index == 0:  # ADD_NEW_ID
            self.id_label.setText(tr("brush.new_id"))
            self.id_spinbox.setEnabled(True)
        elif index == 1:  # ADD_TO_EXISTING
            self.id_label.setText(tr("brush.target_id"))
            self.id_spinbox.setEnabled(True)
        else:  # ERASE
            self.id_spinbox.setEnabled(False)
        
        self._on_config_changed()
        
    def _on_config_changed(self) -> None:
        """設定変更時の処理"""
        self._update_config_from_ui()
        self.config_changed.emit(self._current_config)
        
    def _update_config_from_ui(self) -> None:
        """UIから設定を更新"""
        mode_index = self.mode_combo.currentIndex()
        mode = [BrushModeDTO.ADD_NEW_ID, BrushModeDTO.ADD_TO_EXISTING, BrushModeDTO.ERASE][mode_index]
        
        kwargs = {
            "mode": mode,
            "size": self.size_slider.value(),
            "hardness": self.hardness_slider.value() / 100.0,
            "opacity": self.opacity_slider.value() / 100.0,
        }
        
        if mode == BrushModeDTO.ADD_NEW_ID:
            kwargs["new_id"] = self.id_spinbox.value()
        elif mode == BrushModeDTO.ADD_TO_EXISTING:
            kwargs["target_id"] = self.id_spinbox.value()
            
        self._current_config = BrushConfigDTO(**kwargs)
        
    def _update_ui_from_config(self) -> None:
        """設定からUIを更新"""
        # モード
        if self._current_config.mode == BrushModeDTO.ADD_NEW_ID:
            self.mode_combo.setCurrentIndex(0)
            if self._current_config.new_id:
                self.id_spinbox.setValue(self._current_config.new_id)
        elif self._current_config.mode == BrushModeDTO.ADD_TO_EXISTING:
            self.mode_combo.setCurrentIndex(1)
            if self._current_config.target_id:
                self.id_spinbox.setValue(self._current_config.target_id)
        else:
            self.mode_combo.setCurrentIndex(2)
            
        # ブラシ設定
        self.size_slider.setValue(self._current_config.size)
        self.hardness_slider.setValue(int(self._current_config.hardness * 100))
        self.opacity_slider.setValue(int(self._current_config.opacity * 100))
        
    def get_current_config(self) -> BrushConfigDTO:
        """現在の設定を取得"""
        return self._current_config