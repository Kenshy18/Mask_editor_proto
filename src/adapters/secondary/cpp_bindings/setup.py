#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++バインディングのセットアップスクリプト

pybind11を使用してC++実装をPythonにバインド。
"""
from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext

# C++拡張モジュール定義
ext_modules = [
    Pybind11Extension(
        "mask_editor_cpp",
        ["video_reader.cpp", "bindings.cpp"],
        include_dirs=[".", "/usr/include/ffmpeg"],  # FFmpeg/OpenCVヘッダ
        libraries=["avformat", "avcodec", "avutil", "swscale", "opencv_core", "opencv_imgproc"],
        library_dirs=["/usr/lib", "/usr/local/lib"],
        cxx_std=17,  # C++17標準
        define_macros=[("VERSION_INFO", "0.1.0")],
    ),
]

setup(
    name="mask_editor_cpp",
    version="0.1.0",
    author="Mask Editor GOD Team",
    author_email="team@maskeditor.example.com",
    description="C++ accelerated video processing for Mask Editor GOD",
    long_description="High-performance C++ implementations of video processing components",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.11",
)