#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国際化（i18n）モジュール

NFR-16要件に基づく日本語UI対応。
将来的な多言語対応を考慮した設計。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QTranslator, QLocale, QCoreApplication

logger = logging.getLogger(__name__)


class I18nManager:
    """国際化マネージャー
    
    UIの多言語対応を管理。日本語をデフォルトとし、
    英語・中国語等への切替をサポート。
    """
    
    def __init__(self, app: QCoreApplication):
        """
        Args:
            app: Qtアプリケーションインスタンス
        """
        self.app = app
        self.translator = QTranslator()
        self.current_locale = "ja_JP"  # デフォルトは日本語
        self.translations: Dict[str, Dict[str, str]] = {}
        self.translations_dir = Path(__file__).parent.parent.parent / "resources" / "translations"
        
        # 翻訳ディレクトリの作成
        self.translations_dir.mkdir(parents=True, exist_ok=True)
        
        # デフォルト翻訳の読み込み
        self._load_translations()
        
    def _load_translations(self) -> None:
        """翻訳ファイルの読み込み"""
        # 日本語翻訳
        ja_file = self.translations_dir / "ja_JP.json"
        if ja_file.exists():
            with open(ja_file, "r", encoding="utf-8") as f:
                self.translations["ja_JP"] = json.load(f)
        else:
            # デフォルト日本語翻訳を作成
            self.translations["ja_JP"] = self._get_default_japanese_translations()
            self._save_translations("ja_JP")
        
        # 英語翻訳
        en_file = self.translations_dir / "en_US.json"
        if en_file.exists():
            with open(en_file, "r", encoding="utf-8") as f:
                self.translations["en_US"] = json.load(f)
        else:
            # デフォルト英語翻訳を作成
            self.translations["en_US"] = self._get_default_english_translations()
            self._save_translations("en_US")
    
    def _get_default_japanese_translations(self) -> Dict[str, str]:
        """デフォルト日本語翻訳"""
        return {
            # メニュー
            "menu.file": "ファイル(&F)",
            "menu.file.new_project": "新規プロジェクト(&N)",
            "menu.file.open_project": "プロジェクトを開く(&O)...",
            "menu.file.save_project": "プロジェクトを保存(&S)",
            "menu.file.save_project_as": "プロジェクトに名前を付けて保存(&A)...",
            "menu.file.import_video": "動画をインポート(&I)...",
            "menu.file.export_video": "動画をエクスポート(&E)...",
            "menu.file.recent_projects": "最近使用したプロジェクト",
            "menu.file.exit": "終了(&X)",
            
            "menu.edit": "編集(&E)",
            "menu.edit.undo": "元に戻す(&U)",
            "menu.edit.redo": "やり直す(&R)",
            "menu.edit.cut": "切り取り(&T)",
            "menu.edit.copy": "コピー(&C)",
            "menu.edit.paste": "貼り付け(&P)",
            "menu.edit.delete": "削除(&D)",
            "menu.edit.select_all": "すべて選択(&A)",
            "menu.edit.preferences": "環境設定(&P)...",
            
            "menu.view": "表示(&V)",
            "menu.view.zoom_in": "拡大(&I)",
            "menu.view.zoom_out": "縮小(&O)",
            "menu.view.zoom_fit": "画面に合わせる(&F)",
            "menu.view.zoom_100": "100%表示(&1)",
            "menu.view.fullscreen": "フルスクリーン(&F)",
            "menu.view.show_timeline": "タイムラインを表示(&T)",
            "menu.view.show_properties": "プロパティを表示(&P)",
            "menu.view.show_alerts": "アラートを表示(&A)",
            
            "menu.tools": "ツール(&T)",
            "menu.tools.mask_editor": "マスクエディター(&M)",
            "menu.tools.effect_editor": "エフェクトエディター(&E)",
            "menu.tools.batch_processing": "バッチ処理(&B)...",
            "menu.tools.statistics": "統計情報(&S)...",
            
            "menu.help": "ヘルプ(&H)",
            "menu.help.documentation": "ドキュメント(&D)",
            "menu.help.keyboard_shortcuts": "キーボードショートカット(&K)",
            "menu.help.about": "Mask Editor GODについて(&A)",
            
            # ツールバー
            "toolbar.new": "新規",
            "toolbar.open": "開く",
            "toolbar.save": "保存",
            "toolbar.undo": "元に戻す",
            "toolbar.redo": "やり直す",
            "toolbar.play": "再生",
            "toolbar.pause": "一時停止",
            "toolbar.stop": "停止",
            "toolbar.previous_frame": "前のフレーム",
            "toolbar.next_frame": "次のフレーム",
            "toolbar.zoom_in": "拡大",
            "toolbar.zoom_out": "縮小",
            "toolbar.zoom_fit": "フィット",
            
            # ステータスバー
            "status.ready": "準備完了",
            "status.loading": "読み込み中...",
            "status.saving": "保存中...",
            "status.processing": "処理中...",
            "status.frame_info": "フレーム: {current}/{total}",
            "status.zoom_level": "ズーム: {zoom}%",
            "status.fps": "FPS: {fps}",
            "status.memory": "メモリ: {used}/{total} GB",
            "status.gpu": "GPU: {usage}%",
            
            # ダイアログ
            "dialog.confirm": "確認",
            "dialog.warning": "警告",
            "dialog.error": "エラー",
            "dialog.info": "情報",
            "dialog.ok": "OK",
            "dialog.cancel": "キャンセル",
            "dialog.yes": "はい",
            "dialog.no": "いいえ",
            "dialog.apply": "適用",
            "dialog.close": "閉じる",
            
            # ファイルダイアログ
            "file_dialog.video_files": "動画ファイル",
            "file_dialog.project_files": "プロジェクトファイル",
            "file_dialog.mask_files": "マスクファイル",
            "file_dialog.all_files": "すべてのファイル",
            
            # プレイヤーコントロール
            "player.play": "再生",
            "player.pause": "一時停止",
            "player.stop": "停止",
            "player.speed": "再生速度",
            "player.loop": "ループ",
            "player.frame": "フレーム",
            "player.time": "時間",
            
            # エラーメッセージ
            "error.file_not_found": "ファイルが見つかりません: {filepath}",
            "error.invalid_format": "無効なファイル形式です: {format}",
            "error.save_failed": "保存に失敗しました: {reason}",
            "error.load_failed": "読み込みに失敗しました: {reason}",
            "error.memory_insufficient": "メモリが不足しています",
            "error.gpu_not_available": "GPUが利用できません",
            
            # ドック
            "dock.timeline": "タイムライン",
            "dock.project": "プロジェクト",
            "dock.properties": "プロパティ",
            "dock.alerts": "アラート",
            "dock.mask_edit": "マスク編集",
            "dock.mask_display": "マスク表示設定",
            
            # マスク編集
            "mask_edit.title": "マスク編集",
            "mask_edit.morphology": "モルフォロジー操作",
            "mask_edit.operation": "操作:",
            "mask_edit.dilate": "膨張",
            "mask_edit.erode": "収縮",
            "mask_edit.open": "オープン",
            "mask_edit.close": "クローズ",
            "mask_edit.kernel_size": "カーネルサイズ:",
            "mask_edit.preview": "プレビュー",
            "mask_edit.apply": "適用",
            "mask_edit.reset": "リセット",
            "mask_edit.history": "編集履歴",
            "mask_edit.undo": "元に戻す",
            "mask_edit.redo": "やり直す",
            
            # マスク表示
            "mask_display.title": "マスク表示設定",
            "mask_display.overlay": "オーバーレイ",
            "mask_display.enabled": "オーバーレイを表示",
            "mask_display.opacity": "不透明度:",
            "mask_display.show_outlines": "輪郭線を表示",
            "mask_display.outline_width": "輪郭線の太さ:",
            "mask_display.show_labels": "ラベルを表示",
            "mask_display.mask_list": "マスク一覧",
            "mask_display.id": "ID",
            "mask_display.class": "クラス",
            "mask_display.confidence": "信頼度",
            "mask_display.visible": "表示",
            "mask_display.color": "色",
            "mask_display.select_all": "全選択",
            "mask_display.deselect_all": "全解除",
            "mask_display.select_color": "色を選択",
            
            # プロジェクト管理
            "project.info.title": "プロジェクト情報",
            "project.info.no_project": "プロジェクトが開かれていません",
            "project.info.unsaved": "未保存",
            "project.info.last_modified": "最終更新",
            "project.action.new": "新規作成",
            "project.action.open": "開く",
            "project.action.save": "保存",
            "project.action.save_as": "名前を付けて保存",
            "project.recent.title": "最近のプロジェクト",
            "project.recent.refresh": "更新",
            "project.autosave.title": "自動保存",
            "project.autosave.enabled": "自動保存: 有効",
            "project.autosave.disabled": "自動保存: 無効",
            "project.autosave.next_save": "次回保存まで: {minutes}分{seconds}秒",
            "project.dialog.open_title": "プロジェクトを開く",
            "project.dialog.save_title": "プロジェクトを保存",
            "project.dialog.filter": "Mask Editor プロジェクト (*.mosaicproj)",
            "project.error.save_title": "保存エラー",
            "project.error.save_message": "プロジェクトの保存中にエラーが発生しました:\n{error}",
            "project.error.open_title": "読み込みエラー",
            "project.error.open_message": "プロジェクトの読み込み中にエラーが発生しました:\n{error}",
            "project.confirm.discard_title": "変更を破棄",
            "project.confirm.discard_message": "保存されていない変更があります。保存しますか？",
        }
    
    def _get_default_english_translations(self) -> Dict[str, str]:
        """デフォルト英語翻訳"""
        return {
            # メニュー
            "menu.file": "&File",
            "menu.file.new_project": "&New Project",
            "menu.file.open_project": "&Open Project...",
            "menu.file.save_project": "&Save Project",
            "menu.file.save_project_as": "Save Project &As...",
            "menu.file.import_video": "&Import Video...",
            "menu.file.export_video": "&Export Video...",
            "menu.file.recent_projects": "Recent Projects",
            "menu.file.exit": "E&xit",
            
            "menu.edit": "&Edit",
            "menu.edit.undo": "&Undo",
            "menu.edit.redo": "&Redo",
            "menu.edit.cut": "Cu&t",
            "menu.edit.copy": "&Copy",
            "menu.edit.paste": "&Paste",
            "menu.edit.delete": "&Delete",
            "menu.edit.select_all": "Select &All",
            "menu.edit.preferences": "&Preferences...",
            
            "menu.view": "&View",
            "menu.view.zoom_in": "Zoom &In",
            "menu.view.zoom_out": "Zoom &Out",
            "menu.view.zoom_fit": "&Fit to Window",
            "menu.view.zoom_100": "&100% View",
            "menu.view.fullscreen": "&Fullscreen",
            "menu.view.show_timeline": "Show &Timeline",
            "menu.view.show_properties": "Show &Properties",
            "menu.view.show_alerts": "Show &Alerts",
            
            "menu.tools": "&Tools",
            "menu.tools.mask_editor": "&Mask Editor",
            "menu.tools.effect_editor": "&Effect Editor",
            "menu.tools.batch_processing": "&Batch Processing...",
            "menu.tools.statistics": "&Statistics...",
            
            "menu.help": "&Help",
            "menu.help.documentation": "&Documentation",
            "menu.help.keyboard_shortcuts": "&Keyboard Shortcuts",
            "menu.help.about": "&About Mask Editor GOD",
            
            # ツールバー
            "toolbar.new": "New",
            "toolbar.open": "Open",
            "toolbar.save": "Save",
            "toolbar.undo": "Undo",
            "toolbar.redo": "Redo",
            "toolbar.play": "Play",
            "toolbar.pause": "Pause",
            "toolbar.stop": "Stop",
            "toolbar.previous_frame": "Previous Frame",
            "toolbar.next_frame": "Next Frame",
            "toolbar.zoom_in": "Zoom In",
            "toolbar.zoom_out": "Zoom Out",
            "toolbar.zoom_fit": "Fit",
            
            # ステータスバー
            "status.ready": "Ready",
            "status.loading": "Loading...",
            "status.saving": "Saving...",
            "status.processing": "Processing...",
            "status.frame_info": "Frame: {current}/{total}",
            "status.zoom_level": "Zoom: {zoom}%",
            "status.fps": "FPS: {fps}",
            "status.memory": "Memory: {used}/{total} GB",
            "status.gpu": "GPU: {usage}%",
            
            # ダイアログ
            "dialog.confirm": "Confirm",
            "dialog.warning": "Warning",
            "dialog.error": "Error",
            "dialog.info": "Information",
            "dialog.ok": "OK",
            "dialog.cancel": "Cancel",
            "dialog.yes": "Yes",
            "dialog.no": "No",
            "dialog.apply": "Apply",
            "dialog.close": "Close",
            
            # ファイルダイアログ
            "file_dialog.video_files": "Video Files",
            "file_dialog.project_files": "Project Files",
            "file_dialog.mask_files": "Mask Files",
            "file_dialog.all_files": "All Files",
            
            # プレイヤーコントロール
            "player.play": "Play",
            "player.pause": "Pause",
            "player.stop": "Stop",
            "player.speed": "Speed",
            "player.loop": "Loop",
            "player.frame": "Frame",
            "player.time": "Time",
            
            # エラーメッセージ
            "error.file_not_found": "File not found: {filepath}",
            "error.invalid_format": "Invalid file format: {format}",
            "error.save_failed": "Failed to save: {reason}",
            "error.load_failed": "Failed to load: {reason}",
            "error.memory_insufficient": "Insufficient memory",
            "error.gpu_not_available": "GPU not available",
            
            # Docks
            "dock.timeline": "Timeline",
            "dock.project": "Project",
            "dock.properties": "Properties",
            "dock.alerts": "Alerts",
            "dock.mask_edit": "Mask Edit",
            "dock.mask_display": "Mask Display Settings",
            
            # Mask Edit
            "mask_edit.title": "Mask Edit",
            "mask_edit.morphology": "Morphology Operations",
            "mask_edit.operation": "Operation:",
            "mask_edit.dilate": "Dilate",
            "mask_edit.erode": "Erode",
            "mask_edit.open": "Open",
            "mask_edit.close": "Close",
            "mask_edit.kernel_size": "Kernel Size:",
            "mask_edit.preview": "Preview",
            "mask_edit.apply": "Apply",
            "mask_edit.reset": "Reset",
            "mask_edit.history": "Edit History",
            "mask_edit.undo": "Undo",
            "mask_edit.redo": "Redo",
            
            # Mask Display
            "mask_display.title": "Mask Display Settings",
            "mask_display.overlay": "Overlay",
            "mask_display.enabled": "Show Overlay",
            "mask_display.opacity": "Opacity:",
            "mask_display.show_outlines": "Show Outlines",
            "mask_display.outline_width": "Outline Width:",
            "mask_display.show_labels": "Show Labels",
            "mask_display.mask_list": "Mask List",
            "mask_display.id": "ID",
            "mask_display.class": "Class",
            "mask_display.confidence": "Confidence",
            "mask_display.visible": "Visible",
            "mask_display.color": "Color",
            "mask_display.select_all": "Select All",
            "mask_display.deselect_all": "Deselect All",
            "mask_display.select_color": "Select Color",
            
            # Project Management
            "project.info.title": "Project Information",
            "project.info.no_project": "No project is open",
            "project.info.unsaved": "Unsaved",
            "project.info.last_modified": "Last Modified",
            "project.action.new": "New",
            "project.action.open": "Open",
            "project.action.save": "Save",
            "project.action.save_as": "Save As",
            "project.recent.title": "Recent Projects",
            "project.recent.refresh": "Refresh",
            "project.autosave.title": "Auto-save",
            "project.autosave.enabled": "Auto-save: Enabled",
            "project.autosave.disabled": "Auto-save: Disabled",
            "project.autosave.next_save": "Next save in: {minutes}m {seconds}s",
            "project.dialog.open_title": "Open Project",
            "project.dialog.save_title": "Save Project",
            "project.dialog.filter": "Mask Editor Project (*.mosaicproj)",
            "project.error.save_title": "Save Error",
            "project.error.save_message": "An error occurred while saving the project:\n{error}",
            "project.error.open_title": "Open Error",
            "project.error.open_message": "An error occurred while opening the project:\n{error}",
            "project.confirm.discard_title": "Discard Changes",
            "project.confirm.discard_message": "You have unsaved changes. Do you want to save them?",
        }
    
    def _save_translations(self, locale: str) -> None:
        """翻訳をファイルに保存"""
        filepath = self.translations_dir / f"{locale}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.translations[locale], f, ensure_ascii=False, indent=2)
    
    def set_locale(self, locale: str) -> bool:
        """ロケールを設定
        
        Args:
            locale: ロケール文字列（例: "ja_JP", "en_US"）
            
        Returns:
            成功した場合True
        """
        if locale not in self.translations:
            logger.warning(f"Unsupported locale: {locale}")
            return False
        
        self.current_locale = locale
        logger.info(f"Locale set to: {locale}")
        return True
    
    def tr(self, key: str, **kwargs) -> str:
        """翻訳を取得
        
        Args:
            key: 翻訳キー
            **kwargs: 翻訳文字列内の変数
            
        Returns:
            翻訳された文字列
        """
        translations = self.translations.get(self.current_locale, {})
        text = translations.get(key, key)
        
        # 変数の置換
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing translation variable: {e}")
        
        return text
    
    def get_available_locales(self) -> list[str]:
        """利用可能なロケールのリストを取得"""
        return list(self.translations.keys())
    
    def get_locale_display_name(self, locale: str) -> str:
        """ロケールの表示名を取得"""
        display_names = {
            "ja_JP": "日本語",
            "en_US": "English",
            "zh_CN": "中文（简体）",
            "zh_TW": "中文（繁體）",
            "ko_KR": "한국어",
        }
        return display_names.get(locale, locale)


# グローバルインスタンス
_i18n_manager: Optional[I18nManager] = None


def get_translator() -> I18nManager:
    """グローバル翻訳マネージャーを取得
    
    Returns:
        I18nManager インスタンス
        
    Raises:
        RuntimeError: 初期化されていない場合
    """
    if _i18n_manager is None:
        raise RuntimeError("I18n not initialized. Call init_i18n() first.")
    return _i18n_manager


def init_i18n(app: QCoreApplication) -> I18nManager:
    """i18nマネージャーを初期化"""
    global _i18n_manager
    _i18n_manager = I18nManager(app)
    return _i18n_manager


def get_i18n() -> I18nManager:
    """i18nマネージャーを取得"""
    if _i18n_manager is None:
        raise RuntimeError("I18n manager not initialized")
    return _i18n_manager


def tr(key: str, **kwargs) -> str:
    """翻訳ショートカット関数"""
    return get_i18n().tr(key, **kwargs)