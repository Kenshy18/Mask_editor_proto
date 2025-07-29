#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenCVブラシエンジンアダプター

OpenCVを使用したブラシ描画エンジンの実装。
"""
import logging
from typing import List, Tuple, Optional
import numpy as np
import cv2
from datetime import datetime

from domain.dto.brush_dto import (
    BrushConfigDTO, BrushStrokeDTO, BrushPointDTO, 
    BrushModeDTO, BrushShapeDTO
)
from domain.ports.secondary.brush_ports import IBrushEngine, IBrushOptimizer

logger = logging.getLogger(__name__)


class OpenCVBrushOptimizer:
    """OpenCVブラシ最適化実装"""
    
    def smooth_points(self, points: List[Tuple[int, int]], window_size: int = 5) -> List[Tuple[int, int]]:
        """
        ポイント列をスムージング
        
        移動平均を使用してポイントを滑らかにする。
        """
        if len(points) < window_size:
            return points
        
        # numpy配列に変換
        points_array = np.array(points, dtype=np.float32)
        
        # 移動平均でスムージング
        kernel = np.ones(window_size) / window_size
        smoothed_x = np.convolve(points_array[:, 0], kernel, mode='same')
        smoothed_y = np.convolve(points_array[:, 1], kernel, mode='same')
        
        # 整数座標に戻す
        smoothed_points = [
            (int(x), int(y)) 
            for x, y in zip(smoothed_x, smoothed_y)
        ]
        
        return smoothed_points
    
    def interpolate_points(self, p1: Tuple[int, int], p2: Tuple[int, int], 
                          density: float = 1.0) -> List[Tuple[int, int]]:
        """
        2点間を補間
        
        Bresenhamアルゴリズムを使用して線形補間。
        """
        x1, y1 = p1
        x2, y2 = p2
        
        # 距離計算
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        distance = np.sqrt(dx**2 + dy**2)
        
        if distance < 1:
            return [p1]
        
        # 補間点数を決定
        num_points = max(2, int(distance * density))
        
        # 線形補間
        x_values = np.linspace(x1, x2, num_points)
        y_values = np.linspace(y1, y2, num_points)
        
        return [(int(x), int(y)) for x, y in zip(x_values, y_values)]
    
    def optimize_stroke(self, stroke: BrushStrokeDTO) -> BrushStrokeDTO:
        """
        ストロークを最適化
        
        重複点の削除と適切な補間を行う。
        """
        if len(stroke.points) < 2:
            return stroke
        
        # ポイントを座標リストに変換
        points = [(p.x, p.y) for p in stroke.points]
        
        # 重複削除
        unique_points = []
        prev_point = None
        for point in points:
            if prev_point is None or point != prev_point:
                unique_points.append(point)
                prev_point = point
        
        # 補間
        interpolated_points = []
        for i in range(len(unique_points) - 1):
            segment = self.interpolate_points(
                unique_points[i], 
                unique_points[i + 1],
                density=1.0 / stroke.config.spacing
            )
            interpolated_points.extend(segment[:-1])  # 最後の点は次のセグメントで追加
        interpolated_points.append(unique_points[-1])  # 最後の点を追加
        
        # 新しいポイントリストを作成
        new_points = []
        for i, (x, y) in enumerate(interpolated_points):
            # 元のポイントから最も近いものの筆圧を使用
            min_dist = float('inf')
            pressure = 1.0
            for orig_point in stroke.points:
                dist = np.sqrt((orig_point.x - x)**2 + (orig_point.y - y)**2)
                if dist < min_dist:
                    min_dist = dist
                    pressure = orig_point.pressure
            
            new_points.append(BrushPointDTO(
                x=x, y=y, 
                pressure=pressure,
                timestamp=datetime.now().timestamp()
            ))
        
        # 新しいストロークを作成
        from dataclasses import replace
        return replace(stroke, points=new_points)


class OpenCVBrushEngine:
    """OpenCVブラシエンジン実装"""
    
    def __init__(self):
        # デフォルトではERASEモードを使用（new_id/target_idが不要）
        self._config = BrushConfigDTO(mode=BrushModeDTO.ERASE)
        self._current_stroke_points: List[BrushPointDTO] = []
        self._optimizer = OpenCVBrushOptimizer()
        self._stroke_start_time = 0.0
        
    def set_brush_config(self, config: BrushConfigDTO) -> None:
        """ブラシ設定を更新"""
        self._config = config
        logger.debug(f"Brush config updated: size={config.size}, mode={config.mode}")
    
    def begin_stroke(self, x: int, y: int, pressure: float = 1.0) -> None:
        """ストローク開始"""
        self._current_stroke_points = []
        self._stroke_start_time = datetime.now().timestamp()
        self._current_stroke_points.append(
            BrushPointDTO(
                x=x, y=y, 
                pressure=pressure,
                timestamp=datetime.now().timestamp()
            )
        )
        logger.debug(f"Stroke started at ({x}, {y})")
    
    def add_stroke_point(self, x: int, y: int, pressure: float = 1.0) -> None:
        """ストロークポイント追加"""
        if not self._current_stroke_points:
            self.begin_stroke(x, y, pressure)
            return
        
        # 前のポイントとの距離をチェック
        last_point = self._current_stroke_points[-1]
        distance = np.sqrt((x - last_point.x)**2 + (y - last_point.y)**2)
        
        # 最小間隔より大きい場合のみ追加
        min_distance = self._config.size * self._config.spacing
        if distance >= min_distance:
            self._current_stroke_points.append(
                BrushPointDTO(
                    x=x, y=y,
                    pressure=pressure,
                    timestamp=datetime.now().timestamp()
                )
            )
    
    def end_stroke(self) -> BrushStrokeDTO:
        """ストローク終了"""
        if not self._current_stroke_points:
            # 空のストロークの場合、ダミーポイントを追加
            self._current_stroke_points = [BrushPointDTO(x=0, y=0)]
        
        stroke = BrushStrokeDTO(
            points=self._current_stroke_points,
            config=self._config
        )
        
        # スムージングが有効な場合は最適化
        if self._config.smoothing > 0:
            stroke = self._optimizer.optimize_stroke(stroke)
        
        logger.debug(f"Stroke ended with {len(stroke.points)} points")
        self._current_stroke_points = []
        
        return stroke
    
    def apply_stroke(self, mask: np.ndarray, stroke: BrushStrokeDTO) -> np.ndarray:
        """
        マスクにストロークを適用
        
        Args:
            mask: 対象マスク（uint8）
            stroke: ストローク情報
            
        Returns:
            更新されたマスク
        """
        # マスクのコピーを作成
        result = mask.copy()
        config = stroke.config
        
        # 描画する値を決定
        if config.mode == BrushModeDTO.ERASE:
            draw_value = 0
        elif config.mode == BrushModeDTO.ADD_NEW_ID:
            draw_value = config.new_id or 255
        else:  # ADD_TO_EXISTING
            draw_value = config.target_id or 255
        
        # 各ポイント間を補間して描画
        points = stroke.points
        for i in range(len(points)):
            point = points[i]
            
            # ブラシサイズを筆圧で調整
            size = int(config.size * point.pressure) if config.pressure_sensitivity else config.size
            
            # ブラシ形状に応じて描画
            if config.shape == BrushShapeDTO.CIRCLE:
                # 円形ブラシ
                if config.hardness >= 1.0:
                    # ハードブラシ
                    cv2.circle(result, (point.x, point.y), size // 2, 
                              int(draw_value), -1, cv2.LINE_AA)
                else:
                    # ソフトブラシ（グラデーション付き）
                    self._draw_soft_circle(result, point.x, point.y, size, 
                                         draw_value, config.hardness, config.opacity)
            
            elif config.shape == BrushShapeDTO.SQUARE:
                # 四角形ブラシ
                half_size = size // 2
                cv2.rectangle(result, 
                            (point.x - half_size, point.y - half_size),
                            (point.x + half_size, point.y + half_size),
                            int(draw_value), -1)
            
            # 次のポイントとの間を補間
            if i < len(points) - 1:
                next_point = points[i + 1]
                # 補間点を生成
                interp_points = self._optimizer.interpolate_points(
                    (point.x, point.y),
                    (next_point.x, next_point.y),
                    density=2.0  # 高密度で補間
                )
                
                # 補間点を描画
                for j, (ix, iy) in enumerate(interp_points[1:-1]):
                    # 筆圧を線形補間
                    t = (j + 1) / len(interp_points)
                    interp_pressure = point.pressure * (1 - t) + next_point.pressure * t
                    interp_size = int(config.size * interp_pressure) if config.pressure_sensitivity else config.size
                    
                    if config.shape == BrushShapeDTO.CIRCLE:
                        if config.hardness >= 1.0:
                            cv2.circle(result, (ix, iy), interp_size // 2, 
                                     int(draw_value), -1, cv2.LINE_AA)
                        else:
                            self._draw_soft_circle(result, ix, iy, interp_size,
                                                 draw_value, config.hardness, config.opacity)
        
        return result
    
    def _draw_soft_circle(self, image: np.ndarray, cx: int, cy: int, 
                         size: int, value: int, hardness: float, opacity: float) -> None:
        """
        ソフトエッジの円を描画
        
        Args:
            image: 描画対象画像
            cx, cy: 中心座標
            size: 直径
            value: 描画値
            hardness: 硬さ（0.0-1.0）
            opacity: 不透明度（0.0-1.0）
        """
        radius = size // 2
        if radius < 1:
            return
        
        # 描画範囲を計算
        x1 = max(0, cx - radius)
        y1 = max(0, cy - radius)
        x2 = min(image.shape[1], cx + radius + 1)
        y2 = min(image.shape[0], cy + radius + 1)
        
        if x2 <= x1 or y2 <= y1:
            return
        
        # メッシュグリッドを作成
        y, x = np.ogrid[y1:y2, x1:x2]
        
        # 中心からの距離を計算
        dist = np.sqrt((x - cx)**2 + (y - cy)**2)
        
        # ソフトエッジのマスクを作成
        hard_radius = radius * hardness
        soft_radius = radius * (1 - hardness)
        
        mask = np.zeros_like(dist)
        mask[dist <= hard_radius] = 1.0
        
        # ソフトエッジ部分
        soft_area = (dist > hard_radius) & (dist <= radius)
        if soft_radius > 0:
            mask[soft_area] = 1.0 - (dist[soft_area] - hard_radius) / soft_radius
        
        # 不透明度を適用
        mask *= opacity
        
        # 既存の値とブレンド
        roi = image[y1:y2, x1:x2]
        if value == 0:  # 消しゴムモード
            image[y1:y2, x1:x2] = roi * (1 - mask)
        else:
            image[y1:y2, x1:x2] = roi * (1 - mask) + value * mask
    
    def preview_stroke(self, width: int, height: int, stroke: BrushStrokeDTO) -> np.ndarray:
        """
        ストロークのプレビュー生成
        
        Args:
            width: キャンバス幅
            height: キャンバス高さ
            stroke: ストローク情報
            
        Returns:
            プレビュー画像（RGBA）
        """
        # 透明な画像を作成
        preview = np.zeros((height, width, 4), dtype=np.uint8)
        
        # アルファチャンネルにストロークを描画
        alpha = np.zeros((height, width), dtype=np.uint8)
        alpha = self.apply_stroke(alpha, stroke)
        
        # 色を設定（赤色のプレビュー）
        preview[:, :, 0] = 255  # R
        preview[:, :, 1] = 0    # G
        preview[:, :, 2] = 0    # B
        preview[:, :, 3] = alpha  # A
        
        return preview