import os
from typing import Any

import ffmpeg

from .state import VideoGenerationState


def get_media_duration(file_path: str) -> float:
    """
    获取媒体文件的时长（秒）
    
    Args:
        file_path: 媒体文件路径
        
    Returns:
        文件时长（秒）
    """
    try:
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        return duration
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        # 尝试从streams获取时长
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e2:
            print(f"Error getting duration from streams for {file_path}: {e2}")
            return 0.0


def adjust_audio_length(audio_path: str, video_path: str, output_path: str) -> str:
    """
    调整音频长度以匹配视频长度（通过截断或填充静音）
    
    Args:
        audio_path: 音频文件路径
        video_path: 视频文件路径
        output_path: 输出文件路径
        
    Returns:
        调整后的音频文件路径
    """
    try:
        # 获取视频时长
        video_duration = get_media_duration(video_path)
        if video_duration <= 0:
            print(f"Could not get video duration for {video_path}")
            return audio_path
            
        # 获取音频时长
        audio_duration = get_media_duration(audio_path)
        if audio_duration <= 0:
            print(f"Could not get audio duration for {audio_path}")
            return audio_path
            
        # 如果音频和视频时长相同（误差在100毫秒内），直接返回原音频
        if abs(video_duration - audio_duration) < 0.1:
            return audio_path
            
        # 使用ffmpeg处理音频长度
        audio_input = ffmpeg.input(audio_path)
        
        if audio_duration > video_duration:
            # 音频过长，需要截断
            adjusted_audio = ffmpeg.filter(audio_input, 'atrim', duration=video_duration)
            print(f"Truncated audio {audio_path} from {audio_duration:.2f}s to {video_duration:.2f}s")
        else:
            # 音频过短，需要填充静音
            # 创建静音音频流
            silence = ffmpeg.input("anullsrc=channel_layout=stereo:sample_rate=44100", f="lavfi")
            # 截取所需长度的静音
            silence_clip = ffmpeg.filter(silence, 'atrim', duration=video_duration - audio_duration)
            # 连接原音频和静音
            adjusted_audio = ffmpeg.filter([audio_input, silence_clip], 'concat', v=0, a=1)
            print(f"Padded audio {audio_path} from {audio_duration:.2f}s to {video_duration:.2f}s with silence")
        
        # 输出调整后的音频
        output = ffmpeg.output(
            adjusted_audio,
            output_path,
            acodec='libmp3lame',  # 使用MP3编码器
            audio_bitrate='128k'
        )
            
        output.overwrite_output().run(capture_stdout=True, capture_stderr=True)
        return output_path
        
    except ffmpeg.Error as e:
        print(f"FFmpeg error adjusting audio length: {e}")
        if e.stderr:
            print(e.stderr.decode())
        return audio_path
    except Exception as e:
        print(f"Error adjusting audio length: {e}")
        return audio_path


async def video_concatenation_node(state: VideoGenerationState) -> dict[str, Any]:
    print("Executing: Video concatenation node")

    root_dir: str = state["root_dir"]
    video_and_audio_dir = os.path.join(root_dir, "video_and_audio")
    os.makedirs(video_and_audio_dir, exist_ok=True)

    final_video = os.path.join(root_dir, "final_video.mp4")

    # 确保video_segments和audio_segments是列表类型，避免NoneType错误
    video_segments: list[str] = state.get("video_segments", [])
    audio_segments: list[str] = state.get("audio_files", [])
    
    # 如果video_segments为None，则初始化为空列表
    if video_segments is None:
        video_segments = []
        
    # 如果audio_segments为None，则初始化为空列表
    if audio_segments is None:
        audio_segments = []

    merged_segments: list[str] = []

    # 只有当两个列表都非空时才进行音视频合并
    if video_segments and audio_segments:
        for idx, (v_path, a_path) in enumerate(zip(video_segments, audio_segments)):
            if not (os.path.isfile(v_path) and os.path.isfile(a_path)):
                print(f"Skip missing pair: {v_path} + {a_path}")
                merged_segments.append(v_path)
                continue

            # 调整音频长度以匹配视频长度
            adjusted_audio_path = os.path.join(video_and_audio_dir, f"adjusted_{idx}.mp3")  # 确保使用.mp3扩展名
            adjusted_audio = adjust_audio_length(a_path, v_path, adjusted_audio_path)
            
            # 合并视频和调整后的音频
            out_path = os.path.join(video_and_audio_dir, f"{idx}.mp4")
            try:
                video_input = ffmpeg.input(v_path)
                audio_input = ffmpeg.input(adjusted_audio)

                output = ffmpeg.output(
                    video_input,
                    audio_input,
                    out_path,
                    vcodec="copy",  # 视频不需要重新编码
                    acodec="aac",
                    shortest=None,  # 不使用shortest参数，因为我们已经调整了音频长度
                    avoid_negative_ts="make_zero",
                )

                output.overwrite_output().run(capture_stdout=True, capture_stderr=True)
                merged_segments.append(out_path)
                print(f"Merged segment {idx}")
                
                # 清理临时调整的音频文件（如果不是原始音频文件）
                if adjusted_audio != a_path and os.path.exists(adjusted_audio) and adjusted_audio == adjusted_audio_path:
                    try:
                        os.remove(adjusted_audio)
                    except Exception as e:
                        print(f"Warning: Could not remove temporary file {adjusted_audio}: {e}")
            except ffmpeg.Error as e:
                print(f"Merge failed for segment {idx}: {e}")
                if e.stderr:
                    print(e.stderr.decode())
                merged_segments.append(v_path)  # fallback
    else:
        # 如果没有音频文件，则直接使用视频文件
        print("No audio files provided, using video segments directly")
        merged_segments = [v for v in video_segments if v and os.path.isfile(v)]
    
    if not merged_segments:
        print("No segments to concatenate")
        return {"final_video": ""}

    concat_list_path = os.path.join(video_and_audio_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for seg in merged_segments:
            abs_seg = os.path.abspath(seg)
            f.write(f"file '{abs_seg}'\n")

    try:
        (
            ffmpeg.input(concat_list_path, format="concat", safe=0)
            .output(final_video, c="copy", avoid_negative_ts="make_zero")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print("🎉 Concatenated with concat demuxer")
    except ffmpeg.Error as e:
        print("Concat demuxer failed, trying concat filter…", e)
        try:
            inputs = [ffmpeg.input(s) for s in merged_segments if s]
            if inputs:
                joined = ffmpeg.concat(*inputs, v=1, a=1).node
                (
                    ffmpeg.output(
                        joined[0], joined[1], final_video, vcodec="libx264", acodec="aac"
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                print("🎉 Concatenated with concat filter")
            else:
                print("No valid inputs for concatenation")
                return {"final_video": ""}
        except ffmpeg.Error as e2:
            print("All concatenation failed, copying first segment:", e2)
            if merged_segments and merged_segments[0] and os.path.isfile(merged_segments[0]):
                import shutil
                shutil.copy2(merged_segments[0], final_video)
            else:
                print("No valid segment to copy")
                return {"final_video": ""}

    return {"final_video": final_video, "root_dir": root_dir}