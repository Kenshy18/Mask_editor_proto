// -*- coding: utf-8 -*-
#ifndef MASK_EDITOR_VIDEO_READER_H
#define MASK_EDITOR_VIDEO_READER_H

#include <string>
#include <memory>
#include <vector>
#include <optional>

// Forward declarations
struct AVFormatContext;
struct AVCodecContext;
struct AVFrame;
struct AVPacket;

namespace mask_editor {

/**
 * ビデオメタデータ
 */
struct VideoMetadata {
    int width;
    int height;
    double fps;
    int64_t frame_count;
    double duration;
    std::string codec;
    std::optional<int64_t> bit_rate;
    std::optional<std::string> color_space;
    std::optional<int> bit_depth;
    bool has_audio;
    std::optional<std::string> timecode;
};

/**
 * フレームデータ
 */
struct Frame {
    int index;
    int64_t pts;
    std::optional<int64_t> dts;
    std::vector<uint8_t> data;  // RGB24形式
    int width;
    int height;
};

/**
 * C++実装のビデオリーダー
 * 
 * FFmpegを直接使用して高速化。
 * IVideoReaderポートと同じインターフェースを提供。
 */
class CppVideoReader {
public:
    CppVideoReader();
    ~CppVideoReader();
    
    // コピー/ムーブ禁止
    CppVideoReader(const CppVideoReader&) = delete;
    CppVideoReader& operator=(const CppVideoReader&) = delete;
    CppVideoReader(CppVideoReader&&) = delete;
    CppVideoReader& operator=(CppVideoReader&&) = delete;
    
    /**
     * 動画ファイルを開く
     * @param path 動画ファイルのパス
     * @return メタデータ
     * @throw std::runtime_error ファイルが開けない場合
     */
    VideoMetadata open(const std::string& path);
    
    /**
     * 指定インデックスのフレームを読み込む
     * @param index フレームインデックス
     * @return フレームデータ（存在しない場合はnullopt）
     */
    std::optional<Frame> read_frame(int index);
    
    /**
     * 指定時間にシーク
     * @param timestamp シーク先の時間（秒）
     * @return 成功した場合true
     */
    bool seek(double timestamp);
    
    /**
     * リソースを解放
     */
    void close();
    
    /**
     * 現在開いているか確認
     */
    bool is_open() const { return format_ctx_ != nullptr; }

private:
    AVFormatContext* format_ctx_;
    AVCodecContext* codec_ctx_;
    AVFrame* frame_;
    AVFrame* rgb_frame_;
    AVPacket* packet_;
    
    int video_stream_index_;
    std::unique_ptr<VideoMetadata> metadata_;
    
    // RGB変換用
    struct SwsContext* sws_ctx_;
    std::vector<uint8_t> rgb_buffer_;
    
    void initialize_codec();
    void cleanup();
    std::optional<Frame> decode_frame();
};

} // namespace mask_editor

#endif // MASK_EDITOR_VIDEO_READER_H