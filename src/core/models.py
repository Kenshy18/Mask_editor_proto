#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コアデータモデル定義

要件定義書に基づくMask Editor Prototypeの中核となるデータ構造を定義します。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


# === Enum定義 ===

class ColorSpace(Enum):
    """色空間定義（FR-31要件準拠）"""
    BT709 = "bt709"        # HD標準
    BT2020 = "bt2020"      # UHD/HDR標準
    SRGB = "srgb"          # コンピュータグラフィックス標準
    P3 = "p3"              # デジタルシネマ標準
    ACES = "aces"          # 映画業界標準
    
    @classmethod
    def from_string(cls, value: str) -> ColorSpace:
        """文字列から色空間を取得"""
        value_lower = value.lower()
        for cs in cls:
            if cs.value == value_lower:
                return cs
        # デフォルトはBT.709
        return cls.BT709


class ChromaSubsampling(Enum):
    """クロマサブサンプリング定義（FR-31要件準拠）"""
    YUV420 = "4:2:0"       # 標準的な圧縮
    YUV422 = "4:2:2"       # 放送品質
    YUV444 = "4:4:4"       # 最高品質（色情報の損失なし）
    
    @property
    def chroma_width_divisor(self) -> int:
        """クロマ幅の除数を取得"""
        if self == self.YUV420 or self == self.YUV422:
            return 2
        return 1
    
    @property
    def chroma_height_divisor(self) -> int:
        """クロマ高さの除数を取得"""
        if self == self.YUV420:
            return 2
        return 1


class TransferCharacteristic(Enum):
    """伝達特性（ガンマ/HDR）定義（FR-31要件準拠）"""
    GAMMA22 = "gamma2.2"   # SDR標準
    GAMMA24 = "gamma2.4"   # 映画標準
    HLG = "hlg"            # Hybrid Log-Gamma (放送HDR)
    PQ = "pq"              # Perceptual Quantizer (映画HDR)
    LINEAR = "linear"      # リニア（ガンマなし）


class FieldOrder(Enum):
    """フィールドオーダー定義（FR-37要件準拠）"""
    PROGRESSIVE = "progressive"  # プログレッシブ（非インターレース）
    TFF = "tff"                 # Top Field First
    BFF = "bff"                 # Bottom Field First


class AlertLevel(Enum):
    """アラートレベル定義（FR-19要件準拠）
    AI出力の品質を4段階で分類
    """
    PERFECT = "perfect"          # ほぼ完璧
    NORMAL = "normal"           # 通常再生で確認
    DETAILED = "detailed"       # 詳細確認推奨
    REQUIRED = "required"       # 修正必要
    
    @property
    def priority(self) -> int:
        """優先度を数値で取得（高いほど要注意）"""
        priorities = {
            self.PERFECT: 0,
            self.NORMAL: 1,
            self.DETAILED: 2,
            self.REQUIRED: 3
        }
        return priorities[self]
    
    @property
    def color(self) -> str:
        """UI表示用の色を取得"""
        colors = {
            self.PERFECT: "#00FF00",    # 緑
            self.NORMAL: "#FFFF00",     # 黄
            self.DETAILED: "#FFA500",   # オレンジ
            self.REQUIRED: "#FF0000"    # 赤
        }
        return colors[self]


# === データクラス定義 ===

