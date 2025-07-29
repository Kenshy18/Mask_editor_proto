#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクトプリセットマネージャー実装

エフェクトプリセットの管理機能を提供。
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import shutil

from domain.dto.effect_dto import EffectType, EffectPresetDTO
from domain.ports.secondary.effect_ports import IEffectPresetManager

logger = logging.getLogger(__name__)


class EffectPresetManager:
    """エフェクトプリセットマネージャー実装"""
    
    def __init__(self, preset_dir: str = None):
        """
        初期化
        
        Args:
            preset_dir: プリセット保存ディレクトリ
        """
        if preset_dir is None:
            # デフォルトディレクトリ（ユーザーホーム）
            preset_dir = os.path.join(
                Path.home(), 
                ".mask_editor_god", 
                "presets"
            )
        
        self._preset_dir = Path(preset_dir)
        self._preset_dir.mkdir(parents=True, exist_ok=True)
        
        # カテゴリーディレクトリを作成
        self._categories = ["basic", "advanced", "custom", "shared"]
        for category in self._categories:
            (self._preset_dir / category).mkdir(exist_ok=True)
        
        # デフォルトプリセットを初期化
        self._initialize_default_presets()
    
    def save_preset(self, preset: EffectPresetDTO) -> bool:
        """
        プリセットを保存
        
        Args:
            preset: プリセット
            
        Returns:
            成功した場合True
        """
        try:
            # カテゴリーディレクトリを決定
            category = preset.category or "custom"
            category_dir = self._preset_dir / category
            category_dir.mkdir(exist_ok=True)
            
            # ファイル名を生成（名前から不正な文字を除去）
            safe_name = self._sanitize_filename(preset.name)
            file_path = category_dir / f"{safe_name}.json"
            
            # プリセットデータを作成
            preset_data = {
                "name": preset.name,
                "description": preset.description,
                "effect_type": preset.effect_type.value,
                "parameters": preset.parameters,
                "category": category,
                "tags": preset.tags,
                "thumbnail": preset.thumbnail,
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            # JSONファイルに保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved preset: {preset.name} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save preset: {preset.name}", exc_info=True)
            return False
    
    def load_preset(self, name: str) -> Optional[EffectPresetDTO]:
        """
        プリセットを読み込み
        
        Args:
            name: プリセット名
            
        Returns:
            プリセット（存在しない場合None）
        """
        try:
            # 全カテゴリーを検索
            for category_dir in self._preset_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                
                # ファイルを検索
                safe_name = self._sanitize_filename(name)
                file_path = category_dir / f"{safe_name}.json"
                
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # DTOに変換
                    preset = EffectPresetDTO(
                        name=data["name"],
                        description=data.get("description"),
                        effect_type=EffectType(data["effect_type"]),
                        parameters=data["parameters"],
                        category=data.get("category"),
                        tags=data.get("tags", []),
                        thumbnail=data.get("thumbnail")
                    )
                    
                    return preset
            
            logger.warning(f"Preset not found: {name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load preset: {name}", exc_info=True)
            return None
    
    def list_presets(
        self, 
        effect_type: Optional[EffectType] = None,
        category: Optional[str] = None
    ) -> List[EffectPresetDTO]:
        """
        プリセット一覧を取得
        
        Args:
            effect_type: フィルタリング用エフェクトタイプ
            category: フィルタリング用カテゴリー
            
        Returns:
            プリセットリスト
        """
        presets = []
        
        try:
            # 検索対象のディレクトリを決定
            if category:
                search_dirs = [self._preset_dir / category]
            else:
                search_dirs = [d for d in self._preset_dir.iterdir() if d.is_dir()]
            
            # 各ディレクトリを検索
            for category_dir in search_dirs:
                for file_path in category_dir.glob("*.json"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # エフェクトタイプでフィルタリング
                        if effect_type and data["effect_type"] != effect_type.value:
                            continue
                        
                        # DTOに変換
                        preset = EffectPresetDTO(
                            name=data["name"],
                            description=data.get("description"),
                            effect_type=EffectType(data["effect_type"]),
                            parameters=data["parameters"],
                            category=data.get("category", category_dir.name),
                            tags=data.get("tags", []),
                            thumbnail=data.get("thumbnail")
                        )
                        
                        presets.append(preset)
                        
                    except Exception as e:
                        logger.warning(f"Failed to load preset file: {file_path}", exc_info=True)
            
            # 名前でソート
            presets.sort(key=lambda p: p.name)
            
        except Exception as e:
            logger.error("Failed to list presets", exc_info=True)
        
        return presets
    
    def delete_preset(self, name: str) -> bool:
        """
        プリセットを削除
        
        Args:
            name: プリセット名
            
        Returns:
            成功した場合True
        """
        try:
            # 全カテゴリーを検索
            for category_dir in self._preset_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                
                # ファイルを検索
                safe_name = self._sanitize_filename(name)
                file_path = category_dir / f"{safe_name}.json"
                
                if file_path.exists():
                    # バックアップを作成
                    backup_dir = self._preset_dir / ".backup"
                    backup_dir.mkdir(exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = backup_dir / f"{safe_name}_{timestamp}.json"
                    shutil.copy2(file_path, backup_path)
                    
                    # 削除
                    file_path.unlink()
                    logger.info(f"Deleted preset: {name} (backup: {backup_path})")
                    return True
            
            logger.warning(f"Preset not found: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete preset: {name}", exc_info=True)
            return False
    
    def export_presets(self, path: str) -> bool:
        """
        プリセットをファイルにエクスポート
        
        Args:
            path: エクスポート先パス
            
        Returns:
            成功した場合True
        """
        try:
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "presets": []
            }
            
            # 全プリセットを収集
            for preset in self.list_presets():
                preset_data = {
                    "name": preset.name,
                    "description": preset.description,
                    "effect_type": preset.effect_type.value,
                    "parameters": preset.parameters,
                    "category": preset.category,
                    "tags": preset.tags,
                    "thumbnail": preset.thumbnail
                }
                export_data["presets"].append(preset_data)
            
            # JSONファイルに保存
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported {len(export_data['presets'])} presets to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export presets to {path}", exc_info=True)
            return False
    
    def import_presets(self, path: str) -> int:
        """
        プリセットをファイルからインポート
        
        Args:
            path: インポート元パス
            
        Returns:
            インポートしたプリセット数
        """
        imported = 0
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # バージョンチェック
            version = data.get("version", "1.0")
            if version != "1.0":
                logger.warning(f"Unsupported preset file version: {version}")
            
            # 各プリセットをインポート
            for preset_data in data.get("presets", []):
                try:
                    preset = EffectPresetDTO(
                        name=preset_data["name"],
                        description=preset_data.get("description"),
                        effect_type=EffectType(preset_data["effect_type"]),
                        parameters=preset_data["parameters"],
                        category=preset_data.get("category", "imported"),
                        tags=preset_data.get("tags", []),
                        thumbnail=preset_data.get("thumbnail")
                    )
                    
                    # 既存のプリセットと名前が重複する場合は番号を付ける
                    original_name = preset.name
                    counter = 1
                    while self.load_preset(preset.name) is not None:
                        preset = EffectPresetDTO(
                            name=f"{original_name} ({counter})",
                            description=preset.description,
                            effect_type=preset.effect_type,
                            parameters=preset.parameters,
                            category=preset.category,
                            tags=preset.tags,
                            thumbnail=preset.thumbnail
                        )
                        counter += 1
                    
                    if self.save_preset(preset):
                        imported += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to import preset: {preset_data.get('name', 'Unknown')}", exc_info=True)
            
            logger.info(f"Imported {imported} presets from {path}")
            
        except Exception as e:
            logger.error(f"Failed to import presets from {path}", exc_info=True)
        
        return imported
    
    def _sanitize_filename(self, name: str) -> str:
        """ファイル名として安全な文字列に変換"""
        # 不正な文字を置換
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # 空白をアンダースコアに
        name = name.replace(' ', '_')
        
        # 長さを制限
        if len(name) > 100:
            name = name[:100]
        
        return name
    
    def _initialize_default_presets(self):
        """デフォルトプリセットを初期化"""
        default_presets = [
            # モザイクプリセット
            EffectPresetDTO(
                name="軽度モザイク",
                description="軽いモザイク効果",
                effect_type=EffectType.MOSAIC,
                parameters={"block_size": 8, "shape": "square"},
                category="basic",
                tags=["light", "subtle"]
            ),
            EffectPresetDTO(
                name="標準モザイク",
                description="標準的なモザイク効果",
                effect_type=EffectType.MOSAIC,
                parameters={"block_size": 16, "shape": "square"},
                category="basic",
                tags=["standard", "default"]
            ),
            EffectPresetDTO(
                name="強力モザイク",
                description="強いモザイク効果",
                effect_type=EffectType.MOSAIC,
                parameters={"block_size": 32, "shape": "square"},
                category="basic",
                tags=["strong", "heavy"]
            ),
            
            # ブラープリセット
            EffectPresetDTO(
                name="ソフトブラー",
                description="柔らかいぼかし効果",
                effect_type=EffectType.BLUR,
                parameters={"radius": 5.0, "quality": "high"},
                category="basic",
                tags=["soft", "subtle"]
            ),
            EffectPresetDTO(
                name="標準ブラー",
                description="標準的なぼかし効果",
                effect_type=EffectType.BLUR,
                parameters={"radius": 10.0, "quality": "high"},
                category="basic",
                tags=["standard", "default"]
            ),
            EffectPresetDTO(
                name="強力ブラー",
                description="強いぼかし効果",
                effect_type=EffectType.BLUR,
                parameters={"radius": 20.0, "quality": "high"},
                category="basic",
                tags=["strong", "heavy"]
            ),
            
            # ピクセレートプリセット
            EffectPresetDTO(
                name="細かいピクセル",
                description="細かいピクセル化",
                effect_type=EffectType.PIXELATE,
                parameters={"pixel_size": 4, "interpolation": "linear"},
                category="basic",
                tags=["fine", "detailed"]
            ),
            EffectPresetDTO(
                name="標準ピクセル",
                description="標準的なピクセル化",
                effect_type=EffectType.PIXELATE,
                parameters={"pixel_size": 8, "interpolation": "nearest"},
                category="basic",
                tags=["standard", "default"]
            ),
            EffectPresetDTO(
                name="大きいピクセル",
                description="大きなピクセル化",
                effect_type=EffectType.PIXELATE,
                parameters={"pixel_size": 16, "interpolation": "nearest"},
                category="basic",
                tags=["large", "blocky"]
            )
        ]
        
        # デフォルトプリセットが存在しない場合のみ作成
        for preset in default_presets:
            if not self.load_preset(preset.name):
                self.save_preset(preset)