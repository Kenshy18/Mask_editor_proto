#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ID管理UIパネル

マスクのID削除、マージ、閾値調整機能を提供するUIコンポーネント。
"""
import logging
from typing import Optional, List, Dict, Tuple

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSlider, QPushButton, QListWidget, QListWidgetItem,
    QSpinBox, QCheckBox, QComboBox, QSplitter,
    QAbstractItemView, QMessageBox, QDoubleSpinBox
)
from PyQt6.QtGui import QIcon, QColor

from .i18n import tr
from .icon_manager import get_icon_manager
from domain.ports.secondary.id_management_ports import IIDManager, IThresholdManager, IIDPreview
from domain.dto.mask_dto import MaskDTO
from domain.dto.id_management_dto import IDStatisticsDTO, ThresholdSettingsDTO

logger = logging.getLogger(__name__)


class IDManagementPanel(QWidget):
    """ID管理パネル
    
    マスクID管理機能のUI。
    """
    
    # シグナル
    ids_deleted = pyqtSignal(list)  # 削除されたIDリスト
    ids_merged = pyqtSignal(list, int)  # マージ元リスト、マージ先ID
    threshold_changed = pyqtSignal(str, float)  # 閾値タイプ、新しい値
    preview_requested = pyqtSignal(str, dict)  # プレビュータイプ、パラメータ
    
    def __init__(self, id_manager: IIDManager, threshold_manager: IThresholdManager,
                 id_preview: IIDPreview, parent: Optional[QWidget] = None):
        """初期化
        
        Args:
            id_manager: ID管理サービス
            threshold_manager: 閾値管理サービス
            id_preview: プレビューサービス
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.id_manager = id_manager
        self.threshold_manager = threshold_manager
        self.id_preview = id_preview
        
        self.current_mask_dto: Optional[MaskDTO] = None
        self.id_statistics: Dict[int, IDStatisticsDTO] = {}
        
        # プレビュー更新用タイマー
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._update_preview)
        
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # スプリッターでID管理と閾値調整を分割
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # ===== ID管理セクション =====
        id_group = QGroupBox(tr("id_management.id_operations"))
        id_layout = QVBoxLayout(id_group)
        
        # ID一覧
        self.id_list = QListWidget()
        self.id_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.id_list.setMaximumHeight(200)
        id_layout.addWidget(QLabel(tr("id_management.object_ids")))
        id_layout.addWidget(self.id_list)
        
        # 操作ボタン
        button_layout = QHBoxLayout()
        
        self.delete_button = QPushButton(tr("id_management.delete_selected"))
        self.delete_button.setIcon(get_icon_manager().get_icon("delete"))
        self.delete_button.clicked.connect(self._on_delete_selected)
        button_layout.addWidget(self.delete_button)
        
        self.delete_range_button = QPushButton(tr("id_management.delete_range"))
        self.delete_range_button.clicked.connect(self._on_delete_range)
        button_layout.addWidget(self.delete_range_button)
        
        self.delete_all_button = QPushButton(tr("id_management.delete_all"))
        self.delete_all_button.setIcon(get_icon_manager().get_icon("clear"))
        self.delete_all_button.clicked.connect(self._on_delete_all)
        button_layout.addWidget(self.delete_all_button)
        
        id_layout.addLayout(button_layout)
        
        # マージ操作
        merge_layout = QHBoxLayout()
        merge_layout.addWidget(QLabel(tr("id_management.merge_to")))
        
        self.merge_target_combo = QComboBox()
        self.merge_target_combo.setMinimumWidth(80)
        merge_layout.addWidget(self.merge_target_combo)
        
        self.merge_button = QPushButton(tr("id_management.merge"))
        self.merge_button.setIcon(get_icon_manager().get_icon("merge"))
        self.merge_button.clicked.connect(self._on_merge)
        merge_layout.addWidget(self.merge_button)
        
        merge_layout.addStretch()
        id_layout.addLayout(merge_layout)
        
        # ID統計情報
        self.stats_label = QLabel(tr("id_management.no_statistics"))
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
        id_layout.addWidget(self.stats_label)
        
        splitter.addWidget(id_group)
        
        # ===== 閾値調整セクション =====
        threshold_group = QGroupBox(tr("id_management.threshold_adjustment"))
        threshold_layout = QVBoxLayout(threshold_group)
        
        # 検出閾値
        detection_layout = QVBoxLayout()
        detection_label_layout = QHBoxLayout()
        detection_label_layout.addWidget(QLabel(tr("id_management.detection_threshold")))
        self.detection_value_label = QLabel("0.50")
        detection_label_layout.addStretch()
        detection_label_layout.addWidget(self.detection_value_label)
        detection_layout.addLayout(detection_label_layout)
        
        self.detection_slider = QSlider(Qt.Orientation.Horizontal)
        self.detection_slider.setRange(0, 100)
        self.detection_slider.setValue(50)
        self.detection_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.detection_slider.setTickInterval(10)
        detection_layout.addWidget(self.detection_slider)
        
        threshold_layout.addLayout(detection_layout)
        
        # マージ閾値
        merge_threshold_layout = QVBoxLayout()
        merge_label_layout = QHBoxLayout()
        merge_label_layout.addWidget(QLabel(tr("id_management.merge_threshold")))
        self.merge_value_label = QLabel("0.80")
        merge_label_layout.addStretch()
        merge_label_layout.addWidget(self.merge_value_label)
        merge_threshold_layout.addLayout(merge_label_layout)
        
        self.merge_slider = QSlider(Qt.Orientation.Horizontal)
        self.merge_slider.setRange(0, 100)
        self.merge_slider.setValue(80)
        self.merge_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.merge_slider.setTickInterval(10)
        merge_threshold_layout.addWidget(self.merge_slider)
        
        threshold_layout.addLayout(merge_threshold_layout)
        
        # 詳細設定
        details_layout = QHBoxLayout()
        
        # 最小ピクセル数
        details_layout.addWidget(QLabel(tr("id_management.min_pixels")))
        self.min_pixels_spin = QSpinBox()
        self.min_pixels_spin.setRange(1, 10000)
        self.min_pixels_spin.setValue(100)
        self.min_pixels_spin.setSuffix(" px")
        details_layout.addWidget(self.min_pixels_spin)
        
        # 最大マージ距離
        details_layout.addWidget(QLabel(tr("id_management.max_merge_distance")))
        self.max_distance_spin = QDoubleSpinBox()
        self.max_distance_spin.setRange(0.0, 500.0)
        self.max_distance_spin.setValue(50.0)
        self.max_distance_spin.setSuffix(" px")
        details_layout.addWidget(self.max_distance_spin)
        
        details_layout.addStretch()
        threshold_layout.addLayout(details_layout)
        
        # プレビューチェックボックス
        self.preview_check = QCheckBox(tr("id_management.realtime_preview"))
        self.preview_check.setChecked(True)
        threshold_layout.addWidget(self.preview_check)
        
        # 適用ボタン
        apply_layout = QHBoxLayout()
        
        self.apply_threshold_button = QPushButton(tr("id_management.apply_threshold"))
        self.apply_threshold_button.setIcon(get_icon_manager().get_icon("apply"))
        self.apply_threshold_button.clicked.connect(self._on_apply_threshold)
        apply_layout.addWidget(self.apply_threshold_button)
        
        self.suggest_merge_button = QPushButton(tr("id_management.suggest_merges"))
        self.suggest_merge_button.clicked.connect(self._on_suggest_merges)
        apply_layout.addWidget(self.suggest_merge_button)
        
        apply_layout.addStretch()
        threshold_layout.addLayout(apply_layout)
        
        splitter.addWidget(threshold_group)
        
        layout.addWidget(splitter)
        
        # 初期状態
        self._update_ui_state()
    
    def _connect_signals(self) -> None:
        """シグナルを接続"""
        # リスト選択変更
        self.id_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # スライダー変更
        self.detection_slider.valueChanged.connect(self._on_detection_threshold_changed)
        self.merge_slider.valueChanged.connect(self._on_merge_threshold_changed)
        
        # スピンボックス変更
        self.min_pixels_spin.valueChanged.connect(self._on_settings_changed)
        self.max_distance_spin.valueChanged.connect(self._on_settings_changed)
        
        # プレビューチェック
        self.preview_check.toggled.connect(self._on_preview_toggled)
    
    def _load_settings(self) -> None:
        """設定を読み込み"""
        settings = self.threshold_manager.get_settings()
        
        # スライダーに反映
        self.detection_slider.setValue(int(settings.detection_threshold * 100))
        self.merge_slider.setValue(int(settings.merge_threshold * 100))
        
        # スピンボックスに反映
        self.min_pixels_spin.setValue(settings.min_pixel_count)
        self.max_distance_spin.setValue(settings.max_merge_distance)
        
        # ラベル更新
        self._update_threshold_labels()
    
    def set_mask(self, mask_dto: Optional[MaskDTO]) -> None:
        """マスクを設定"""
        self.current_mask_dto = mask_dto
        
        # ID一覧を更新
        self._update_id_list()
        
        # 統計情報を更新
        if mask_dto:
            mask_dict = mask_dto.to_dict()
            stats_dict = self.id_manager.get_id_statistics(mask_dict)
            
            # IDStatisticsDTOに変換
            self.id_statistics = {}
            for id_, stats in stats_dict.items():
                self.id_statistics[id_] = IDStatisticsDTO(
                    id=stats["id"],
                    pixel_count=stats["pixel_count"],
                    bbox=stats["bbox"],
                    center=stats["center"],
                    area_ratio=stats["area_ratio"],
                    confidence=stats.get("confidence"),
                    class_name=stats.get("class_name")
                )
        else:
            self.id_statistics = {}
        
        # UI状態を更新
        self._update_ui_state()
        self._update_stats_display()
    
    def _update_id_list(self) -> None:
        """ID一覧を更新"""
        self.id_list.clear()
        self.merge_target_combo.clear()
        
        if not self.current_mask_dto:
            return
        
        # IDでソート
        sorted_ids = sorted(self.current_mask_dto.object_ids)
        
        for obj_id in sorted_ids:
            # リストアイテムを作成
            item_text = f"ID {obj_id}"
            
            # クラス名があれば追加
            if obj_id in self.current_mask_dto.classes:
                item_text += f" ({self.current_mask_dto.classes[obj_id]})"
            
            # 信頼度があれば追加
            if obj_id in self.current_mask_dto.confidences:
                confidence = self.current_mask_dto.confidences[obj_id]
                item_text += f" [{confidence:.2f}]"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, obj_id)
            
            # 信頼度に応じて色分け
            if obj_id in self.current_mask_dto.confidences:
                confidence = self.current_mask_dto.confidences[obj_id]
                if confidence < 0.5:
                    item.setForeground(QColor(255, 0, 0))  # 赤
                elif confidence < 0.7:
                    item.setForeground(QColor(255, 165, 0))  # オレンジ
            
            self.id_list.addItem(item)
            
            # マージターゲットコンボボックスにも追加
            self.merge_target_combo.addItem(f"ID {obj_id}", obj_id)
    
    def _update_stats_display(self) -> None:
        """統計情報表示を更新"""
        selected_items = self.id_list.selectedItems()
        
        if not selected_items:
            self.stats_label.setText(tr("id_management.no_selection"))
            return
        
        # 選択されたIDの統計を表示
        stats_text = []
        total_pixels = 0
        
        for item in selected_items:
            obj_id = item.data(Qt.ItemDataRole.UserRole)
            if obj_id in self.id_statistics:
                stats = self.id_statistics[obj_id]
                stats_text.append(
                    f"ID {obj_id}: {stats.pixel_count} px "
                    f"({stats.area_ratio*100:.1f}%), "
                    f"bbox: ({stats.bbox[0]},{stats.bbox[1]})-({stats.bbox[2]},{stats.bbox[3]})"
                )
                total_pixels += stats.pixel_count
        
        if len(selected_items) > 1:
            stats_text.append(f"\n{tr('id_management.total')}: {total_pixels} px")
        
        self.stats_label.setText("\n".join(stats_text))
    
    def _update_threshold_labels(self) -> None:
        """閾値ラベルを更新"""
        detection_value = self.detection_slider.value() / 100.0
        merge_value = self.merge_slider.value() / 100.0
        
        self.detection_value_label.setText(f"{detection_value:.2f}")
        self.merge_value_label.setText(f"{merge_value:.2f}")
    
    def _update_ui_state(self) -> None:
        """UI状態を更新"""
        has_mask = self.current_mask_dto is not None
        has_selection = len(self.id_list.selectedItems()) > 0
        has_multiple = len(self.id_list.selectedItems()) > 1
        
        self.delete_button.setEnabled(has_mask and has_selection)
        self.delete_range_button.setEnabled(has_mask)
        self.delete_all_button.setEnabled(has_mask)
        self.merge_button.setEnabled(has_mask and has_selection)
        self.apply_threshold_button.setEnabled(has_mask)
        self.suggest_merge_button.setEnabled(has_mask)
    
    def _on_selection_changed(self) -> None:
        """選択が変更された時"""
        self._update_stats_display()
        self._update_ui_state()
    
    def _on_delete_selected(self) -> None:
        """選択されたIDを削除"""
        selected_items = self.id_list.selectedItems()
        if not selected_items or not self.current_mask_dto:
            return
        
        # 確認ダイアログ
        ret = QMessageBox.question(
            self,
            tr("id_management.confirm_delete"),
            tr("id_management.confirm_delete_message", count=len(selected_items)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if ret != QMessageBox.StandardButton.Yes:
            return
        
        # 削除するIDのリスト
        target_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        
        # 削除実行
        mask_dict = self.current_mask_dto.to_dict()
        new_mask_dict = self.id_manager.delete_ids(mask_dict, target_ids)
        
        # 新しいマスクDTOを作成
        new_mask_dto = MaskDTO.from_dict(new_mask_dict)
        self.set_mask(new_mask_dto)
        
        # シグナルを発信
        self.ids_deleted.emit(target_ids)
        
        logger.info(f"Deleted {len(target_ids)} IDs")
    
    def _on_delete_range(self) -> None:
        """範囲指定で削除"""
        # TODO: 範囲入力ダイアログを実装
        pass
    
    def _on_delete_all(self) -> None:
        """全て削除"""
        if not self.current_mask_dto:
            return
        
        # 確認ダイアログ
        ret = QMessageBox.warning(
            self,
            tr("id_management.confirm_delete_all"),
            tr("id_management.confirm_delete_all_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if ret != QMessageBox.StandardButton.Yes:
            return
        
        # 全削除実行
        mask_dict = self.current_mask_dto.to_dict()
        new_mask_dict = self.id_manager.delete_all(mask_dict)
        
        # 新しいマスクDTOを作成
        new_mask_dto = MaskDTO.from_dict(new_mask_dict)
        self.set_mask(new_mask_dto)
        
        # シグナルを発信
        self.ids_deleted.emit(self.current_mask_dto.object_ids)
        
        logger.info("Deleted all IDs")
    
    def _on_merge(self) -> None:
        """選択されたIDをマージ"""
        selected_items = self.id_list.selectedItems()
        if not selected_items or not self.current_mask_dto:
            return
        
        # マージ先ID
        target_id = self.merge_target_combo.currentData()
        if target_id is None:
            return
        
        # マージ元IDのリスト
        source_ids = [
            item.data(Qt.ItemDataRole.UserRole) 
            for item in selected_items
            if item.data(Qt.ItemDataRole.UserRole) != target_id
        ]
        
        if not source_ids:
            QMessageBox.information(
                self,
                tr("id_management.no_merge"),
                tr("id_management.no_merge_message")
            )
            return
        
        # 確認ダイアログ
        ret = QMessageBox.question(
            self,
            tr("id_management.confirm_merge"),
            tr("id_management.confirm_merge_message", 
               count=len(source_ids), target=target_id),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if ret != QMessageBox.StandardButton.Yes:
            return
        
        # マージ実行
        mask_dict = self.current_mask_dto.to_dict()
        new_mask_dict = self.id_manager.merge_ids(mask_dict, source_ids, target_id)
        
        # 新しいマスクDTOを作成
        new_mask_dto = MaskDTO.from_dict(new_mask_dict)
        self.set_mask(new_mask_dto)
        
        # シグナルを発信
        self.ids_merged.emit(source_ids, target_id)
        
        logger.info(f"Merged {len(source_ids)} IDs into ID {target_id}")
    
    def _on_detection_threshold_changed(self, value: int) -> None:
        """検出閾値が変更された時"""
        threshold = value / 100.0
        self.detection_value_label.setText(f"{threshold:.2f}")
        
        # 閾値を設定
        self.threshold_manager.set_detection_threshold(threshold)
        
        # シグナルを発信
        self.threshold_changed.emit("detection", threshold)
        
        # プレビュー更新をスケジュール
        if self.preview_check.isChecked():
            self.preview_timer.stop()
            self.preview_timer.start(200)  # 200ms後に更新
    
    def _on_merge_threshold_changed(self, value: int) -> None:
        """マージ閾値が変更された時"""
        threshold = value / 100.0
        self.merge_value_label.setText(f"{threshold:.2f}")
        
        # 閾値を設定
        self.threshold_manager.set_merge_threshold(threshold)
        
        # シグナルを発信
        self.threshold_changed.emit("merge", threshold)
        
        # プレビュー更新をスケジュール
        if self.preview_check.isChecked():
            self.preview_timer.stop()
            self.preview_timer.start(200)
    
    def _on_settings_changed(self) -> None:
        """詳細設定が変更された時"""
        # 新しい設定を作成
        new_settings = ThresholdSettingsDTO(
            detection_threshold=self.detection_slider.value() / 100.0,
            merge_threshold=self.merge_slider.value() / 100.0,
            min_pixel_count=self.min_pixels_spin.value(),
            max_merge_distance=self.max_distance_spin.value(),
            merge_overlap_ratio=0.7  # TODO: UIに追加
        )
        
        # 設定を更新
        self.threshold_manager.update_settings(new_settings)
    
    def _on_preview_toggled(self, checked: bool) -> None:
        """プレビュー表示が切り替えられた時"""
        if checked and self.current_mask_dto:
            self._update_preview()
    
    def _on_apply_threshold(self) -> None:
        """閾値を適用"""
        if not self.current_mask_dto:
            return
        
        # 検出閾値を適用
        threshold = self.detection_slider.value() / 100.0
        mask_dict = self.current_mask_dto.to_dict()
        new_mask_dict = self.threshold_manager.apply_detection_threshold(
            mask_dict, 
            self.current_mask_dto.confidences,
            threshold
        )
        
        # 新しいマスクDTOを作成
        new_mask_dto = MaskDTO.from_dict(new_mask_dict)
        
        # 削除されたIDを特定
        deleted_ids = list(set(self.current_mask_dto.object_ids) - set(new_mask_dto.object_ids))
        
        self.set_mask(new_mask_dto)
        
        # シグナルを発信
        if deleted_ids:
            self.ids_deleted.emit(deleted_ids)
        
        logger.info(f"Applied threshold {threshold}, removed {len(deleted_ids)} IDs")
    
    def _on_suggest_merges(self) -> None:
        """マージ候補を提案"""
        if not self.current_mask_dto:
            return
        
        # マージ候補を取得
        threshold = self.merge_slider.value() / 100.0
        mask_dict = self.current_mask_dto.to_dict()
        candidates = self.threshold_manager.suggest_merge_candidates(mask_dict, threshold)
        
        if not candidates:
            QMessageBox.information(
                self,
                tr("id_management.no_candidates"),
                tr("id_management.no_candidates_message")
            )
            return
        
        # TODO: 候補表示ダイアログを実装
        # とりあえず最初の候補を表示
        if candidates:
            id1, id2, score = candidates[0]
            QMessageBox.information(
                self,
                tr("id_management.merge_suggestion"),
                tr("id_management.merge_suggestion_message",
                   id1=id1, id2=id2, score=score)
            )
    
    def _update_preview(self) -> None:
        """プレビューを更新"""
        if not self.current_mask_dto or not self.preview_check.isChecked():
            return
        
        # 現在の操作に応じたプレビューを生成
        selected_items = self.id_list.selectedItems()
        
        if selected_items:
            # 削除プレビュー
            target_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
            params = {
                "type": "delete",
                "mask_data": self.current_mask_dto.to_dict(),
                "target_ids": target_ids
            }
            self.preview_requested.emit("delete", params)
        else:
            # 閾値プレビュー
            threshold = self.detection_slider.value() / 100.0
            params = {
                "type": "threshold",
                "mask_data": self.current_mask_dto.to_dict(),
                "confidences": self.current_mask_dto.confidences,
                "threshold": threshold
            }
            self.preview_requested.emit("threshold", params)