@dataclass
class Frame:
    """フレームデータクラス（要件定義書セクション12.1準拠）
    
    動画の1フレームを表現し、NLE品質要件（NFR-14）を満たすための
    すべてのメタデータを保持します。
    """
    data: np.ndarray                    # HxWxC (uint8/uint16/float32)
    pts: int                            # Presentation timestamp (microseconds)
    dts: Optional[int] = None           # Decoding timestamp (microseconds)
    timecode: str = ""                  # SMPTE timecode (e.g., "01:23:45:12")
    colorspace: ColorSpace = ColorSpace.BT709
    bit_depth: int = 8                  # 8, 10, 12, 16 bit
    subsampling: ChromaSubsampling = ChromaSubsampling.YUV420
    transfer: TransferCharacteristic = TransferCharacteristic.GAMMA22
    field_order: FieldOrder = FieldOrder.PROGRESSIVE
    hdr_metadata: Optional[Dict[str, Any]] = None  # MaxCLL, MaxFALL等
    
    # 追加のメタデータ
    frame_number: int = 0               # 0-basedフレーム番号
    duration: int = 0                   # フレームの表示時間（microseconds）
    is_keyframe: bool = False           # キーフレームかどうか
    
    def __post_init__(self):
        """初期化後の検証"""
        if self.data.ndim not in [2, 3]:
            raise ValueError(f"Frame data must be 2D or 3D, got {self.data.ndim}D")
        
        if self.bit_depth not in [8, 10, 12, 16]:
            raise ValueError(f"Unsupported bit depth: {self.bit_depth}")
        
        # PTS/DTSの検証
        if self.dts is not None and self.dts > self.pts:
            raise ValueError("DTS cannot be greater than PTS")
    
    @property
    def shape(self) -> Tuple[int, int, int]:
        """フレームの形状を取得 (H, W, C)"""
        if self.data.ndim == 2:
            return (*self.data.shape, 1)
        return self.data.shape
    
    @property
    def width(self) -> int:
        """フレーム幅"""
        return self.shape[1]
    
    @property
    def height(self) -> int:
        """フレーム高さ"""
        return self.shape[0]
    
    @property
    def channels(self) -> int:
        """チャンネル数"""
        return self.shape[2]
    
    @property
    def pts_seconds(self) -> float:
        """PTSを秒単位で取得"""
        return self.pts / 1_000_000
    
    def to_dict(self) -> Dict[str, Any]:
        """シリアライズ用辞書に変換"""
        return {
            "pts": self.pts,
            "dts": self.dts,
            "timecode": self.timecode,
            "colorspace": self.colorspace.value,
            "bit_depth": self.bit_depth,
            "subsampling": self.subsampling.value,
            "transfer": self.transfer.value,
            "field_order": self.field_order.value,
            "hdr_metadata": self.hdr_metadata,
            "frame_number": self.frame_number,
            "duration": self.duration,
            "is_keyframe": self.is_keyframe,
            "shape": self.shape
        }
    
    def calculate_hash(self) -> str:
        """フレームデータのハッシュを計算（品質検証用）"""
        return hashlib.md5(self.data.tobytes()).hexdigest()


