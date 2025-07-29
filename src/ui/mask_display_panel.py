#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスク表示設定パネル

マスクの表示設定を管理するUIパネル。
"""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import Optional, Dict, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QSlider, QLabel, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QColorDialog, QSpinBox
)

from ui.i18n import tr
from domain.dto.mask_dto import MaskDTO, MaskOverlaySettingsDTO

logger = logging.getLogger(__name__)


class MaskDisplayPanel(QWidget):
    """マスク表示設定パネル
    
    オーバーレイの透明度、色、表示/非表示を管理。
    """
    
    # シグナル
    settings_changed = pyqtSignal(MaskOverlaySettingsDTO)
    mask_visibility_changed = pyqtSignal(int, bool)  # マスクID、表示フラグ
    mask_color_changed = pyqtSignal(int, str)  # マスクID、色
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 現在の設定
        self.overlay_settings = MaskOverlaySettingsDTO()
        self.current_mask_dto: Optional[MaskDTO] = None
        
        # UI初期化
        self._setup_ui()
        
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # タイトル
        title_label = QLabel(tr("mask_display.title"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # オーバーレイ設定グループ
        overlay_group = self._create_overlay_group()
        layout.addWidget(overlay_group)
        
        # マスク一覧グループ
        mask_list_group = self._create_mask_list_group()
        layout.addWidget(mask_list_group)
        
        # ストレッチを追加
        layout.addStretch()
    
    def _create_overlay_group(self) -> QGroupBox:
        """オーバーレイ設定グループを作成"""
        group = QGroupBox(tr("mask_display.overlay"))
        layout = QVBoxLayout(group)
        
        # オーバーレイ有効/無効
        self.overlay_checkbox = QCheckBox(tr("mask_display.enabled"))
        self.overlay_checkbox.setChecked(self.overlay_settings.enabled)
        self.overlay_checkbox.toggled.connect(self._on_overlay_toggled)
        layout.addWidget(self.overlay_checkbox)
        
        # 不透明度スライダー
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel(tr("mask_display.opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.overlay_settings.opacity * 100))
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        
        self.opacity_label = QLabel(f"{int(self.overlay_settings.opacity * 100)}%")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)
        
        # 輪郭線表示
        self.outline_checkbox = QCheckBox(tr("mask_display.show_outlines"))
        self.outline_checkbox.setChecked(self.overlay_settings.show_outlines)
        self.outline_checkbox.toggled.connect(self._on_outline_toggled)
        layout.addWidget(self.outline_checkbox)
        
        # 輪郭線の太さ
        outline_width_layout = QHBoxLayout()
        outline_width_label = QLabel(tr("mask_display.outline_width"))
        self.outline_width_spinbox = QSpinBox()
        self.outline_width_spinbox.setRange(1, 10)
        self.outline_width_spinbox.setValue(self.overlay_settings.outline_width)
        self.outline_width_spinbox.valueChanged.connect(self._on_outline_width_changed)
        
        outline_width_layout.addWidget(outline_width_label)
        outline_width_layout.addWidget(self.outline_width_spinbox)
        outline_width_layout.addStretch()
        layout.addLayout(outline_width_layout)
        
        # ラベル表示
        self.labels_checkbox = QCheckBox(tr("mask_display.show_labels"))
        self.labels_checkbox.setChecked(self.overlay_settings.show_labels)
        self.labels_checkbox.toggled.connect(self._on_labels_toggled)
        layout.addWidget(self.labels_checkbox)
        
        return group
    
    def _create_mask_list_group(self) -> QGroupBox:
        """マスク一覧グループを作成"""
        group = QGroupBox(tr("mask_display.mask_list"))
        layout = QVBoxLayout(group)
        
        # マスクテーブル
        self.mask_table = QTableWidget()
        self.mask_table.setColumnCount(5)
        self.mask_table.setHorizontalHeaderLabels([
            tr("mask_display.id"),
            tr("mask_display.class"),
            tr("mask_display.confidence"),
            tr("mask_display.visible"),
            tr("mask_display.color")
        ])
        
        # ヘッダー設定
        header = self.mask_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # 行の高さを設定
        self.mask_table.verticalHeader().setDefaultSectionSize(30)
        self.mask_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.mask_table)
        
        # 全選択/全解除ボタン
        button_layout = QHBoxLayout()
        self.select_all_button = QPushButton(tr("mask_display.select_all"))
        self.select_all_button.clicked.connect(self._on_select_all)
        self.deselect_all_button = QPushButton(tr("mask_display.deselect_all"))
        self.deselect_all_button.clicked.connect(self._on_deselect_all)
        
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.deselect_all_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return group
    
    def set_mask(self, mask_dto: Optional[MaskDTO]) -> None:
        """マスクデータを設定"""
        self.current_mask_dto = mask_dto
        self._update_mask_table()
    
    def set_overlay_settings(self, settings: MaskOverlaySettingsDTO) -> None:
        """オーバーレイ設定を更新"""
        self.overlay_settings = settings
        
        # UIを更新
        self.overlay_checkbox.setChecked(settings.enabled)
        self.opacity_slider.setValue(int(settings.opacity * 100))
        self.outline_checkbox.setChecked(settings.show_outlines)
        self.outline_width_spinbox.setValue(settings.outline_width)
        self.labels_checkbox.setChecked(settings.show_labels)
        
        self._update_mask_table()
    
    def _update_mask_table(self) -> None:
        """マスクテーブルを更新"""
        if not self.current_mask_dto:
            self.mask_table.setRowCount(0)
            return
        
        # 行数を設定
        self.mask_table.setRowCount(len(self.current_mask_dto.object_ids))
        
        # 各マスクの情報を表示
        for row, obj_id in enumerate(self.current_mask_dto.object_ids):
            # ID
            id_item = QTableWidgetItem(str(obj_id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.mask_table.setItem(row, 0, id_item)
            
            # クラス
            class_name = self.current_mask_dto.classes.get(obj_id, f"ID{obj_id}")
            class_item = QTableWidgetItem(class_name)
            self.mask_table.setItem(row, 1, class_item)
            
            # 信頼度
            confidence = self.current_mask_dto.confidences.get(obj_id, 0.0)
            conf_item = QTableWidgetItem(f"{confidence:.2f}")
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.mask_table.setItem(row, 2, conf_item)
            
            # 表示チェックボックス
            visible_checkbox = QCheckBox()
            visible_checkbox.setChecked(
                self.overlay_settings.is_mask_visible(obj_id)
            )
            visible_checkbox.toggled.connect(
                lambda checked, mask_id=obj_id: self._on_mask_visibility_changed(mask_id, checked)
            )
            
            # チェックボックスを中央に配置
            visible_widget = QWidget()
            visible_layout = QHBoxLayout(visible_widget)
            visible_layout.addWidget(visible_checkbox)
            visible_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            visible_layout.setContentsMargins(0, 0, 0, 0)
            self.mask_table.setCellWidget(row, 3, visible_widget)
            
            # 色選択ボタン
            color = self.overlay_settings.get_mask_color(obj_id)
            color_button = QPushButton()
            color_button.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
            color_button.setFixedSize(40, 20)
            color_button.clicked.connect(
                lambda _, mask_id=obj_id: self._on_color_button_clicked(mask_id)
            )
            
            # ボタンを中央に配置
            color_widget = QWidget()
            color_layout = QHBoxLayout(color_widget)
            color_layout.addWidget(color_button)
            color_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color_layout.setContentsMargins(0, 0, 0, 0)
            self.mask_table.setCellWidget(row, 4, color_widget)
    
    def _on_overlay_toggled(self, checked: bool) -> None:
        """オーバーレイ有効/無効が切り替えられた"""
        self.overlay_settings = replace(self.overlay_settings, enabled=checked)
        self._emit_settings_changed()
    
    def _on_opacity_changed(self, value: int) -> None:
        """不透明度が変更された"""
        opacity = value / 100.0
        self.overlay_settings = replace(self.overlay_settings, opacity=opacity)
        self.opacity_label.setText(f"{value}%")
        self._emit_settings_changed()
    
    def _on_outline_toggled(self, checked: bool) -> None:
        """輪郭線表示が切り替えられた"""
        self.overlay_settings = replace(self.overlay_settings, show_outlines=checked)
        self._emit_settings_changed()
    
    def _on_outline_width_changed(self, value: int) -> None:
        """輪郭線の太さが変更された"""
        self.overlay_settings = replace(self.overlay_settings, outline_width=value)
        self._emit_settings_changed()
    
    def _on_labels_toggled(self, checked: bool) -> None:
        """ラベル表示が切り替えられた"""
        self.overlay_settings = replace(self.overlay_settings, show_labels=checked)
        self._emit_settings_changed()
    
    def _on_mask_visibility_changed(self, mask_id: int, visible: bool) -> None:
        """マスクの表示/非表示が変更された"""
        new_visibility = self.overlay_settings.mask_visibility.copy()
        new_visibility[mask_id] = visible
        self.overlay_settings = replace(self.overlay_settings, mask_visibility=new_visibility)
        self.mask_visibility_changed.emit(mask_id, visible)
        self._emit_settings_changed()
    
    def _on_color_button_clicked(self, mask_id: int) -> None:
        """色選択ボタンがクリックされた"""
        current_color = self.overlay_settings.get_mask_color(mask_id)
        color = QColorDialog.getColor(
            QColor(current_color),
            self,
            tr("mask_display.select_color")
        )
        
        if color.isValid():
            color_str = color.name()
            new_colors = self.overlay_settings.mask_colors.copy()
            new_colors[mask_id] = color_str
            self.overlay_settings = replace(self.overlay_settings, mask_colors=new_colors)
            self.mask_color_changed.emit(mask_id, color_str)
            self._update_mask_table()
            self._emit_settings_changed()
    
    def _on_select_all(self) -> None:
        """全選択"""
        if self.current_mask_dto:
            new_visibility = self.overlay_settings.mask_visibility.copy()
            for obj_id in self.current_mask_dto.object_ids:
                new_visibility[obj_id] = True
            self.overlay_settings = replace(self.overlay_settings, mask_visibility=new_visibility)
            self._update_mask_table()
            self._emit_settings_changed()
    
    def _on_deselect_all(self) -> None:
        """全解除"""
        if self.current_mask_dto:
            new_visibility = self.overlay_settings.mask_visibility.copy()
            for obj_id in self.current_mask_dto.object_ids:
                new_visibility[obj_id] = False
            self.overlay_settings = replace(self.overlay_settings, mask_visibility=new_visibility)
            self._update_mask_table()
            self._emit_settings_changed()
    
    def _emit_settings_changed(self) -> None:
        """設定変更を通知"""
        self.settings_changed.emit(self.overlay_settings)