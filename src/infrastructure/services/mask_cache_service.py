#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マスクキャッシュサービス

マスクデータのキャッシュを管理する独立したサービス
"""
import logging
import threading
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, Future

from domain.ports.secondary.cache_ports import IMaskCache

logger = logging.getLogger(__name__)


class MaskCacheService(IMaskCache):
    """マスクキャッシュサービスの実装
    
    LRUキャッシュとプリフェッチ機能を提供。
    インフラストラクチャ層の独立したサービスとして実装。
    """
    
    def __init__(self, max_size: int = 100, prefetch_workers: int = 2):
        """初期化
        
        Args:
            max_size: キャッシュの最大サイズ
            prefetch_workers: プリフェッチワーカー数
        """
        self._max_size = max_size
        self._cache = OrderedDict()  # LRU実装用
        self._lock = threading.Lock()
        
        # プリフェッチ用
        self._executor = ThreadPoolExecutor(
            max_workers=prefetch_workers,
            thread_name_prefix="MaskPrefetch"
        )
        self._prefetch_futures: Dict[int, Future] = {}
        
        # 統計
        self._hits = 0
        self._misses = 0
        
        # プリフェッチコールバック（実際の読み込み処理は外部から注入）
        self._load_callback = None
    
    def set_load_callback(self, callback) -> None:
        """マスク読み込みコールバックを設定
        
        Args:
            callback: frame_index -> mask_data の関数
        """
        self._load_callback = callback
    
    def get_mask(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """マスクをキャッシュから取得"""
        with self._lock:
            if frame_index in self._cache:
                # LRU: 最近使用したものを末尾に移動
                self._cache.move_to_end(frame_index)
                self._hits += 1
                return self._cache[frame_index]
            
            self._misses += 1
            return None
    
    def set_mask(self, frame_index: int, mask_data: Optional[Dict[str, Any]]) -> None:
        """マスクをキャッシュに設定"""
        with self._lock:
            # 既存のエントリがある場合は末尾に移動
            if frame_index in self._cache:
                self._cache.move_to_end(frame_index)
            else:
                # 新規追加
                self._cache[frame_index] = mask_data
                
                # サイズ制限チェック
                if len(self._cache) > self._max_size:
                    # 最も古いものを削除
                    self._cache.popitem(last=False)
    
    def prefetch(self, frame_indices: List[int]) -> None:
        """複数フレームを先読み"""
        if not self._load_callback:
            return
        
        # 既にキャッシュにあるものは除外
        with self._lock:
            indices_to_load = [
                idx for idx in frame_indices 
                if idx not in self._cache and idx not in self._prefetch_futures
            ]
        
        # 非同期で読み込み開始
        for idx in indices_to_load:
            future = self._executor.submit(self._load_mask_async, idx)
            self._prefetch_futures[idx] = future
    
    def _load_mask_async(self, frame_index: int) -> None:
        """非同期でマスクを読み込み"""
        try:
            # コールバックを使用してマスクを読み込み
            mask_data = self._load_callback(frame_index)
            
            # キャッシュに保存
            if mask_data is not None:
                self.set_mask(frame_index, mask_data)
                
        except Exception as e:
            logger.error(f"Prefetch error for frame {frame_index}: {e}")
        finally:
            # フューチャーを削除
            self._prefetch_futures.pop(frame_index, None)
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
        
        # プリフェッチをキャンセル
        for future in self._prefetch_futures.values():
            future.cancel()
        self._prefetch_futures.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            
            return {
                "cache_size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "prefetch_queue": len(self._prefetch_futures)
            }
    
    def __del__(self):
        """デストラクタ"""
        # スレッドプールをシャットダウン
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)