@dataclass
class Mask:
    """マスクデータクラス（要件定義書IN-2準拠）
    
    AI生成または手動編集されたマスクデータを保持。
    NPY/PNG形式での入出力をサポート。
    """
    data: np.ndarray          # HxW (bool or uint8)
    id: int                   # オブジェクトID（時系列追跡用）
    class_name: str           # クラス名（例: "genital"）
    confidence: float         # 信頼度 (0.0-1.0)
    frame_index: int          # フレームインデックス（0-based）
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # 追加のメタデータ
    source: str = "ai"        # "ai" or "manual"
    parent_id: Optional[int] = None  # 分割元のID（ID分割時）
    
    def __post_init__(self):
        """初期化後の検証"""
        if self.data.ndim != 2:
            raise ValueError(f"Mask data must be 2D, got {self.data.ndim}D")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
        
        # データ型の確認
        if self.data.dtype not in [np.bool_, np.uint8]:
            self.data = self.data.astype(np.uint8)
    
    @property
    def shape(self) -> Tuple[int, int]:
        """マスクの形状を取得 (H, W)"""
        return self.data.shape
    
    @property
    def area(self) -> int:
        """マスク領域のピクセル数"""
        return np.sum(self.data > 0)
    
    @property
    def bbox(self) -> Optional[Tuple[int, int, int, int]]:
        """マスクのバウンディングボックスを計算 (x1, y1, x2, y2)"""
        if self.area == 0:
            return None
        
        rows, cols = np.where(self.data > 0)
        return (int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max()))
    
    def to_npy(self, filepath: Union[str, Path]) -> None:
        """NPY形式で保存"""
        np.save(filepath, self.data)
    
    def to_png(self, filepath: Union[str, Path]) -> None:
        """PNG形式で保存"""
        import cv2
        # bool型の場合は255倍、uint8の場合も値が0-1の範囲なら255倍
        if self.data.dtype == np.bool_:
            img_data = self.data.astype(np.uint8) * 255
        else:
            # uint8でも値が0-1の範囲なら255倍する
            if self.data.max() <= 1:
                img_data = self.data * 255
            else:
                img_data = self.data
        cv2.imwrite(str(filepath), img_data)
    
    @classmethod
    def from_npy(cls, filepath: Union[str, Path], **kwargs) -> Mask:
        """NPYファイルから読み込み"""
        data = np.load(filepath)
        return cls(data=data, **kwargs)
    
    @classmethod
    def from_png(cls, filepath: Union[str, Path], **kwargs) -> Mask:
        """PNGファイルから読み込み"""
        import cv2
        data = cv2.imread(str(filepath), cv2.IMREAD_GRAYSCALE)
        if data is None:
            raise ValueError(f"Failed to load image: {filepath}")
        # 2値化（閾値128）
        data = (data > 128).astype(np.uint8)
        return cls(data=data, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """シリアライズ用辞書に変換"""
        return {
            "id": self.id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "frame_index": self.frame_index,
            "attributes": self.attributes,
            "source": self.source,
            "parent_id": self.parent_id,
            "shape": self.shape,
            "area": int(self.area),  # numpy.int64をintに変換
            "bbox": self.bbox
        }


@dataclass
class BoundingBox:
    """バウンディングボックスクラス（要件定義書IN-4準拠）
    
    オブジェクト検出結果を表現。x,y,w,h形式を基本とし、
    他の形式への変換もサポート。
    """
    x: float              # 左上X座標
    y: float              # 左上Y座標
    width: float          # 幅
    height: float         # 高さ
    id: int               # オブジェクトID
    score: float          # 検出スコア (0.0-1.0)
    class_name: str       # クラス名
    frame_index: int      # フレームインデックス
    
    # 追加のメタデータ
    track_id: Optional[int] = None      # トラッキングID
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の検証"""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Width and height must be positive")
        
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0 and 1, got {self.score}")
    
    @property
    def x2(self) -> float:
        """右下X座標"""
        return self.x + self.width
    
    @property
    def y2(self) -> float:
        """右下Y座標"""
        return self.y + self.height
    
    @property
    def center_x(self) -> float:
        """中心X座標"""
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        """中心Y座標"""
        return self.y + self.height / 2
    
    @property
    def area(self) -> float:
        """面積"""
        return self.width * self.height
    
    def to_xyxy(self) -> Tuple[float, float, float, float]:
        """(x1, y1, x2, y2)形式に変換"""
        return (self.x, self.y, self.x2, self.y2)
    
    def to_xywh(self) -> Tuple[float, float, float, float]:
        """(x, y, w, h)形式で取得"""
        return (self.x, self.y, self.width, self.height)
    
    def to_cxcywh(self) -> Tuple[float, float, float, float]:
        """(center_x, center_y, w, h)形式に変換"""
        return (self.center_x, self.center_y, self.width, self.height)
    
    @classmethod
    def from_xyxy(cls, x1: float, y1: float, x2: float, y2: float, **kwargs) -> BoundingBox:
        """(x1, y1, x2, y2)形式から作成"""
        return cls(x=x1, y=y1, width=x2-x1, height=y2-y1, **kwargs)
    
    def iou(self, other: BoundingBox) -> float:
        """IoU (Intersection over Union)を計算"""
        # 交差領域
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON形式でのシリアライズ"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "id": self.id,
            "score": self.score,
            "class_name": self.class_name,
            "frame_index": self.frame_index,
            "track_id": self.track_id,
            "attributes": self.attributes
        }


@dataclass
class AlertTag:
    """アラートタグクラス（FR-19要件準拠）
    
    AI出力の品質を4段階で評価し、確認の優先度を示す。
    """
    level: AlertLevel                   # アラートレベル（4段階）
    reason: str                         # アラートの理由
    frame_range: Tuple[int, int]        # 対象フレーム範囲 (start, end)
    confidence: float                   # アラートの確信度 (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 追加の情報
    object_ids: List[int] = field(default_factory=list)  # 関連するオブジェクトID
    created_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False              # 解決済みかどうか
    
    def __post_init__(self):
        """初期化後の検証"""
        if self.frame_range[0] > self.frame_range[1]:
            raise ValueError("Invalid frame range: start > end")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
    
    @property
    def duration_frames(self) -> int:
        """影響するフレーム数"""
        return self.frame_range[1] - self.frame_range[0] + 1
    
    def contains_frame(self, frame_index: int) -> bool:
        """指定フレームが範囲内かチェック"""
        return self.frame_range[0] <= frame_index <= self.frame_range[1]
    
    def to_dict(self) -> Dict[str, Any]:
        """シリアライズ用辞書に変換"""
        return {
            "level": self.level.value,
            "reason": self.reason,
            "frame_range": self.frame_range,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "object_ids": self.object_ids,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved
        }


@dataclass 
class OpticalFlow:
    """オプティカルフロークラス（要件定義書IN-5準拠）
    
    隣接フレーム間の画素移動ベクトルを保持。
    """
    flow: np.ndarray                    # HxWx2 float32 (dx, dy)
    frame_pair: Tuple[int, int]         # (from_frame, to_frame)
    method: str = "liteflownet"         # 計算手法
    confidence: Optional[np.ndarray] = None  # HxW float32 (信頼度マップ)
    
    def __post_init__(self):
        """初期化後の検証"""
        if self.flow.ndim != 3 or self.flow.shape[2] != 2:
            raise ValueError(f"Flow must be HxWx2, got shape {self.flow.shape}")
        
        if self.flow.dtype != np.float32:
            self.flow = self.flow.astype(np.float32)
        
        if self.confidence is not None:
            if self.confidence.shape[:2] != self.flow.shape[:2]:
                raise ValueError("Confidence map shape mismatch")
    
    @property
    def shape(self) -> Tuple[int, int]:
        """フローの形状を取得 (H, W)"""
        return self.flow.shape[:2]
    
    @property
    def magnitude(self) -> np.ndarray:
        """フローの大きさを計算"""
        return np.sqrt(self.flow[..., 0]**2 + self.flow[..., 1]**2)
    
    @property
    def angle(self) -> np.ndarray:
        """フローの角度を計算（ラジアン）"""
        return np.arctan2(self.flow[..., 1], self.flow[..., 0])
    
    def to_npz(self, filepath: Union[str, Path]) -> None:
        """NPZ形式で保存"""
        save_dict = {
            "flow": self.flow,
            "frame_pair": self.frame_pair,
            "method": self.method
        }
        if self.confidence is not None:
            save_dict["confidence"] = self.confidence
        np.savez_compressed(filepath, **save_dict)
    
    @classmethod
    def from_npz(cls, filepath: Union[str, Path]) -> OpticalFlow:
        """NPZファイルから読み込み"""
        data = np.load(filepath)
        return cls(
            flow=data["flow"],
            frame_pair=tuple(data["frame_pair"]),
            method=str(data["method"]),
            confidence=data.get("confidence")
        )


# === プロジェクト関連クラス ===

@dataclass
class EditHistory:
    """編集履歴エントリ"""
    timestamp: datetime
    action: str                        # "add_mask", "delete_mask", "modify_mask", etc.
    target_type: str                   # "mask", "effect", "setting", etc.
    target_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """シリアライズ用辞書に変換"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "description": self.description
        }


