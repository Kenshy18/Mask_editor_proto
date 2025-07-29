#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
キャッシュポート定義

キャッシュ機能の抽象化インターフェース
"""
from typing import Protocol, TypeVar, Optional, Dict, Any

T = TypeVar('T')


class ICache(Protocol[T]):
    """汎用キャッシュインターフェース"""
    
    def get(self, key: str) -> Optional[T]:
        """キャッシュから値を取得"""
        ...
    
    def set(self, key: str, value: T) -> None:
        """キャッシュに値を設定"""
        ...
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        ...


class IMaskCache(Protocol):
    """マスクデータ専用キャッシュインターフェース"""
    
    def get_mask(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """マスクをキャッシュから取得"""
        ...
    
    def set_mask(self, frame_index: int, mask_data: Optional[Dict[str, Any]]) -> None:
        """マスクをキャッシュに設定"""
        ...
    
    def prefetch(self, frame_indices: list[int]) -> None:
        """複数フレームを先読み"""
        ...
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        ...