#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入力データソースファクトリー

入力データソースの生成を管理。
"""
from pathlib import Path
from typing import Dict, Any

from domain.ports.secondary.input_data_ports import IInputDataSource
from adapters.secondary.local_file_input_adapter import LocalFileInputAdapter


class InputDataSourceFactory:
    """入力データソースファクトリー
    
    設定に基づいて適切な入力データソースを生成。
    """
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> IInputDataSource:
        """設定から入力データソースを生成
        
        Args:
            config: 設定辞書
            
        Returns:
            入力データソースインスタンス
        """
        source_type = config.get("type", "local_file")
        
        if source_type == "local_file":
            adapter = LocalFileInputAdapter()
            if "base_path" in config:
                adapter.set_base_path(config["base_path"])
            # アダプターを初期化
            adapter.initialize(config)
            return adapter
        else:
            raise ValueError(f"Unknown input data source type: {source_type}")
    
    @staticmethod
    def create_local_file_source(base_path: Path) -> IInputDataSource:
        """ローカルファイル入力データソースを生成
        
        Args:
            base_path: ベースディレクトリパス
            
        Returns:
            LocalFileInputAdapterインスタンス
        """
        adapter = LocalFileInputAdapter()
        adapter.set_base_path(str(base_path))
        
        # アダプターを初期化（デフォルト設定を使用）
        config = {
            "base_path": str(base_path),
            # デフォルトのファイル名を使用
            # これらは LocalFileInputAdapter.initialize() のデフォルト値と同じ
        }
        adapter.initialize(config)
        
        return adapter