@dataclass
class Timeline:
    """タイムライン情報"""
    total_frames: int
    fps: float
    duration_seconds: float
    in_point: int = 0                  # 開始フレーム
    out_point: Optional[int] = None    # 終了フレーム（Noneの場合はtotal_frames-1）
    markers: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """初期化後の処理"""
        if self.out_point is None:
            self.out_point = self.total_frames - 1
    
    @property
    def working_duration_frames(self) -> int:
        """作業範囲のフレーム数"""
        return self.out_point - self.in_point + 1
    
    @property
    def working_duration_seconds(self) -> float:
        """作業範囲の秒数"""
        return self.working_duration_frames / self.fps
    
    def frame_to_timecode(self, frame_index: int, drop_frame: bool = False) -> str:
        """フレーム番号をタイムコードに変換"""
        if drop_frame and abs(self.fps - 29.97) < 0.01:
            # Drop Frame タイムコード計算（NTSC）
            # 実装は複雑なため、ここでは簡略版
            total_frames = frame_index
            fps_int = 30
            
            # 10分ごとのドロップフレーム数を計算
            ten_minute_frames = 17982  # 10分のフレーム数（ドロップフレーム考慮）
            ten_minutes = total_frames // ten_minute_frames
            remaining_frames = total_frames % ten_minute_frames
            
            # 簡略計算（完全な実装には追加のロジックが必要）
            hours = ten_minutes // 6
            minutes = (ten_minutes % 6) * 10 + remaining_frames // (fps_int * 60)
            seconds = (remaining_frames % (fps_int * 60)) // fps_int
            frames = remaining_frames % fps_int
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d};{frames:02d}"
        else:
            # Non-Drop Frame タイムコード
            fps_int = round(self.fps)
            hours = frame_index // (fps_int * 3600)
            minutes = (frame_index % (fps_int * 3600)) // (fps_int * 60)
            seconds = (frame_index % (fps_int * 60)) // fps_int
            frames = frame_index % fps_int
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """シリアライズ用辞書に変換"""
        return asdict(self)


