#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラシツールパネル

ブラシツールの設定と操作を行うUIパネル。
"""
from typing import Optional, Dict, Any
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QSlider, QLabel, QComboBox,
    QSpinBox, QCheckBox, QButtonGroup,
    QRadioButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QImage, QColor

from ui.i18n import tr
from domain.dto.brush_dto import (
    BrushConfigDTO, BrushModeDTO, BrushShapeDTO,
    BrushPresetDTO
)
from domain.ports.secondary.brush_ports import IBrushPreview
from ui.animations import get_animation_manager
from ui.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class BrushPreviewWidget(QWidget):
    """ブラシプレビューウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self._preview_image: Optional[QPixmap] = None
        
    def set_preview(self, preview: Optional[QPixmap]) -> None:
        """プレビュー画像を設定"""
        self._preview_image = preview
        self.update()
        
    def paintEvent(self, event):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        theme = get_theme_manager()
        painter.fillRect(self.rect(), QColor(theme.color_scheme.surface))
        
        # 枠線
        painter.setPen(QColor(theme.color_scheme.border))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # プレビュー画像
        if self._preview_image:
            painter.drawPixmap(0, 0, self._preview_image)


class BrushToolPanel(QWidget):
    """ブラシツールパネル"""
    
    # シグナル
    config_changed = pyqtSignal(BrushConfigDTO)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    preset_selected = pyqtSignal(BrushPresetDTO)
    
    def __init__(self, brush_preview: Optional[IBrushPreview] = None, parent=None):
        super().__init__(parent)
        self._brush_preview = brush_preview
        # デフォルトではERASEモードを使用（new_id/target_idが不要）
        self._current_config = BrushConfigDTO(mode=BrushModeDTO.ERASE)
        self._animation_manager = get_animation_manager()
        
        # UI初期化
        self._setup_ui()
        
        # 初期設定を反映
        self._update_ui_from_config()
        self._update_preview()
        
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # タイトル
        title_label = QLabel(tr("brush.title"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # モード選択
        mode_group = self._create_mode_group()
        layout.addWidget(mode_group)
        
        # ブラシ設定
        brush_group = self._create_brush_settings_group()
        layout.addWidget(brush_group)
        
        # 描画オプション
        options_group = self._create_options_group()
        layout.addWidget(options_group)
        
        # アクションボタン
        actions_layout = self._create_actions_layout()
        layout.addLayout(actions_layout)
        
        # プリセット
        preset_group = self._create_preset_group()
        layout.addWidget(preset_group)
        
        # ストレッチを追加
        layout.addStretch()
        
    def _create_mode_group(self) -> QGroupBox:
        """モード選択グループを作成"""
        group = QGroupBox(tr("brush.mode"))
        layout = QVBoxLayout(group)
        
        # ラジオボタングループ
        self.mode_group = QButtonGroup(self)
        
        # 新規ID追加モード
        self.add_new_radio = QRadioButton(tr("brush.mode.add_new"))
        self.add_new_radio.setChecked(True)
        self.mode_group.addButton(self.add_new_radio, 0)
        layout.addWidget(self.add_new_radio)
        
        # 新規ID入力
        new_id_layout = QHBoxLayout()
        new_id_layout.addSpacing(20)
        new_id_label = QLabel(tr("brush.new_id"))
        self.new_id_spinbox = QSpinBox()
        self.new_id_spinbox.setRange(1, 255)
        self.new_id_spinbox.setValue(1)
        new_id_layout.addWidget(new_id_label)
        new_id_layout.addWidget(self.new_id_spinbox)
        new_id_layout.addStretch()
        layout.addLayout(new_id_layout)
        
        # 既存ID加筆モード
        self.add_existing_radio = QRadioButton(tr("brush.mode.add_existing"))
        self.mode_group.addButton(self.add_existing_radio, 1)
        layout.addWidget(self.add_existing_radio)
        
        # 対象ID入力
        target_id_layout = QHBoxLayout()
        target_id_layout.addSpacing(20)
        target_id_label = QLabel(tr("brush.target_id"))
        self.target_id_spinbox = QSpinBox()
        self.target_id_spinbox.setRange(1, 255)
        self.target_id_spinbox.setValue(1)
        self.target_id_spinbox.setEnabled(False)
        target_id_layout.addWidget(target_id_label)
        target_id_layout.addWidget(self.target_id_spinbox)
        target_id_layout.addStretch()
        layout.addLayout(target_id_layout)
        
        # 消しゴムモード
        self.erase_radio = QRadioButton(tr("brush.mode.erase"))
        self.mode_group.addButton(self.erase_radio, 2)
        layout.addWidget(self.erase_radio)
        
        # モード変更時の処理
        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        
        return group
        
    def _create_brush_settings_group(self) -> QGroupBox:
        """ブラシ設定グループを作成"""
        group = QGroupBox(tr("brush.settings"))
        layout = QVBoxLayout(group)
        
        # プレビュー
        preview_layout = QHBoxLayout()
        self.preview_widget = BrushPreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)
        
        # サイズ
        size_layout = QHBoxLayout()
        size_label = QLabel(tr("brush.size"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(10)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(10)
        self.size_value_label = QLabel("10")
        self.size_value_label.setMinimumWidth(30)
        
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider, 1)
        size_layout.addWidget(self.size_value_label)
        layout.addLayout(size_layout)
        
        # 硬さ
        hardness_layout = QHBoxLayout()
        hardness_label = QLabel(tr("brush.hardness"))
        self.hardness_slider = QSlider(Qt.Orientation.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(80)
        self.hardness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.hardness_slider.setTickInterval(10)
        self.hardness_value_label = QLabel("80%")
        self.hardness_value_label.setMinimumWidth(40)
        
        hardness_layout.addWidget(hardness_label)
        hardness_layout.addWidget(self.hardness_slider, 1)
        hardness_layout.addWidget(self.hardness_value_label)
        layout.addLayout(hardness_layout)
        
        # 不透明度
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel(tr("brush.opacity"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        self.opacity_value_label = QLabel("100%")
        self.opacity_value_label.setMinimumWidth(40)
        
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_value_label)
        layout.addLayout(opacity_layout)
        
        # 形状
        shape_layout = QHBoxLayout()
        shape_label = QLabel(tr("brush.shape"))
        self.shape_combo = QComboBox()
        self.shape_combo.addItem(tr("brush.shape.circle"), BrushShapeDTO.CIRCLE)
        self.shape_combo.addItem(tr("brush.shape.square"), BrushShapeDTO.SQUARE)
        
        shape_layout.addWidget(shape_label)
        shape_layout.addWidget(self.shape_combo)
        shape_layout.addStretch()
        layout.addLayout(shape_layout)
        
        # イベント接続
        self.size_slider.valueChanged.connect(self._on_size_changed)
        self.hardness_slider.valueChanged.connect(self._on_hardness_changed)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.shape_combo.currentIndexChanged.connect(self._on_shape_changed)
        
        return group
        
    def _create_options_group(self) -> QGroupBox:
        """描画オプショングループを作成"""
        group = QGroupBox(tr("brush.options"))
        layout = QVBoxLayout(group)
        
        # 筆圧感度
        self.pressure_checkbox = QCheckBox(tr("brush.pressure_sensitivity"))
        self.pressure_checkbox.setChecked(True)
        self.pressure_checkbox.toggled.connect(self._on_config_changed)
        layout.addWidget(self.pressure_checkbox)
        
        # スムージング
        smoothing_layout = QHBoxLayout()
        smoothing_label = QLabel(tr("brush.smoothing"))
        self.smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.smoothing_slider.setRange(0, 100)
        self.smoothing_slider.setValue(50)
        self.smoothing_value_label = QLabel("50%")
        self.smoothing_value_label.setMinimumWidth(40)
        
        smoothing_layout.addWidget(smoothing_label)
        smoothing_layout.addWidget(self.smoothing_slider, 1)
        smoothing_layout.addWidget(self.smoothing_value_label)
        layout.addLayout(smoothing_layout)
        
        self.smoothing_slider.valueChanged.connect(self._on_smoothing_changed)
        
        return group
        
    def _create_actions_layout(self) -> QHBoxLayout:
        """アクションボタンレイアウトを作成"""
        layout = QHBoxLayout()
        
        # Undoボタン
        self.undo_button = QPushButton(tr("brush.undo"))
        self.undo_button.clicked.connect(self.undo_requested.emit)
        self.undo_button.setEnabled(False)
        
        # Redoボタン
        self.redo_button = QPushButton(tr("brush.redo"))
        self.redo_button.clicked.connect(self.redo_requested.emit)
        self.redo_button.setEnabled(False)
        
        # クリアボタン
        self.clear_button = QPushButton(tr("brush.clear"))
        self.clear_button.clicked.connect(self._on_clear_clicked)
        
        layout.addWidget(self.undo_button)
        layout.addWidget(self.redo_button)
        layout.addWidget(self.clear_button)
        layout.addStretch()
        
        return layout
        
    def _create_preset_group(self) -> QGroupBox:
        """プリセットグループを作成"""
        group = QGroupBox(tr("brush.presets"))
        layout = QVBoxLayout(group)
        
        # プリセットボタン（仮実装）
        preset_layout = QHBoxLayout()
        
        # 小ブラシ
        small_button = QPushButton(tr("brush.preset.small"))
        small_button.clicked.connect(lambda: self._apply_preset_size(5))
        preset_layout.addWidget(small_button)
        
        # 中ブラシ
        medium_button = QPushButton(tr("brush.preset.medium"))
        medium_button.clicked.connect(lambda: self._apply_preset_size(20))
        preset_layout.addWidget(medium_button)
        
        # 大ブラシ
        large_button = QPushButton(tr("brush.preset.large"))
        large_button.clicked.connect(lambda: self._apply_preset_size(50))
        preset_layout.addWidget(large_button)
        
        layout.addLayout(preset_layout)
        
        return group
        
    def _on_mode_changed(self, button: QRadioButton) -> None:
        """モードが変更された"""
        # スピンボックスの有効/無効を切り替え
        mode_id = self.mode_group.id(button)
        self.new_id_spinbox.setEnabled(mode_id == 0)  # ADD_NEW_ID
        self.target_id_spinbox.setEnabled(mode_id == 1)  # ADD_TO_EXISTING
        
        self._on_config_changed()
        
    def _on_size_changed(self, value: int) -> None:
        """サイズが変更された"""
        self.size_value_label.setText(str(value))
        self._on_config_changed()
        
    def _on_hardness_changed(self, value: int) -> None:
        """硬さが変更された"""
        self.hardness_value_label.setText(f"{value}%")
        self._on_config_changed()
        
    def _on_opacity_changed(self, value: int) -> None:
        """不透明度が変更された"""
        self.opacity_value_label.setText(f"{value}%")
        self._on_config_changed()
        
    def _on_smoothing_changed(self, value: int) -> None:
        """スムージングが変更された"""
        self.smoothing_value_label.setText(f"{value}%")
        self._on_config_changed()
        
    def _on_shape_changed(self, index: int) -> None:
        """形状が変更された"""
        self._on_config_changed()
        
    def _on_config_changed(self) -> None:
        """設定が変更された"""
        # 新しい設定を作成
        mode_id = self.mode_group.checkedId()
        mode = [BrushModeDTO.ADD_NEW_ID, BrushModeDTO.ADD_TO_EXISTING, BrushModeDTO.ERASE][mode_id]
        
        from dataclasses import replace
        self._current_config = BrushConfigDTO(
            mode=mode,
            size=self.size_slider.value(),
            hardness=self.hardness_slider.value() / 100.0,
            opacity=self.opacity_slider.value() / 100.0,
            shape=self.shape_combo.currentData(),
            target_id=self.target_id_spinbox.value() if mode == BrushModeDTO.ADD_TO_EXISTING else None,
            new_id=self.new_id_spinbox.value() if mode == BrushModeDTO.ADD_NEW_ID else None,
            smoothing=self.smoothing_slider.value() / 100.0,
            pressure_sensitivity=self.pressure_checkbox.isChecked()
        )
        
        # プレビューを更新
        self._update_preview()
        
        # シグナルを発行
        self.config_changed.emit(self._current_config)
        
    def _update_preview(self) -> None:
        """プレビューを更新"""
        if not self._brush_preview:
            return
            
        # プレビュー画像を生成
        preview_array = self._brush_preview.generate_preview(self._current_config)
        
        # QPixmapに変換
        height, width = preview_array.shape[:2]
        bytes_per_line = 4 * width
        
        qimage = QImage(
            preview_array.data,
            width, height,
            bytes_per_line,
            QImage.Format.Format_RGBA8888
        )
        
        pixmap = QPixmap.fromImage(qimage)
        self.preview_widget.set_preview(pixmap)
        
    def _update_ui_from_config(self) -> None:
        """設定からUIを更新"""
        # モード
        if self._current_config.mode == BrushModeDTO.ADD_NEW_ID:
            self.add_new_radio.setChecked(True)
        elif self._current_config.mode == BrushModeDTO.ADD_TO_EXISTING:
            self.add_existing_radio.setChecked(True)
        else:
            self.erase_radio.setChecked(True)
            
        # サイズ、硬さ、不透明度
        self.size_slider.setValue(self._current_config.size)
        self.hardness_slider.setValue(int(self._current_config.hardness * 100))
        self.opacity_slider.setValue(int(self._current_config.opacity * 100))
        
        # 形状
        for i in range(self.shape_combo.count()):
            if self.shape_combo.itemData(i) == self._current_config.shape:
                self.shape_combo.setCurrentIndex(i)
                break
                
        # オプション
        self.pressure_checkbox.setChecked(self._current_config.pressure_sensitivity)
        self.smoothing_slider.setValue(int(self._current_config.smoothing * 100))
        
        # ID
        if self._current_config.new_id:
            self.new_id_spinbox.setValue(self._current_config.new_id)
        if self._current_config.target_id:
            self.target_id_spinbox.setValue(self._current_config.target_id)
            
    def _apply_preset_size(self, size: int) -> None:
        """プリセットサイズを適用"""
        self.size_slider.setValue(size)
        
    def _on_clear_clicked(self) -> None:
        """クリアボタンがクリックされた"""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            tr("brush.clear_confirm_title"),
            tr("brush.clear_confirm_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_requested.emit()
            
    def set_undo_enabled(self, enabled: bool) -> None:
        """Undoボタンの有効/無効を設定"""
        self.undo_button.setEnabled(enabled)
        
    def set_redo_enabled(self, enabled: bool) -> None:
        """Redoボタンの有効/無効を設定"""
        self.redo_button.setEnabled(enabled)
        
    def get_current_config(self) -> BrushConfigDTO:
        """現在の設定を取得"""
        return self._current_config
        
    def set_config(self, config: BrushConfigDTO) -> None:
        """設定を適用"""
        self._current_config = config
        self._update_ui_from_config()
        self._update_preview()