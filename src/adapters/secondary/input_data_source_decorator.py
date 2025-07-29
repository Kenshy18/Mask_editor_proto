#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入力データソースデコレータ

デコレータパターンでキャッシュ機能を追加
"""
import logging
import time
from typing import Dict, Any, List, Optional, Iterator
from functools import lru_cache

from domain.ports.secondary.input_data_ports import IInputDataSource
from domain.ports.secondary.cache_ports import IMaskCache

logger = logging.getLogger(__name__)


class CachedInputDataSourceDecorator:
    """キャッシュ機能付き入力データソースデコレータ
    
    既存のIInputDataSource実装をラップしてキャッシュ機能を追加。
    Hexagonal Architectureに準拠したデコレータパターン実装。
    """
    
    def __init__(self, inner: IInputDataSource, cache: IMaskCache):
        """初期化
        
        Args:
            inner: ラップする入力データソース
            cache: マスクキャッシュサービス
        """
        self._inner = inner
        self._cache = cache
        
        # パフォーマンス統計
        self._cache_hits = 0
        self._cache_misses = 0
    
    # IInputDataSourceの実装
    def initialize(self, config: Dict[str, Any]) -> None:
        """データソースを初期化"""
        self._inner.initialize(config)
    
    def get_video_path(self) -> Any:
        """動画ファイルパスを取得"""
        return self._inner.get_video_path()
    
    def get_video_metadata(self) -> Dict[str, Any]:
        """動画メタデータを取得"""
        return self._inner.get_video_metadata()
    
    def get_detections(self, frame_index: int) -> List[Dict[str, Any]]:
        """指定フレームの検出情報を取得"""
        return self._inner.get_detections(frame_index)
    
    def get_mask(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """指定フレームのマスクを取得（キャッシュ付き）"""
        # キャッシュから取得を試みる
        cached_mask = self._cache.get_mask(frame_index)
        if cached_mask is not None:
            self._cache_hits += 1
            logger.debug(f"Cache hit for frame {frame_index}")
            return cached_mask
        
        # キャッシュミス
        self._cache_misses += 1
        
        # 元の実装から取得
        start_time = time.time()
        mask_data = self._inner.get_mask(frame_index)
        load_time = (time.time() - start_time) * 1000
        
        if load_time > 50:
            logger.warning(f"Slow mask load for frame {frame_index}: {load_time:.1f}ms")
        
        # キャッシュに保存
        self._cache.set_mask(frame_index, mask_data)
        
        # 次のフレームをプリフェッチ
        self._prefetch_next_frames(frame_index)
        
        return mask_data
    
    def get_frame_indices(self) -> List[int]:
        """利用可能なフレームインデックスのリストを取得"""
        return self._inner.get_frame_indices()
    
    def iterate_frames(self, start: int = 0, end: Optional[int] = None) -> Iterator[tuple[int, List[Dict[str, Any]], Optional[Dict[str, Any]]]]:
        """フレームを順次イテレート"""
        return self._inner.iterate_frames(start, end)
    
    def close(self) -> None:
        """リソースを解放"""
        self._cache.clear()
        self._inner.close()
    
    # 追加メソッド
    def _prefetch_next_frames(self, current_frame: int, count: int = 10) -> None:
        """次のフレームをプリフェッチ"""
        next_frames = list(range(current_frame + 1, current_frame + count + 1))
        self._cache.prefetch(next_frames)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0
        
        stats = self._cache.get_stats()
        stats.update({
            "decorator_cache_hits": self._cache_hits,
            "decorator_cache_misses": self._cache_misses,
            "decorator_hit_rate": hit_rate
        })
        
        return stats