@dataclass
class Project:
    """プロジェクトクラス（FR-2要件準拠）
    
    .mosaicproj形式での保存・読み込みをサポート。
    すべての編集状態、履歴、設定を保持。
    """
    version: str = "1.0.0"              # プロジェクトファイルバージョン
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    # プロジェクトの基本情報
    name: str = "Untitled Project"
    description: str = ""
    source_video_path: str = ""
    
    # タイムライン情報
    timeline: Optional[Timeline] = None
    
    # 設定
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # 編集履歴
    history: List[EditHistory] = field(default_factory=list)
    history_index: int = -1             # 現在の履歴位置（Undo/Redo用）
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # リソース管理
    mask_directory: str = ""
    output_directory: str = ""
    temp_directory: str = ""
    
    def add_history(self, history_entry: EditHistory) -> None:
        """編集履歴を追加"""
        # 現在位置以降の履歴を削除（Redo履歴をクリア）
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        
        self.history.append(history_entry)
        self.history_index = len(self.history) - 1
        self.modified_at = datetime.now()
    
    def undo(self) -> Optional[EditHistory]:
        """Undo操作"""
        if self.can_undo():
            self.history_index -= 1
            return self.history[self.history_index + 1]
        return None
    
    def redo(self) -> Optional[EditHistory]:
        """Redo操作"""
        if self.can_redo():
            self.history_index += 1
            return self.history[self.history_index]
        return None
    
    def can_undo(self) -> bool:
        """Undo可能かチェック"""
        return self.history_index >= 0
    
    def can_redo(self) -> bool:
        """Redo可能かチェック"""
        return self.history_index < len(self.history) - 1
    
    def to_dict(self) -> Dict[str, Any]:
        """シリアライズ用辞書に変換"""
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "name": self.name,
            "description": self.description,
            "source_video_path": self.source_video_path,
            "timeline": self.timeline.to_dict() if self.timeline else None,
            "settings": self.settings,
            "history": [h.to_dict() for h in self.history],
            "history_index": self.history_index,
            "metadata": self.metadata,
            "mask_directory": self.mask_directory,
            "output_directory": self.output_directory,
            "temp_directory": self.temp_directory
        }
    
    def save(self, filepath: Union[str, Path]) -> None:
        """プロジェクトを.mosaicproj形式で保存"""
        import zipfile
        import tempfile
        
        filepath = Path(filepath)
        if not filepath.suffix:
            filepath = filepath.with_suffix(".mosaicproj")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # プロジェクトJSONを保存
            project_json = tmpdir_path / "project.json"
            with open(project_json, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
            # ZIPファイルとして保存
            with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(project_json, "project.json")
                
                # 将来的には追加のアセット（カスタムマスク等）も含める
    
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> Project:
        """プロジェクトを.mosaicproj形式から読み込み"""
        import zipfile
        
        filepath = Path(filepath)
        
        with zipfile.ZipFile(filepath, "r") as zf:
            with zf.open("project.json") as f:
                data = json.load(f)
        
        # バージョンチェック
        file_version = data.get("version", "0.0.0")
        if file_version.split(".")[0] != cls.version.split(".")[0]:
            raise ValueError(
                f"Incompatible project version: {file_version} "
                f"(current: {cls.version})"
            )
        
        # Projectインスタンスを再構築
        project = cls(
            version=data["version"],
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
            name=data["name"],
            description=data["description"],
            source_video_path=data["source_video_path"],
            settings=data["settings"],
            metadata=data["metadata"],
            mask_directory=data["mask_directory"],
            output_directory=data["output_directory"],
            temp_directory=data["temp_directory"],
            history_index=data["history_index"]
        )
        
        # タイムライン
        if data["timeline"]:
            project.timeline = Timeline(**data["timeline"])
        
        # 履歴
        for h_data in data["history"]:
            history = EditHistory(
                timestamp=datetime.fromisoformat(h_data["timestamp"]),
                action=h_data["action"],
                target_type=h_data["target_type"],
                target_id=h_data["target_id"],
                parameters=h_data["parameters"],
                description=h_data["description"]
            )
            project.history.append(history)
        
        return project


# === ヘルパー関数 ===

def create_test_frame(width: int = 1920, height: int = 1080) -> Frame:
    """テスト用のフレームを作成"""
    data = np.zeros((height, width, 3), dtype=np.uint8)
    return Frame(
        data=data,
        pts=0,
        timecode="00:00:00:00",
        frame_number=0
    )


def create_test_mask(width: int = 1920, height: int = 1080) -> Mask:
    """テスト用のマスクを作成"""
    data = np.zeros((height, width), dtype=np.uint8)
    # 中央に矩形を描画
    h_start, h_end = height // 4, 3 * height // 4
    w_start, w_end = width // 4, 3 * width // 4
    data[h_start:h_end, w_start:w_end] = 1
    
    return Mask(
        data=data,
        id=1,
        class_name="test",
        confidence=0.95,
        frame_index=0
    )