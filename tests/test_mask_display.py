#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスク表示・編集機能のテスト
"""
import numpy as np
import pytest

from src.domain.dto.frame_dto import FrameDTO
from src.domain.dto.mask_dto import MaskDTO, MaskOverlaySettingsDTO


class TestMaskDTO:
    """MaskDTOのテスト"""
    
    def test_mask_dto_creation(self):
        """MaskDTOの作成テスト"""
        # テストデータ
        mask_data = np.zeros((100, 100), dtype=np.uint8)
        mask_data[20:30, 20:30] = 1  # ID 1のマスク
        mask_data[50:60, 50:60] = 2  # ID 2のマスク
        
        mask_dto = MaskDTO(
            frame_index=0,
            data=mask_data,
            width=100,
            height=100,
            object_ids=[1, 2],
            classes={1: "person", 2: "car"},
            confidences={1: 0.95, 2: 0.88}
        )
        
        assert mask_dto.frame_index == 0
        assert mask_dto.width == 100
        assert mask_dto.height == 100
        assert len(mask_dto.object_ids) == 2
        assert mask_dto.classes[1] == "person"
        assert mask_dto.confidences[2] == 0.88
    
    def test_get_mask_for_id(self):
        """特定IDのマスク取得テスト"""
        mask_data = np.zeros((100, 100), dtype=np.uint8)
        mask_data[20:30, 20:30] = 1
        
        mask_dto = MaskDTO(
            frame_index=0,
            data=mask_data,
            width=100,
            height=100,
            object_ids=[1],
            classes={1: "person"},
            confidences={1: 0.95}
        )
        
        binary_mask = mask_dto.get_mask_for_id(1)
        assert binary_mask.shape == (100, 100)
        assert np.all(binary_mask[20:30, 20:30] == 255)
        assert np.all(binary_mask[0:20, 0:20] == 0)
    
    def test_count_pixels(self):
        """ピクセル数カウントテスト"""
        mask_data = np.zeros((100, 100), dtype=np.uint8)
        mask_data[20:30, 20:30] = 1  # 10x10 = 100ピクセル
        mask_data[50:60, 50:60] = 2  # 10x10 = 100ピクセル
        
        mask_dto = MaskDTO(
            frame_index=0,
            data=mask_data,
            width=100,
            height=100,
            object_ids=[1, 2],
            classes={1: "person", 2: "car"},
            confidences={1: 0.95, 2: 0.88}
        )
        
        assert mask_dto.count_pixels() == 200  # 全体
        assert mask_dto.count_pixels(1) == 100
        assert mask_dto.count_pixels(2) == 100


class TestMaskOverlaySettingsDTO:
    """MaskOverlaySettingsDTOのテスト"""
    
    def test_default_settings(self):
        """デフォルト設定のテスト"""
        settings = MaskOverlaySettingsDTO()
        
        assert settings.opacity == 0.7
        assert settings.enabled is True
        assert len(settings.default_colors) == 10
        assert settings.show_outlines is False
        assert settings.outline_width == 2
        assert settings.show_labels is False
    
    def test_opacity_validation(self):
        """不透明度の検証テスト"""
        with pytest.raises(ValueError):
            MaskOverlaySettingsDTO(opacity=1.5)
        
        with pytest.raises(ValueError):
            MaskOverlaySettingsDTO(opacity=-0.1)
    
    def test_get_mask_color(self):
        """マスク色取得テスト"""
        settings = MaskOverlaySettingsDTO()
        
        # デフォルトカラーの割り当て
        assert settings.get_mask_color(0) == "#FF0000"  # 赤
        assert settings.get_mask_color(1) == "#00FF00"  # 緑
        assert settings.get_mask_color(10) == "#FF0000"  # ループして赤
        
        # カスタムカラーの設定
        settings.mask_colors[1] = "#FFFFFF"
        assert settings.get_mask_color(1) == "#FFFFFF"
    
    def test_is_mask_visible(self):
        """マスク表示判定テスト"""
        settings = MaskOverlaySettingsDTO()
        
        # デフォルトは表示
        assert settings.is_mask_visible(1) is True
        
        # 個別に非表示設定
        settings.mask_visibility[1] = False
        assert settings.is_mask_visible(1) is False
        
        # 全体無効化
        settings.enabled = False
        settings.mask_visibility[2] = True
        assert settings.is_mask_visible(2) is False
    
    def test_color_validation(self):
        """色形式の検証テスト"""
        with pytest.raises(ValueError):
            MaskOverlaySettingsDTO(mask_colors={1: "red"})  # 無効な形式
        
        with pytest.raises(ValueError):
            MaskOverlaySettingsDTO(mask_colors={1: "#FF00"})  # 短すぎる
        
        with pytest.raises(ValueError):
            MaskOverlaySettingsDTO(mask_colors={1: "#GGGGGG"})  # 無効な文字
    
    def test_serialization(self):
        """シリアライズテスト"""
        settings = MaskOverlaySettingsDTO(
            opacity=0.5,
            enabled=False,
            mask_visibility={1: False, 2: True},
            mask_colors={1: "#FFFFFF", 2: "#000000"}
        )
        
        # 辞書に変換
        data = settings.to_dict()
        assert data["opacity"] == 0.5
        assert data["enabled"] is False
        assert data["mask_visibility"][1] is False
        assert data["mask_colors"][2] == "#000000"
        
        # 辞書から復元
        restored = MaskOverlaySettingsDTO.from_dict(data)
        assert restored.opacity == 0.5
        assert restored.enabled is False
        assert restored.mask_visibility[1] is False
        assert restored.mask_colors[2] == "#000000"