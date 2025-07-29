#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIアニメーション

スムーズなアニメーションとトランジション効果を提供。
"""
from __future__ import annotations

import logging
from typing import Optional, Callable, Any

from PyQt6.QtCore import (
    QPropertyAnimation, QSequentialAnimationGroup, QParallelAnimationGroup,
    QEasingCurve, QRect, QPoint, QSize, pyqtSignal, QObject,
    QAbstractAnimation, QTimer
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect

logger = logging.getLogger(__name__)


class AnimationManager(QObject):
    """アニメーションマネージャー
    
    アプリケーション全体のアニメーションを管理。
    """
    
    def __init__(self):
        super().__init__()
        self._animations = []
        self._default_duration = 300
        self._default_easing = QEasingCurve.Type.InOutCubic
    
    def fade_in(self, widget: QWidget, duration: Optional[int] = None, 
                callback: Optional[Callable] = None) -> QPropertyAnimation:
        """フェードイン
        
        Args:
            widget: 対象ウィジェット
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            
        Returns:
            アニメーションオブジェクト
        """
        # グラフィックエフェクトを設定
        effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(effect)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration or self._default_duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(self._default_easing)
        
        if callback:
            animation.finished.connect(callback)
        
        # ウィジェットを表示してからアニメーション開始
        widget.show()
        animation.start()
        
        self._animations.append(animation)
        return animation
    
    def fade_out(self, widget: QWidget, duration: Optional[int] = None,
                 callback: Optional[Callable] = None, hide_on_finish: bool = True) -> QPropertyAnimation:
        """フェードアウト
        
        Args:
            widget: 対象ウィジェット
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            hide_on_finish: 完了時に非表示にするか
            
        Returns:
            アニメーションオブジェクト
        """
        # グラフィックエフェクトを設定
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect()
            widget.setGraphicsEffect(effect)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration or self._default_duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(self._default_easing)
        
        def on_finished():
            if hide_on_finish:
                widget.hide()
            if callback:
                callback()
        
        animation.finished.connect(on_finished)
        animation.start()
        
        self._animations.append(animation)
        return animation
    
    def slide_in(self, widget: QWidget, direction: str = "left", 
                 duration: Optional[int] = None, callback: Optional[Callable] = None) -> QPropertyAnimation:
        """スライドイン
        
        Args:
            widget: 対象ウィジェット
            direction: 方向（"left", "right", "top", "bottom"）
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            
        Returns:
            アニメーションオブジェクト
        """
        # 開始位置を計算
        parent = widget.parent()
        if not parent:
            return None
        
        end_pos = widget.pos()
        
        if direction == "left":
            start_pos = QPoint(-widget.width(), end_pos.y())
        elif direction == "right":
            start_pos = QPoint(parent.width(), end_pos.y())
        elif direction == "top":
            start_pos = QPoint(end_pos.x(), -widget.height())
        elif direction == "bottom":
            start_pos = QPoint(end_pos.x(), parent.height())
        else:
            start_pos = end_pos
        
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration or self._default_duration)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        if callback:
            animation.finished.connect(callback)
        
        widget.move(start_pos)
        widget.show()
        animation.start()
        
        self._animations.append(animation)
        return animation
    
    def slide_out(self, widget: QWidget, direction: str = "left",
                  duration: Optional[int] = None, callback: Optional[Callable] = None,
                  hide_on_finish: bool = True) -> QPropertyAnimation:
        """スライドアウト
        
        Args:
            widget: 対象ウィジェット
            direction: 方向（"left", "right", "top", "bottom"）
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            hide_on_finish: 完了時に非表示にするか
            
        Returns:
            アニメーションオブジェクト
        """
        # 終了位置を計算
        parent = widget.parent()
        if not parent:
            return None
        
        start_pos = widget.pos()
        
        if direction == "left":
            end_pos = QPoint(-widget.width(), start_pos.y())
        elif direction == "right":
            end_pos = QPoint(parent.width(), start_pos.y())
        elif direction == "top":
            end_pos = QPoint(start_pos.x(), -widget.height())
        elif direction == "bottom":
            end_pos = QPoint(start_pos.x(), parent.height())
        else:
            end_pos = start_pos
        
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration or self._default_duration)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        def on_finished():
            if hide_on_finish:
                widget.hide()
            if callback:
                callback()
        
        animation.finished.connect(on_finished)
        animation.start()
        
        self._animations.append(animation)
        return animation
    
    def scale(self, widget: QWidget, start_scale: float, end_scale: float,
              duration: Optional[int] = None, callback: Optional[Callable] = None) -> QPropertyAnimation:
        """スケールアニメーション
        
        Args:
            widget: 対象ウィジェット
            start_scale: 開始スケール
            end_scale: 終了スケール
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            
        Returns:
            アニメーションオブジェクト
        """
        # サイズアニメーションで代用
        original_size = widget.size()
        start_size = QSize(
            int(original_size.width() * start_scale),
            int(original_size.height() * start_scale)
        )
        end_size = QSize(
            int(original_size.width() * end_scale),
            int(original_size.height() * end_scale)
        )
        
        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(duration or self._default_duration)
        animation.setStartValue(start_size)
        animation.setEndValue(end_size)
        animation.setEasingCurve(self._default_easing)
        
        if callback:
            animation.finished.connect(callback)
        
        widget.resize(start_size)
        animation.start()
        
        self._animations.append(animation)
        return animation
    
    def bounce(self, widget: QWidget, height: int = 20,
               duration: Optional[int] = None, callback: Optional[Callable] = None) -> QSequentialAnimationGroup:
        """バウンスアニメーション
        
        Args:
            widget: 対象ウィジェット
            height: バウンスの高さ
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            
        Returns:
            アニメーショングループ
        """
        group = QSequentialAnimationGroup()
        
        original_pos = widget.pos()
        
        # 上に移動
        up_animation = QPropertyAnimation(widget, b"pos")
        up_animation.setDuration((duration or self._default_duration) // 2)
        up_animation.setStartValue(original_pos)
        up_animation.setEndValue(QPoint(original_pos.x(), original_pos.y() - height))
        up_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 下に戻る
        down_animation = QPropertyAnimation(widget, b"pos")
        down_animation.setDuration((duration or self._default_duration) // 2)
        down_animation.setStartValue(QPoint(original_pos.x(), original_pos.y() - height))
        down_animation.setEndValue(original_pos)
        down_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        
        group.addAnimation(up_animation)
        group.addAnimation(down_animation)
        
        if callback:
            group.finished.connect(callback)
        
        group.start()
        
        self._animations.append(group)
        return group
    
    def shake(self, widget: QWidget, amplitude: int = 10, 
              duration: Optional[int] = None, callback: Optional[Callable] = None) -> QSequentialAnimationGroup:
        """シェイクアニメーション
        
        Args:
            widget: 対象ウィジェット
            amplitude: 振幅
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            
        Returns:
            アニメーショングループ
        """
        group = QSequentialAnimationGroup()
        
        original_pos = widget.pos()
        shake_duration = (duration or self._default_duration) // 6
        
        # 左右に振動
        positions = [
            QPoint(original_pos.x() - amplitude, original_pos.y()),
            QPoint(original_pos.x() + amplitude, original_pos.y()),
            QPoint(original_pos.x() - amplitude // 2, original_pos.y()),
            QPoint(original_pos.x() + amplitude // 2, original_pos.y()),
            original_pos
        ]
        
        for i, pos in enumerate(positions):
            animation = QPropertyAnimation(widget, b"pos")
            animation.setDuration(shake_duration)
            animation.setEndValue(pos)
            
            if i == 0:
                animation.setStartValue(original_pos)
            
            group.addAnimation(animation)
        
        if callback:
            group.finished.connect(callback)
        
        group.start()
        
        self._animations.append(group)
        return group
    
    def pulse(self, widget: QWidget, scale_factor: float = 1.1,
              duration: Optional[int] = None, repeat: int = 1,
              callback: Optional[Callable] = None) -> QSequentialAnimationGroup:
        """パルスアニメーション
        
        Args:
            widget: 対象ウィジェット
            scale_factor: 拡大率
            duration: アニメーション時間（ミリ秒）
            repeat: 繰り返し回数
            callback: 完了時のコールバック
            
        Returns:
            アニメーショングループ
        """
        group = QSequentialAnimationGroup()
        
        for _ in range(repeat):
            # 拡大
            expand = self.scale(widget, 1.0, scale_factor, duration // 2)
            # 縮小
            shrink = self.scale(widget, scale_factor, 1.0, duration // 2)
            
            # グループには新しいアニメーションを作成
            expand_anim = QPropertyAnimation(widget, b"size")
            expand_anim.setDuration((duration or self._default_duration) // 2)
            expand_anim.setStartValue(widget.size())
            expand_anim.setEndValue(QSize(
                int(widget.width() * scale_factor),
                int(widget.height() * scale_factor)
            ))
            expand_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            shrink_anim = QPropertyAnimation(widget, b"size")
            shrink_anim.setDuration((duration or self._default_duration) // 2)
            shrink_anim.setStartValue(QSize(
                int(widget.width() * scale_factor),
                int(widget.height() * scale_factor)
            ))
            shrink_anim.setEndValue(widget.size())
            shrink_anim.setEasingCurve(QEasingCurve.Type.InCubic)
            
            group.addAnimation(expand_anim)
            group.addAnimation(shrink_anim)
        
        if callback:
            group.finished.connect(callback)
        
        group.start()
        
        self._animations.append(group)
        return group
    
    def color_transition(self, widget: QWidget, start_color: QColor, end_color: QColor,
                        duration: Optional[int] = None, callback: Optional[Callable] = None) -> QPropertyAnimation:
        """色のトランジション
        
        Args:
            widget: 対象ウィジェット
            start_color: 開始色
            end_color: 終了色
            duration: アニメーション時間（ミリ秒）
            callback: 完了時のコールバック
            
        Returns:
            アニメーションオブジェクト
        """
        # スタイルシートアニメーションで代用
        animation = QPropertyAnimation(widget, b"styleSheet")
        animation.setDuration(duration or self._default_duration)
        animation.setStartValue(f"background-color: {start_color.name()};")
        animation.setEndValue(f"background-color: {end_color.name()};")
        animation.setEasingCurve(self._default_easing)
        
        if callback:
            animation.finished.connect(callback)
        
        animation.start()
        
        self._animations.append(animation)
        return animation
    
    def stop_all(self):
        """すべてのアニメーションを停止"""
        for animation in self._animations:
            if animation and animation.state() == QAbstractAnimation.State.Running:
                animation.stop()
        self._animations.clear()
    
    def set_default_duration(self, duration: int):
        """デフォルトのアニメーション時間を設定"""
        self._default_duration = duration
    
    def set_default_easing(self, easing: QEasingCurve.Type):
        """デフォルトのイージングを設定"""
        self._default_easing = easing


# グローバルインスタンス
_animation_manager: Optional[AnimationManager] = None


def get_animation_manager() -> AnimationManager:
    """アニメーションマネージャーのシングルトンインスタンスを取得"""
    global _animation_manager
    if _animation_manager is None:
        _animation_manager = AnimationManager()
    return _animation_manager