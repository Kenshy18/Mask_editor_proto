#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスク表示制御ポート定義

マスクの表示設定とオーバーレイを制御するインターフェース。
"""
from typing import Protocol, Dict, List, Optional
from domain.dto.mask_dto import MaskDTO, MaskOverlaySettingsDTO


class IMaskDisplayController(Protocol):
    """マスク表示制御ポート（Primary）
    
    マスクの表示設定とオーバーレイを制御。
    """
    
    def get_overlay_settings(self) -> MaskOverlaySettingsDTO:
        """オーバーレイ設定を取得"""
        ...
    
    def update_overlay_settings(self, settings: MaskOverlaySettingsDTO) -> None:
        """オーバーレイ設定を更新"""
        ...
    
    def toggle_mask_visibility(self, mask_id: int, visible: bool) -> None:
        """マスクの表示/非表示を切り替え"""
        ...
    
    def get_mask_color_map(self) -> Dict[int, str]:
        """マスクID別の色マップを取得"""
        ...
    
    def update_mask_color(self, mask_id: int, color: str) -> None:
        """マスクの色を更新"""
        ...
    
    def get_visible_mask_ids(self) -> List[int]:
        """表示中のマスクIDリストを取得"""
        ...