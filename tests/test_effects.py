#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エフェクトシステムのテスト

エフェクトエンジン、個別エフェクト、プリセット管理のテストを実施。
"""
import unittest
import numpy as np
import tempfile
import shutil
from pathlib import Path

from domain.dto.effect_dto import (
    EffectType, EffectConfigDTO, EffectParameterDTO,
    ParameterType, STANDARD_EFFECTS
)
from domain.dto.frame_dto import FrameDTO
from domain.dto.mask_dto import MaskDTO
from adapters.secondary.effects import MosaicEffect, BlurEffect, PixelateEffect
from adapters.secondary.effect_engine import EffectEngine
from adapters.secondary.effect_preset_manager import EffectPresetManager


class TestEffectDTOs(unittest.TestCase):
    """エフェクトDTOのテスト"""
    
    def test_effect_parameter_validation(self):
        """パラメータ検証のテスト"""
        # 整数パラメータ
        param = EffectParameterDTO(
            name="test_int",
            display_name="Test Integer",
            parameter_type=ParameterType.INTEGER,
            default_value=10,
            min_value=0,
            max_value=100
        )
        
        # 正常値
        self.assertTrue(param.validate_value(50))
        self.assertTrue(param.validate_value(0))
        self.assertTrue(param.validate_value(100))
        
        # 異常値
        self.assertFalse(param.validate_value(-1))
        self.assertFalse(param.validate_value(101))
        self.assertFalse(param.validate_value(10.5))  # 型が違う
        
    def test_effect_config_dto(self):
        """エフェクト設定DTOのテスト"""
        config = EffectConfigDTO(
            effect_type=EffectType.MOSAIC,
            effect_id="mosaic_1",
            parameters={"block_size": 16, "shape": "square"},
            intensity=0.8
        )
        
        self.assertEqual(config.effect_type, EffectType.MOSAIC)
        self.assertEqual(config.effect_id, "mosaic_1")
        self.assertEqual(config.intensity, 0.8)
        
        # 辞書変換
        data = config.to_dict()
        self.assertEqual(data["effect_type"], "mosaic")
        self.assertEqual(data["parameters"]["block_size"], 16)
        
        # 辞書から復元
        restored = EffectConfigDTO.from_dict(data)
        self.assertEqual(restored.effect_id, config.effect_id)
        self.assertEqual(restored.parameters, config.parameters)


class TestBasicEffects(unittest.TestCase):
    """基本エフェクトのテスト"""
    
    def setUp(self):
        """テスト用データの準備"""
        # テスト画像（100x100 RGB）
        self.test_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        
        # テストマスク（中央50x50領域）
        self.test_mask = np.zeros((100, 100), dtype=np.uint8)
        self.test_mask[25:75, 25:75] = 255
    
    def test_mosaic_effect(self):
        """モザイクエフェクトのテスト"""
        effect = MosaicEffect()
        
        # エフェクト設定
        config = EffectConfigDTO(
            effect_type=EffectType.MOSAIC,
            effect_id="test_mosaic",
            parameters={"block_size": 8, "shape": "square"}
        )
        
        # 設定の妥当性確認
        self.assertTrue(effect.validate_config(config))
        
        # エフェクト適用
        result_frame, result = effect.apply(
            self.test_frame,
            self.test_mask,
            config
        )
        
        # 結果確認
        self.assertTrue(result.success)
        self.assertIsInstance(result_frame, np.ndarray)
        self.assertEqual(result_frame.shape, self.test_frame.shape)
        self.assertGreater(result.processing_time_ms, 0)
        self.assertEqual(result.statistics["block_size"], 8)
        
        # マスク領域が変更されていることを確認
        masked_region = result_frame[25:75, 25:75]
        original_region = self.test_frame[25:75, 25:75]
        self.assertFalse(np.array_equal(masked_region, original_region))
        
        # マスク外領域は変更されていないことを確認
        unmasked_region = result_frame[0:25, 0:25]
        original_unmasked = self.test_frame[0:25, 0:25]
        self.assertTrue(np.array_equal(unmasked_region, original_unmasked))
    
    def test_blur_effect(self):
        """ブラーエフェクトのテスト"""
        effect = BlurEffect()
        
        # エフェクト設定
        config = EffectConfigDTO(
            effect_type=EffectType.BLUR,
            effect_id="test_blur",
            parameters={"radius": 5.0, "quality": "medium"}
        )
        
        # エフェクト適用
        result_frame, result = effect.apply(
            self.test_frame,
            self.test_mask,
            config
        )
        
        # 結果確認
        self.assertTrue(result.success)
        self.assertEqual(result.statistics["radius"], 5.0)
        self.assertEqual(result.statistics["quality"], "medium")
    
    def test_pixelate_effect(self):
        """ピクセレートエフェクトのテスト"""
        effect = PixelateEffect()
        
        # エフェクト設定
        config = EffectConfigDTO(
            effect_type=EffectType.PIXELATE,
            effect_id="test_pixelate",
            parameters={"pixel_size": 4, "interpolation": "nearest"}
        )
        
        # エフェクト適用
        result_frame, result = effect.apply(
            self.test_frame,
            self.test_mask,
            config
        )
        
        # 結果確認
        self.assertTrue(result.success)
        self.assertEqual(result.statistics["pixel_size"], 4)
        self.assertIn("effective_pixels", result.statistics)


class TestEffectEngine(unittest.TestCase):
    """エフェクトエンジンのテスト"""
    
    def setUp(self):
        """テスト環境のセットアップ"""
        self.engine = EffectEngine(max_workers=2)
        
        # テストフレーム
        self.frame_dto = FrameDTO(
            data=np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8),
            width=100,
            height=100,
            frame_number=0,
            timestamp_ms=0
        )
        
        # テストマスク
        mask_data = np.zeros((100, 100), dtype=np.uint8)
        mask_data[25:75, 25:75] = 255
        self.mask_dto = MaskDTO(
            data=mask_data,
            mask_id=1,
            class_name="test",
            confidence=1.0,
            frame_index=0
        )
    
    def test_get_available_effects(self):
        """利用可能なエフェクト一覧取得のテスト"""
        effects = self.engine.get_available_effects()
        
        # 標準エフェクトが登録されているか確認
        effect_types = [e.effect_type for e in effects]
        self.assertIn(EffectType.MOSAIC, effect_types)
        self.assertIn(EffectType.BLUR, effect_types)
        self.assertIn(EffectType.PIXELATE, effect_types)
    
    def test_apply_single_effect(self):
        """単一エフェクト適用のテスト"""
        # エフェクト設定
        config = EffectConfigDTO(
            effect_type=EffectType.MOSAIC,
            effect_id="test_1",
            parameters={"block_size": 16, "shape": "square"}
        )
        
        # エフェクト適用
        result_frame, results = self.engine.apply_effects(
            self.frame_dto,
            [self.mask_dto],
            [config]
        )
        
        # 結果確認
        self.assertIsInstance(result_frame, FrameDTO)
        self.assertIn("test_1", results)
        self.assertTrue(results["test_1"].success)
        self.assertIn("_total", results)
    
    def test_apply_multiple_effects(self):
        """複数エフェクト連続適用のテスト"""
        # 複数のエフェクト設定
        configs = [
            EffectConfigDTO(
                effect_type=EffectType.BLUR,
                effect_id="blur_1",
                parameters={"radius": 3.0, "quality": "low"},
                intensity=0.5
            ),
            EffectConfigDTO(
                effect_type=EffectType.MOSAIC,
                effect_id="mosaic_1",
                parameters={"block_size": 8, "shape": "square"},
                intensity=0.7
            )
        ]
        
        # エフェクト適用
        result_frame, results = self.engine.apply_effects(
            self.frame_dto,
            [self.mask_dto],
            configs
        )
        
        # 両方のエフェクトが適用されたか確認
        self.assertIn("blur_1", results)
        self.assertIn("mosaic_1", results)
        self.assertTrue(results["blur_1"].success)
        self.assertTrue(results["mosaic_1"].success)
    
    def test_preview_mode(self):
        """プレビューモードのテスト"""
        config = EffectConfigDTO(
            effect_type=EffectType.BLUR,
            effect_id="preview_test",
            parameters={"radius": 20.0, "quality": "high"}
        )
        
        # プレビューモードで適用
        result_frame, results = self.engine.apply_effects(
            self.frame_dto,
            [self.mask_dto],
            [config],
            preview_mode=True
        )
        
        # プレビューモードでは品質が下がることを確認
        self.assertTrue(results["preview_test"].success)
        self.assertTrue(results["_total"].statistics["preview_mode"])


class TestEffectPresetManager(unittest.TestCase):
    """プリセットマネージャーのテスト"""
    
    def setUp(self):
        """テスト用ディレクトリの作成"""
        self.temp_dir = tempfile.mkdtemp()
        self.preset_manager = EffectPresetManager(self.temp_dir)
    
    def tearDown(self):
        """テスト用ディレクトリの削除"""
        shutil.rmtree(self.temp_dir)
    
    def test_default_presets(self):
        """デフォルトプリセットの確認"""
        presets = self.preset_manager.list_presets()
        
        # デフォルトプリセットが存在することを確認
        self.assertGreater(len(presets), 0)
        
        # モザイクプリセットの確認
        mosaic_presets = [p for p in presets if p.effect_type == EffectType.MOSAIC]
        self.assertGreater(len(mosaic_presets), 0)
    
    def test_save_and_load_preset(self):
        """プリセット保存/読み込みのテスト"""
        from domain.dto.effect_dto import EffectPresetDTO
        
        # テストプリセット作成
        preset = EffectPresetDTO(
            name="テストプリセット",
            description="これはテストです",
            effect_type=EffectType.BLUR,
            parameters={"radius": 15.0, "quality": "high"},
            category="test",
            tags=["test", "sample"]
        )
        
        # 保存
        self.assertTrue(self.preset_manager.save_preset(preset))
        
        # 読み込み
        loaded = self.preset_manager.load_preset("テストプリセット")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, preset.name)
        self.assertEqual(loaded.parameters["radius"], 15.0)
        
        # 削除
        self.assertTrue(self.preset_manager.delete_preset("テストプリセット"))
        self.assertIsNone(self.preset_manager.load_preset("テストプリセット"))
    
    def test_export_import_presets(self):
        """プリセットのエクスポート/インポートテスト"""
        export_path = Path(self.temp_dir) / "export.json"
        
        # エクスポート
        self.assertTrue(self.preset_manager.export_presets(str(export_path)))
        self.assertTrue(export_path.exists())
        
        # 新しいマネージャーでインポート
        new_temp_dir = tempfile.mkdtemp()
        try:
            new_manager = EffectPresetManager(new_temp_dir)
            
            # デフォルトプリセットをクリア（テスト用）
            imported_count = new_manager.import_presets(str(export_path))
            self.assertGreater(imported_count, 0)
            
            # インポートされたプリセットの確認
            presets = new_manager.list_presets()
            self.assertGreater(len(presets), 0)
            
        finally:
            shutil.rmtree(new_temp_dir)


if __name__ == '__main__':
    unittest.main()