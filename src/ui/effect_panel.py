#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクト設定パネル

エフェクトの選択、パラメータ調整、プリセット管理を行うUIパネル。
"""
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QComboBox, QPushButton, QSlider, QSpinBox,
    QDoubleSpinBox, QLabel, QCheckBox, QListWidget,
    QListWidgetItem, QSplitter, QToolButton, QMenu,
    QMessageBox, QFileDialog, QInputDialog,
    QStackedWidget, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QImage
import numpy as np
import logging

from domain.dto.effect_dto import (
    EffectType, EffectConfigDTO, EffectPresetDTO,
    ParameterType, STANDARD_EFFECTS
)
from domain.dto.mask_dto import MaskDTO
from domain.ports.secondary.effect_ports import (
    IEffectEngine, IEffectPresetManager, IEffectPreview
)

logger = logging.getLogger(__name__)


class EffectPanel(QWidget):
    """エフェクト設定パネル"""
    
    # シグナル定義
    effect_applied = pyqtSignal(EffectConfigDTO)  # エフェクト適用時
    preview_requested = pyqtSignal()  # プレビュー更新要求時
    
    def __init__(
        self,
        effect_engine: IEffectEngine,
        preset_manager: IEffectPresetManager,
        effect_preview: IEffectPreview,
        parent=None
    ):
        """
        初期化
        
        Args:
            effect_engine: エフェクトエンジン
            preset_manager: プリセットマネージャー
            effect_preview: エフェクトプレビュー
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self._effect_engine = effect_engine
        self._preset_manager = preset_manager
        self._effect_preview = effect_preview
        
        self._current_effects: Dict[str, EffectConfigDTO] = {}
        self._selected_mask_ids: List[int] = []
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._update_preview_delayed)
        self._preview_timer.setSingleShot(True)
        
        self._setup_ui()
        self._load_effects()
        self._load_presets()
    
    def _setup_ui(self):
        """UI構築"""
        layout = QVBoxLayout(self)
        
        # エフェクトリストとパラメータをスプリッターで分割
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上部: エフェクトリスト
        effect_group = QGroupBox("アクティブエフェクト")
        effect_layout = QVBoxLayout(effect_group)
        
        # エフェクト追加ボタン
        add_layout = QHBoxLayout()
        self._effect_type_combo = QComboBox()
        add_layout.addWidget(self._effect_type_combo)
        
        self._add_effect_btn = QPushButton("エフェクト追加")
        self._add_effect_btn.clicked.connect(self._add_effect)
        add_layout.addWidget(self._add_effect_btn)
        
        effect_layout.addLayout(add_layout)
        
        # エフェクトリスト
        self._effect_list = QListWidget()
        self._effect_list.currentItemChanged.connect(self._on_effect_selected)
        effect_layout.addWidget(self._effect_list)
        
        # エフェクト操作ボタン
        effect_btn_layout = QHBoxLayout()
        
        self._remove_effect_btn = QPushButton("削除")
        self._remove_effect_btn.clicked.connect(self._remove_effect)
        effect_btn_layout.addWidget(self._remove_effect_btn)
        
        self._duplicate_effect_btn = QPushButton("複製")
        self._duplicate_effect_btn.clicked.connect(self._duplicate_effect)
        effect_btn_layout.addWidget(self._duplicate_effect_btn)
        
        effect_btn_layout.addStretch()
        effect_layout.addLayout(effect_btn_layout)
        
        splitter.addWidget(effect_group)
        
        # 下部: パラメータ設定
        param_group = QGroupBox("パラメータ")
        param_layout = QVBoxLayout(param_group)
        
        # パラメータスタック（エフェクトタイプごとに異なるUI）
        self._param_stack = QStackedWidget()
        param_layout.addWidget(self._param_stack)
        
        # 共通パラメータ
        common_layout = QHBoxLayout()
        
        common_layout.addWidget(QLabel("強度:"))
        self._intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self._intensity_slider.setRange(0, 100)
        self._intensity_slider.setValue(100)
        self._intensity_slider.valueChanged.connect(self._on_intensity_changed)
        common_layout.addWidget(self._intensity_slider)
        
        self._intensity_spin = QSpinBox()
        self._intensity_spin.setRange(0, 100)
        self._intensity_spin.setValue(100)
        self._intensity_spin.setSuffix("%")
        self._intensity_spin.valueChanged.connect(self._intensity_slider.setValue)
        self._intensity_slider.valueChanged.connect(self._intensity_spin.setValue)
        common_layout.addWidget(self._intensity_spin)
        
        param_layout.addLayout(common_layout)
        
        # プリセット管理
        preset_layout = QHBoxLayout()
        
        self._preset_combo = QComboBox()
        self._preset_combo.currentIndexChanged.connect(self._apply_preset)
        preset_layout.addWidget(self._preset_combo)
        
        preset_menu_btn = QToolButton()
        preset_menu_btn.setText("...")
        preset_menu = QMenu()
        preset_menu.addAction("プリセット保存", self._save_preset)
        preset_menu.addAction("プリセット削除", self._delete_preset)
        preset_menu.addSeparator()
        preset_menu.addAction("インポート", self._import_presets)
        preset_menu.addAction("エクスポート", self._export_presets)
        preset_menu_btn.setMenu(preset_menu)
        preset_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        preset_layout.addWidget(preset_menu_btn)
        
        param_layout.addLayout(preset_layout)
        
        splitter.addWidget(param_group)
        
        layout.addWidget(splitter)
        
        # 適用ボタン
        apply_layout = QHBoxLayout()
        
        self._preview_check = QCheckBox("リアルタイムプレビュー")
        self._preview_check.setChecked(True)
        apply_layout.addWidget(self._preview_check)
        
        apply_layout.addStretch()
        
        self._apply_btn = QPushButton("適用")
        self._apply_btn.clicked.connect(self._apply_effects)
        apply_layout.addWidget(self._apply_btn)
        
        layout.addLayout(apply_layout)
    
    def _load_effects(self):
        """利用可能なエフェクトを読み込み"""
        self._effect_type_combo.clear()
        
        for effect_def in self._effect_engine.get_available_effects():
            self._effect_type_combo.addItem(
                effect_def.display_name,
                effect_def.effect_type
            )
            
            # パラメータUIを作成
            param_widget = self._create_parameter_widget(effect_def)
            self._param_stack.addWidget(param_widget)
    
    def _create_parameter_widget(self, effect_def) -> QWidget:
        """エフェクトタイプごとのパラメータウィジェットを作成"""
        widget = QWidget()
        layout = QGridLayout(widget)
        
        # パラメータごとにUIを作成
        for i, param_def in enumerate(effect_def.parameters):
            label = QLabel(f"{param_def.display_name}:")
            layout.addWidget(label, i, 0)
            
            if param_def.parameter_type == ParameterType.INTEGER:
                if param_def.min_value is not None and param_def.max_value is not None:
                    # スライダーとスピンボックス
                    slider = QSlider(Qt.Orientation.Horizontal)
                    slider.setRange(param_def.min_value, param_def.max_value)
                    slider.setValue(param_def.default_value)
                    slider.setObjectName(f"param_{param_def.name}_slider")
                    
                    spin = QSpinBox()
                    spin.setRange(param_def.min_value, param_def.max_value)
                    spin.setValue(param_def.default_value)
                    if param_def.unit:
                        spin.setSuffix(f" {param_def.unit}")
                    spin.setObjectName(f"param_{param_def.name}_spin")
                    
                    # 相互接続
                    slider.valueChanged.connect(spin.setValue)
                    spin.valueChanged.connect(slider.setValue)
                    slider.valueChanged.connect(self._on_parameter_changed)
                    
                    layout.addWidget(slider, i, 1)
                    layout.addWidget(spin, i, 2)
                else:
                    # スピンボックスのみ
                    spin = QSpinBox()
                    spin.setValue(param_def.default_value)
                    spin.setObjectName(f"param_{param_def.name}")
                    spin.valueChanged.connect(self._on_parameter_changed)
                    layout.addWidget(spin, i, 1, 1, 2)
                    
            elif param_def.parameter_type == ParameterType.FLOAT:
                if param_def.min_value is not None and param_def.max_value is not None:
                    # スライダーとスピンボックス
                    slider = QSlider(Qt.Orientation.Horizontal)
                    # スライダーは整数値なので100倍して扱う
                    slider.setRange(
                        int(param_def.min_value * 100),
                        int(param_def.max_value * 100)
                    )
                    slider.setValue(int(param_def.default_value * 100))
                    slider.setObjectName(f"param_{param_def.name}_slider")
                    
                    spin = QDoubleSpinBox()
                    spin.setRange(param_def.min_value, param_def.max_value)
                    spin.setValue(param_def.default_value)
                    spin.setSingleStep(param_def.step or 0.1)
                    if param_def.unit:
                        spin.setSuffix(f" {param_def.unit}")
                    spin.setObjectName(f"param_{param_def.name}_spin")
                    
                    # 相互接続
                    slider.valueChanged.connect(
                        lambda v, s=spin: s.setValue(v / 100.0)
                    )
                    spin.valueChanged.connect(
                        lambda v, s=slider: s.setValue(int(v * 100))
                    )
                    slider.valueChanged.connect(self._on_parameter_changed)
                    
                    layout.addWidget(slider, i, 1)
                    layout.addWidget(spin, i, 2)
                else:
                    # スピンボックスのみ
                    spin = QDoubleSpinBox()
                    spin.setValue(param_def.default_value)
                    spin.setObjectName(f"param_{param_def.name}")
                    spin.valueChanged.connect(self._on_parameter_changed)
                    layout.addWidget(spin, i, 1, 1, 2)
                    
            elif param_def.parameter_type == ParameterType.BOOLEAN:
                check = QCheckBox()
                check.setChecked(param_def.default_value)
                check.setObjectName(f"param_{param_def.name}")
                check.stateChanged.connect(self._on_parameter_changed)
                layout.addWidget(check, i, 1, 1, 2)
                
            elif param_def.parameter_type == ParameterType.CHOICE:
                combo = QComboBox()
                for choice in param_def.choices:
                    combo.addItem(choice)
                combo.setCurrentText(param_def.default_value)
                combo.setObjectName(f"param_{param_def.name}")
                combo.currentTextChanged.connect(self._on_parameter_changed)
                layout.addWidget(combo, i, 1, 1, 2)
            
            # 説明を追加
            if param_def.description:
                desc_label = QLabel(param_def.description)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet("color: gray; font-size: 10px;")
                layout.addWidget(desc_label, i, 3)
        
        # 余白を埋める
        layout.setRowStretch(len(effect_def.parameters), 1)
        
        return widget
    
    def _add_effect(self):
        """エフェクトを追加"""
        effect_type = self._effect_type_combo.currentData()
        if not effect_type:
            return
        
        # エフェクトIDを生成
        effect_id = f"{effect_type.value}_{len(self._current_effects)}"
        
        # デフォルト設定でエフェクトを作成
        effect_def = STANDARD_EFFECTS[effect_type]
        config = effect_def.get_default_config(effect_id)
        
        # 選択中のマスクIDを設定
        if self._selected_mask_ids:
            config = EffectConfigDTO(
                effect_type=config.effect_type,
                effect_id=config.effect_id,
                enabled=config.enabled,
                parameters=config.parameters,
                intensity=config.intensity,
                blend_mode=config.blend_mode,
                target_mask_ids=self._selected_mask_ids.copy(),
                custom_data=config.custom_data
            )
        
        # リストに追加
        self._current_effects[effect_id] = config
        
        item = QListWidgetItem(f"{effect_def.display_name} ({effect_id})")
        item.setData(Qt.ItemDataRole.UserRole, effect_id)
        item.setCheckState(Qt.CheckState.Checked if config.enabled else Qt.CheckState.Unchecked)
        self._effect_list.addItem(item)
        
        # 追加したエフェクトを選択
        self._effect_list.setCurrentItem(item)
        
        # プレビュー更新
        self._request_preview_update()
    
    def _remove_effect(self):
        """選択中のエフェクトを削除"""
        current_item = self._effect_list.currentItem()
        if not current_item:
            return
        
        effect_id = current_item.data(Qt.ItemDataRole.UserRole)
        
        # 確認ダイアログ
        reply = QMessageBox.question(
            self,
            "エフェクト削除",
            f"エフェクト '{current_item.text()}' を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 削除
            del self._current_effects[effect_id]
            self._effect_list.takeItem(self._effect_list.row(current_item))
            
            # プレビュー更新
            self._request_preview_update()
    
    def _duplicate_effect(self):
        """選択中のエフェクトを複製"""
        current_item = self._effect_list.currentItem()
        if not current_item:
            return
        
        effect_id = current_item.data(Qt.ItemDataRole.UserRole)
        config = self._current_effects[effect_id]
        
        # 新しいIDを生成
        new_id = f"{config.effect_type.value}_{len(self._current_effects)}"
        
        # 設定を複製
        new_config = EffectConfigDTO(
            effect_type=config.effect_type,
            effect_id=new_id,
            enabled=config.enabled,
            parameters=config.parameters.copy(),
            intensity=config.intensity,
            blend_mode=config.blend_mode,
            target_mask_ids=config.target_mask_ids.copy() if config.target_mask_ids else None,
            custom_data=config.custom_data.copy()
        )
        
        # リストに追加
        self._current_effects[new_id] = new_config
        
        effect_def = STANDARD_EFFECTS[config.effect_type]
        item = QListWidgetItem(f"{effect_def.display_name} ({new_id}) - コピー")
        item.setData(Qt.ItemDataRole.UserRole, new_id)
        item.setCheckState(Qt.CheckState.Checked if new_config.enabled else Qt.CheckState.Unchecked)
        self._effect_list.addItem(item)
        
        # プレビュー更新
        self._request_preview_update()
    
    def _on_effect_selected(self, current, previous):
        """エフェクト選択時の処理"""
        if not current:
            return
        
        effect_id = current.data(Qt.ItemDataRole.UserRole)
        config = self._current_effects.get(effect_id)
        if not config:
            return
        
        # パラメータUIを切り替え
        effect_type_index = 0
        for i in range(self._effect_type_combo.count()):
            if self._effect_type_combo.itemData(i) == config.effect_type:
                effect_type_index = i
                break
        
        self._param_stack.setCurrentIndex(effect_type_index)
        
        # パラメータ値を設定
        param_widget = self._param_stack.currentWidget()
        if param_widget:
            self._update_parameter_ui(param_widget, config)
        
        # 強度を設定
        self._intensity_slider.setValue(int(config.intensity * 100))
    
    def _update_parameter_ui(self, widget: QWidget, config: EffectConfigDTO):
        """パラメータUIを更新"""
        for param_name, value in config.parameters.items():
            # スライダー
            slider = widget.findChild(QSlider, f"param_{param_name}_slider")
            if slider:
                if isinstance(value, float):
                    slider.setValue(int(value * 100))
                else:
                    slider.setValue(value)
            
            # スピンボックス
            spin = widget.findChild((QSpinBox, QDoubleSpinBox), f"param_{param_name}_spin")
            if spin:
                spin.setValue(value)
            
            # 単独スピンボックス
            spin = widget.findChild((QSpinBox, QDoubleSpinBox), f"param_{param_name}")
            if spin:
                spin.setValue(value)
            
            # チェックボックス
            check = widget.findChild(QCheckBox, f"param_{param_name}")
            if check:
                check.setChecked(value)
            
            # コンボボックス
            combo = widget.findChild(QComboBox, f"param_{param_name}")
            if combo:
                combo.setCurrentText(value)
    
    def _on_parameter_changed(self):
        """パラメータ変更時の処理"""
        current_item = self._effect_list.currentItem()
        if not current_item:
            return
        
        effect_id = current_item.data(Qt.ItemDataRole.UserRole)
        config = self._current_effects.get(effect_id)
        if not config:
            return
        
        # 現在のパラメータ値を収集
        param_widget = self._param_stack.currentWidget()
        if not param_widget:
            return
        
        parameters = {}
        effect_def = STANDARD_EFFECTS[config.effect_type]
        
        for param_def in effect_def.parameters:
            param_name = param_def.name
            
            # 各UIタイプから値を取得
            # スピンボックス（スライダー付き）
            spin = param_widget.findChild((QSpinBox, QDoubleSpinBox), f"param_{param_name}_spin")
            if spin:
                parameters[param_name] = spin.value()
                continue
            
            # 単独スピンボックス
            spin = param_widget.findChild((QSpinBox, QDoubleSpinBox), f"param_{param_name}")
            if spin:
                parameters[param_name] = spin.value()
                continue
            
            # チェックボックス
            check = param_widget.findChild(QCheckBox, f"param_{param_name}")
            if check:
                parameters[param_name] = check.isChecked()
                continue
            
            # コンボボックス
            combo = param_widget.findChild(QComboBox, f"param_{param_name}")
            if combo:
                parameters[param_name] = combo.currentText()
                continue
        
        # 設定を更新
        self._current_effects[effect_id] = EffectConfigDTO(
            effect_type=config.effect_type,
            effect_id=config.effect_id,
            enabled=config.enabled,
            parameters=parameters,
            intensity=config.intensity,
            blend_mode=config.blend_mode,
            target_mask_ids=config.target_mask_ids,
            custom_data=config.custom_data
        )
        
        # プレビュー更新
        self._request_preview_update()
    
    def _on_intensity_changed(self, value):
        """強度変更時の処理"""
        current_item = self._effect_list.currentItem()
        if not current_item:
            return
        
        effect_id = current_item.data(Qt.ItemDataRole.UserRole)
        config = self._current_effects.get(effect_id)
        if not config:
            return
        
        # 設定を更新
        self._current_effects[effect_id] = EffectConfigDTO(
            effect_type=config.effect_type,
            effect_id=config.effect_id,
            enabled=config.enabled,
            parameters=config.parameters,
            intensity=value / 100.0,
            blend_mode=config.blend_mode,
            target_mask_ids=config.target_mask_ids,
            custom_data=config.custom_data
        )
        
        # プレビュー更新
        self._request_preview_update()
    
    def _request_preview_update(self):
        """プレビュー更新をリクエスト（遅延実行）"""
        if self._preview_check.isChecked():
            # 既存のタイマーをキャンセル
            self._preview_timer.stop()
            # 300ms後に更新
            self._preview_timer.start(300)
    
    def _update_preview_delayed(self):
        """遅延プレビュー更新"""
        self.preview_requested.emit()
    
    def _apply_effects(self):
        """エフェクトを適用"""
        # 有効なエフェクトのみ適用
        for i in range(self._effect_list.count()):
            item = self._effect_list.item(i)
            effect_id = item.data(Qt.ItemDataRole.UserRole)
            config = self._current_effects.get(effect_id)
            
            if config and item.checkState() == Qt.CheckState.Checked:
                self.effect_applied.emit(config)
    
    def _load_presets(self):
        """プリセットを読み込み"""
        self._preset_combo.clear()
        self._preset_combo.addItem("-- プリセット選択 --", None)
        
        # カテゴリーごとにグループ化
        categories = {}
        for preset in self._preset_manager.list_presets():
            category = preset.category or "その他"
            if category not in categories:
                categories[category] = []
            categories[category].append(preset)
        
        # コンボボックスに追加
        for category, presets in sorted(categories.items()):
            self._preset_combo.addItem(f"--- {category} ---", None)
            for preset in presets:
                self._preset_combo.addItem(f"  {preset.name}", preset)
    
    def _apply_preset(self, index):
        """プリセットを適用"""
        preset = self._preset_combo.itemData(index)
        if not preset or not isinstance(preset, EffectPresetDTO):
            return
        
        # エフェクトを追加
        effect_id = f"{preset.effect_type.value}_preset_{len(self._current_effects)}"
        config = preset.to_config(effect_id)
        
        # 選択中のマスクIDを設定
        if self._selected_mask_ids:
            config = EffectConfigDTO(
                effect_type=config.effect_type,
                effect_id=config.effect_id,
                enabled=config.enabled,
                parameters=config.parameters,
                intensity=config.intensity,
                blend_mode=config.blend_mode,
                target_mask_ids=self._selected_mask_ids.copy(),
                custom_data=config.custom_data
            )
        
        # リストに追加
        self._current_effects[effect_id] = config
        
        effect_def = STANDARD_EFFECTS[config.effect_type]
        item = QListWidgetItem(f"{effect_def.display_name} ({preset.name})")
        item.setData(Qt.ItemDataRole.UserRole, effect_id)
        item.setCheckState(Qt.CheckState.Checked)
        self._effect_list.addItem(item)
        
        # 追加したエフェクトを選択
        self._effect_list.setCurrentItem(item)
        
        # プレビュー更新
        self._request_preview_update()
        
        # コンボボックスをリセット
        self._preset_combo.setCurrentIndex(0)
    
    def _save_preset(self):
        """現在の設定をプリセットとして保存"""
        current_item = self._effect_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "保存するエフェクトを選択してください。")
            return
        
        effect_id = current_item.data(Qt.ItemDataRole.UserRole)
        config = self._current_effects.get(effect_id)
        if not config:
            return
        
        # プリセット名を入力
        name, ok = QInputDialog.getText(
            self,
            "プリセット保存",
            "プリセット名:",
            text=f"{current_item.text()}_preset"
        )
        
        if ok and name:
            # プリセットを作成
            preset = EffectPresetDTO(
                name=name,
                description=f"{current_item.text()}の設定",
                effect_type=config.effect_type,
                parameters=config.parameters.copy(),
                category="custom"
            )
            
            # 保存
            if self._preset_manager.save_preset(preset):
                QMessageBox.information(self, "成功", f"プリセット '{name}' を保存しました。")
                self._load_presets()
            else:
                QMessageBox.critical(self, "エラー", "プリセットの保存に失敗しました。")
    
    def _delete_preset(self):
        """選択中のプリセットを削除"""
        preset = self._preset_combo.currentData()
        if not preset or not isinstance(preset, EffectPresetDTO):
            QMessageBox.warning(self, "警告", "削除するプリセットを選択してください。")
            return
        
        # 確認ダイアログ
        reply = QMessageBox.question(
            self,
            "プリセット削除",
            f"プリセット '{preset.name}' を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self._preset_manager.delete_preset(preset.name):
                QMessageBox.information(self, "成功", f"プリセット '{preset.name}' を削除しました。")
                self._load_presets()
            else:
                QMessageBox.critical(self, "エラー", "プリセットの削除に失敗しました。")
    
    def _import_presets(self):
        """プリセットをインポート"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "プリセットをインポート",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            count = self._preset_manager.import_presets(file_path)
            if count > 0:
                QMessageBox.information(
                    self,
                    "成功",
                    f"{count}個のプリセットをインポートしました。"
                )
                self._load_presets()
            else:
                QMessageBox.warning(self, "警告", "プリセットをインポートできませんでした。")
    
    def _export_presets(self):
        """プリセットをエクスポート"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "プリセットをエクスポート",
            "effect_presets.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if self._preset_manager.export_presets(file_path):
                QMessageBox.information(self, "成功", "プリセットをエクスポートしました。")
            else:
                QMessageBox.critical(self, "エラー", "プリセットのエクスポートに失敗しました。")
    
    def set_selected_masks(self, mask_ids: List[int]):
        """選択中のマスクIDを設定"""
        self._selected_mask_ids = mask_ids.copy()
        
        # 既存のエフェクトのターゲットマスクを更新
        for effect_id, config in self._current_effects.items():
            self._current_effects[effect_id] = EffectConfigDTO(
                effect_type=config.effect_type,
                effect_id=config.effect_id,
                enabled=config.enabled,
                parameters=config.parameters,
                intensity=config.intensity,
                blend_mode=config.blend_mode,
                target_mask_ids=self._selected_mask_ids.copy() if self._selected_mask_ids else None,
                custom_data=config.custom_data
            )
        
        # プレビュー更新
        self._request_preview_update()
    
    def get_active_effects(self) -> List[EffectConfigDTO]:
        """アクティブなエフェクトのリストを取得"""
        active_effects = []
        
        for i in range(self._effect_list.count()):
            item = self._effect_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                effect_id = item.data(Qt.ItemDataRole.UserRole)
                config = self._current_effects.get(effect_id)
                if config:
                    active_effects.append(config)
        
        return active_effects
    
    def clear_effects(self):
        """全エフェクトをクリア"""
        self._effect_list.clear()
        self._current_effects.clear()
        self._request_preview_update()