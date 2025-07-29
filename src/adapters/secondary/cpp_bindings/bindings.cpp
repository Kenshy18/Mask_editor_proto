// -*- coding: utf-8 -*-
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "video_reader.h"

namespace py = pybind11;
using namespace mask_editor;

// numpy配列への変換
py::array_t<uint8_t> frame_to_numpy(const Frame& frame) {
    // RGB24形式のデータをnumpy配列に変換
    auto result = py::array_t<uint8_t>(
        {frame.height, frame.width, 3},  // shape
        {frame.width * 3, 3, 1}          // strides
    );
    
    // データをコピー
    auto buf = result.mutable_unchecked<3>();
    size_t idx = 0;
    for (py::ssize_t i = 0; i < frame.height; ++i) {
        for (py::ssize_t j = 0; j < frame.width; ++j) {
            for (py::ssize_t k = 0; k < 3; ++k) {
                buf(i, j, k) = frame.data[idx++];
            }
        }
    }
    
    return result;
}

PYBIND11_MODULE(mask_editor_cpp, m) {
    m.doc() = "Mask Editor GOD C++ acceleration module";
    
    // VideoMetadata構造体
    py::class_<VideoMetadata>(m, "VideoMetadata")
        .def(py::init<>())
        .def_readwrite("width", &VideoMetadata::width)
        .def_readwrite("height", &VideoMetadata::height)
        .def_readwrite("fps", &VideoMetadata::fps)
        .def_readwrite("frame_count", &VideoMetadata::frame_count)
        .def_readwrite("duration", &VideoMetadata::duration)
        .def_readwrite("codec", &VideoMetadata::codec)
        .def_readwrite("bit_rate", &VideoMetadata::bit_rate)
        .def_readwrite("color_space", &VideoMetadata::color_space)
        .def_readwrite("bit_depth", &VideoMetadata::bit_depth)
        .def_readwrite("has_audio", &VideoMetadata::has_audio)
        .def_readwrite("timecode", &VideoMetadata::timecode);
    
    // Frame構造体
    py::class_<Frame>(m, "Frame")
        .def(py::init<>())
        .def_readwrite("index", &Frame::index)
        .def_readwrite("pts", &Frame::pts)
        .def_readwrite("dts", &Frame::dts)
        .def_readwrite("width", &Frame::width)
        .def_readwrite("height", &Frame::height)
        .def_property_readonly("data", [](const Frame& f) {
            return frame_to_numpy(f);
        });
    
    // CppVideoReaderクラス
    py::class_<CppVideoReader>(m, "CppVideoReader")
        .def(py::init<>())
        .def("open", &CppVideoReader::open,
             "Open a video file",
             py::arg("path"))
        .def("read_frame", &CppVideoReader::read_frame,
             "Read a frame by index",
             py::arg("index"))
        .def("seek", &CppVideoReader::seek,
             "Seek to timestamp",
             py::arg("timestamp"))
        .def("close", &CppVideoReader::close,
             "Close the video file")
        .def("is_open", &CppVideoReader::is_open,
             "Check if a video is open")
        .def("__enter__", [](CppVideoReader& self) -> CppVideoReader& {
            return self;
        })
        .def("__exit__", [](CppVideoReader& self, py::object, py::object, py::object) {
            self.close();
        });
    
    // バージョン情報
    #ifdef VERSION_INFO
    m.attr("__version__") = VERSION_INFO;
    #else
    m.attr("__version__") = "dev";
    #endif
}