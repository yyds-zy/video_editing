import gradio as gr
import cv2
import os
import numpy as np
from pathlib import Path
import tempfile
import shutil
import time
import subprocess # Import the subprocess module to run external commands like FFmpeg

# --- User Configuration START ---
# Please enter the full path to the FFmpeg executable here.
# Example (Windows): r"C:\ffmpeg\bin\ffmpeg.exe"
# Example (macOS/Linux): "/usr/local/bin/ffmpeg" or "/usr/bin/ffmpeg"
# If you are unsure about the path, please refer to the "How to find FFmpeg path" instructions below.
# If you prefer to rely on the system PATH (not recommended if errors occur here), set this variable to None.
FFMPEG_EXECUTABLE_PATH = r"D:\tools\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" # Replace None with your FFmpeg path, e.g., r"C:\ffmpeg\bin\ffmpeg.exe"
# --- User Configuration END ---


# Create the base output directory if it doesn't exist
CLIP_VIDEO_BASE_DIR = "CLIP_VIDEO"
os.makedirs(CLIP_VIDEO_BASE_DIR, exist_ok=True)

def extract_frame(video_path, frame_number):
    """Extract a specific frame from a video."""
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if ret:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame_rgb
        return None
    except Exception as e:
        print(f"Failed to extract frame: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()

def get_video_info(video_path):
    """Get video information."""
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        return {
            "fps": fps,
            "frame_count": frame_count,
            "duration": duration,
            "width": width,
            "height": height
        }
    except Exception as e:
        print(f"Failed to get video info: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()

def preview_video(video_path):
    """
    使用FFmpeg提取视频首帧进行预览，以避免大文件内存问题。
    """
    if not video_path:
        return None, "请先选择视频文件"

    try:
        if not os.path.exists(video_path):
            return None, "视频文件不存在或无法访问"
        
        # 首先尝试用OpenCV获取视频信息，因为它更快
        info = get_video_info(video_path)
        if info is None or info['duration'] <= 0 or info['fps'] <= 0:
            return None, "无法读取视频文件信息，请确保格式正确且未损坏。"

        # 使用FFmpeg来安全地提取预览帧
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_img_path = temp_file.name

        ffmpeg_cmd_name = ["ffmpeg"]
        if FFMPEG_EXECUTABLE_PATH and os.path.exists(FFMPEG_EXECUTABLE_PATH):
            ffmpeg_cmd_name = [FFMPEG_EXECUTABLE_PATH]
        
        # FFmpeg命令: 从视频文件第一秒 (-ss 1) 提取一帧 (-vframes 1)，并强制覆盖输出 (-y)
        # 将 -ss 放在 -i 之前以加快处理速度
        ffmpeg_command = ffmpeg_cmd_name + [
            "-ss", "1",
            "-i", video_path,
            "-vframes", "1",
            "-y",
            temp_img_path
        ]
        
        # 捕获FFmpeg的输出以进行调试
        process = subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True, shell=False)
        print("FFmpeg STDOUT:", process.stdout)
        print("FFmpeg STDERR:", process.stderr)

        # 使用OpenCV读取FFmpeg生成的图片
        preview_frame = cv2.imread(temp_img_path)
        if preview_frame is None:
            return None, "无法提取视频预览帧。请检查FFmpeg是否正常工作。"
            
        # Gradio需要RGB格式
        preview_frame_rgb = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
        
        # 移除临时文件
        os.remove(temp_img_path)
        
        info_text = f"""
        📹 视频信息:
        • 时长: {info['duration']:.2f} 秒
        • 帧率: {info['fps']:.1f} fps
        • 分辨率: {info['width']} x {info['height']}
        • 总帧数: {info['frame_count']}
        """
        
        return preview_frame_rgb, info_text
        
    except FileNotFoundError:
        return None, "❌ 错误：未找到FFmpeg。请检查FFMPEG_EXECUTABLE_PATH配置或系统PATH。"
    except subprocess.CalledProcessError as e:
        return None, f"❌ 预览失败。FFmpeg命令执行出错：{e.stderr}"
    except Exception as e:
        return None, f"预览失败：{str(e)}"

def update_status(video_path):
    """Update status indicator."""
    if not video_path:
        return """
        <div class="status-box ready-status">
            <span class="status-icon">🚀</span>
            <span class="status-text">系统就绪</span>
            <span class="status-info">• 支持MP4格式</span>
            <span class="status-info">• 自动切割</span>
            <span class="status-info">• 高质量输出</span>
        </div>
        """
    
    try:
        info = get_video_info(video_path)
        if info is None:
            return """
            <div class="status-box error-status">
                <span class="status-icon">⚠️</span>
                <span class="status-text">文件读取失败</span>
                <span class="status-info">• 请检查文件格式</span>
                <span class="status-info">• 确保文件完整</span>
            </div>
            """
        
        return f"""
        <div class="status-box success-status">
            <span class="status-icon">✅</span>
            <span class="status-text">视频已上传</span>
            <span class="status-info">• 时长: {info['duration']:.1f}s</span>
            <span class="status-info">• 分辨率: {info['width']}x{info['height']}</span>
            <span class="status-info">• 帧率: {info['fps']:.1f}fps</span>
        </div>
        """
    except Exception as e:
        print(f"Status update failed: {e}")
        return """
        <div class="status-box error-status">
            <span class="status-icon">⚠️</span>
            <span class="status-text">文件读取失败</span>
            <span class="status-info">• 请检查文件格式</span>
            <span class="status-info">• 确保文件完整</span>
            </div>
        """

def cut_video(video_path, clip_duration_input, progress=gr.Progress()):
    """
    Cuts the video and preserves audio.
    Uses FFmpeg to extract segments with audio directly from the source video file.
    """
    if not video_path:
        return "请先选择视频文件" # Please select a video file first
    
    if clip_duration_input <= 0:
        return "❌ 错误：切割时长必须大于0秒。" # Error: Clip duration must be greater than 0 seconds.

    try:
        # **Important Debugging Information**: Print the PATH environment variable of the current Python process
        print(f"Python process PATH: {os.environ.get('PATH')}")

        # Check if the file exists and is accessible
        if not os.path.exists(video_path):
            return "❌ 错误：视频文件不存在或无法访问" # Error: Video file does not exist or is inaccessible
        
        # Get video information (this still uses OpenCV's get_video_info, which doesn't rely on FFmpeg's PATH)
        info = get_video_info(video_path)
        if info is None:
            return "❌ 错误：无法读取视频文件信息。请确保视频文件格式正确。" # Error: Unable to read video file information. Please ensure the video file format is correct.
        
        duration = info['duration']
        
        # Validate video information
        if duration <= 0:
            return "❌ 错误：视频文件格式无效或损坏" # Error: Invalid or corrupted video file format
        
        if duration < clip_duration_input:
            return f"❌ 错误：视频时长太短，无法进行 {clip_duration_input} 秒切割（至少需要 {clip_duration_input} 秒）" # Error: Video duration is too short to cut for {clip_duration_input} seconds (at least {clip_duration_input} seconds required)
        
        # Calculate the number of clips (cut every 1 second, so it's 'duration' number of clips)
        # Note: total_clips here represents the number of *potential* start points
        total_potential_clips = int(duration)
        progress(0, desc="开始切割视频...") # Starting video cutting...
        
        cut_info = []
        actual_saved_clips_count = 0
        
        # Generate a timestamped directory for the current cutting operation
        timestamp_folder = time.strftime("clip_%Y%m%d_%H%M%S")
        current_output_dir = os.path.join(CLIP_VIDEO_BASE_DIR, timestamp_folder)
        os.makedirs(current_output_dir, exist_ok=True)
        
        # Determine FFmpeg command name or full path
        ffmpeg_cmd_name = ["ffmpeg"]
        if FFMPEG_EXECUTABLE_PATH:
            if not os.path.exists(FFMPEG_EXECUTABLE_PATH):
                return f"❌ 错误：配置的 FFmpeg 路径不存在：{FFMPEG_EXECUTABLE_PATH}" # Error: Configured FFmpeg path does not exist: {FFMPEG_EXECUTABLE_PATH}
            ffmpeg_cmd_name = [FFMPEG_EXECUTABLE_PATH]


        for i in range(total_potential_clips):
            # Calculate time range: start from second 'i', last for 'clip_duration_input' seconds
            start_time = i
            
            # Ensure the clip does not exceed the total video duration
            actual_end_time = min(start_time + clip_duration_input, duration)
            actual_clip_duration = actual_end_time - start_time

            # **IMPORTANT CHANGE**: Only save if the actual clip duration is exactly the desired input duration
            if actual_clip_duration < clip_duration_input:
                continue # Skip this segment if it's shorter than the desired duration

            # Set output filename, add zero-padding for numerical sorting
            output_filename = f"clip_{i:03d}.mp4" # Removed timestamp from individual clip name as it's now in the folder name
            output_path = os.path.join(current_output_dir, output_filename) # Save to the new timestamped directory
            
            # FFmpeg command construction
            # -ss: Specify start time (now performs input seeking for faster initial jump)
            # -i: Specify input file
            # -t: Specify duration
            # -c:v libx264: Re-encode video using H.264 codec. This ensures clean, frame-accurate cuts.
            # -preset veryfast: Balance encoding speed and output quality. Can be 'ultrafast', 'superfast', 'fast', 'medium', 'slow', etc.
            # -crf 23: Constant Rate Factor. A quality-based setting for H.264. Lower value = higher quality/larger file size. 23 is a good default.
            # -c:a aac: Encode audio to AAC format for compatibility
            # -b:a 192k: Set audio bitrate to 192kbps for good audio quality
            # -map 0:v:0?: Map the first video stream (optional, avoids errors if no video stream)
            # -map 0:a:0?: Map the first audio stream (optional)
            # -y: Overwrite output file automatically without confirmation
            ffmpeg_command = ffmpeg_cmd_name + [
                "-ss", str(start_time), # Moved -ss BEFORE -i for fast input seeking
                "-i", video_path,
                "-t", str(actual_clip_duration), # Use actual_clip_duration here
                "-c:v", "libx264",       # Re-encode video to ensure clean start
                "-preset", "veryfast",   # Encoding preset for speed/quality balance
                "-crf", "23",            # Quality setting for H.264
                "-c:a", "aac",
                "-b:a", "192k", 
                "-map", "0:v:0?", 
                "-map", "0:a:0?", 
                "-y", 
                output_path
            ]
            
            # Update progress bar
            progress((i + 1) / total_potential_clips, desc=f"正在处理第 {i + 1}/{total_potential_clips} 段 (从 {start_time:.1f}s 到 {actual_end_time:.1f}s)...") # Processing segment {i+1}/{total_potential_clips} (from {start_time:.1f}s to {actual_end_time:.1f}s)...
            
            try:
                # Execute FFmpeg command
                subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True, shell=False) 
                cut_info.append(f"✅ {output_filename} - {start_time:.1f}s 到 {actual_end_time:.1f}s (时长: {actual_clip_duration:.1f}s)")
                actual_saved_clips_count += 1
            except subprocess.CalledProcessError as e:
                # Error handling for failed FFmpeg command execution
                print(f"FFmpeg command execution failed: {e}")
                print(f"STDOUT: {e.stdout}")
                print(f"STDERR: {e.stderr}")
                cut_info.append(f"❌ 失败: {output_filename} (从 {start_time:.1f}s 到 {actual_end_time:.1f}s) - 错误: {e.stderr.strip()}") # Failed: {output_filename} (from {start_time:.1f}s to {actual_end_time:.1f}s) - Error: {e.stderr.strip()}
            except FileNotFoundError:
                # Error handling for FFmpeg executable not found
                return "❌ 错误：未找到 FFmpeg。请确保 FFmpeg 已安装并配置在系统 PATH 中，或者在代码中显式指定 FFMPEG_EXECUTABLE_PATH。" # Error: FFmpeg not found. Please ensure FFmpeg is installed and configured in your system PATH, or specify FFMPEG_EXECUTABLE_PATH explicitly in the code.
            except Exception as e:
                # Other exception handling
                cut_info.append(f"❌ 失败: {output_filename} (从 {start_time:.1f}s 到 {actual_end_time:.1f}s) - 错误: {str(e)}") # Failed: {output_filename} (from {start_time:.1f}s to {actual_end_time:.1f}s) - Error: {str(e)}
        
        # Generate final result report
        result = f"""
🎬 视频切割完成！ # Video cutting complete!

📊 切割统计: # Cutting statistics:
• 总尝试处理段数: {total_potential_clips} # Total attempted clips:
• 实际保存段数: {actual_saved_clips_count} # Actual saved clips:
• 输出目录: {current_output_dir} # Output directory:
• 每段理论时长: {clip_duration_input}秒 # Theoretical duration per clip: {clip_duration_input} seconds
• 输出格式: MP4 (视频重新编码为H.264，音频重新编码为AAC) # Output format: MP4 (video re-encoded to H.264, audio re-encoded to AAC)

📁 切割详情: # Cutting details:
{chr(10).join(cut_info)}

✨ 所有视频文件已保存到 {current_output_dir} 目录。 # All video files saved to {current_output_dir} directory.
请注意，由于进行了重新编码，切割过程可能会比之前更慢一些。 # Please note that due to re-encoding, the cutting process might be slower than before.
        """
        
        return result
        
    except Exception as e:
        return f"切割失败: {str(e)}" # Cutting failed

# Custom CSS styles - Modern dark theme
custom_css = """
/* Basic styles for the entire page */
.gradio-container {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 25%, #0f3460 50%, #16213e 75%, #1a1a2e 100%);
    min-height: 100vh;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #e8f4fd;
    padding: 0;
    overflow-x: hidden;
}

/* Main content wrapper, providing the centered layout and shadow effect */
.main-wrapper {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 40px 20px;
    box-sizing: border-box;
}

/* Central card container for the main interface */
.main-card {
    background: linear-gradient(135deg, rgba(22, 33, 62, 0.95) 0%, rgba(15, 52, 96, 0.95) 100%);
    border-radius: 20px;
    padding: 30px;
    max-width: 1200px;
    width: 100%;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    display: flex;
    flex-direction: column;
    gap: 30px;
}

/* Header section (Title and subtitle) */
.header-section {
    text-align: center;
}

.title {
    background: linear-gradient(45deg, #00d4ff, #0099cc, #00d4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 3em;
    font-weight: 800;
    margin-bottom: 5px;
    text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
    letter-spacing: 2px;
}

.subtitle {
    color: #b8c6db;
    font-size: 1.3em;
    margin-bottom: 0;
    opacity: 0.9;
    font-weight: 300;
}

/* Status indicator on top of the page */
.status-box {
    text-align: center;
    margin-bottom: 20px;
    padding: 10px 20px;
    border-radius: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    font-weight: 600;
    transition: all 0.3s ease;
    border: 1px solid;
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    width: auto;
    max-width: 90%;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(8px);
}

.status-box.ready-status {
    background: rgba(0, 212, 255, 0.1);
    border-color: rgba(0, 212, 255, 0.3);
    color: #00d4ff;
}

.status-box.success-status {
    background: rgba(46, 204, 113, 0.1);
    border-color: rgba(46, 204, 113, 0.3);
    color: #2ecc71;
}

.status-box.error-status {
    background: rgba(231, 76, 60, 0.1);
    border-color: rgba(231, 76, 60, 0.3);
    color: #e74c3c;
}

.status-icon {
    font-size: 1.2em;
}

.status-text {
    font-weight: bold;
}

.status-info {
    font-weight: 400;
    color: #b8c6db;
    font-size: 0.9em;
}

/* Section titles */
.section-title {
    color: #00d4ff;
    font-size: 1.4em;
    font-weight: 600;
    margin-bottom: 15px;
    text-align: center;
    text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

/* Card for video input and settings */
.input-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    padding: 25px;
    border: 1px solid rgba(0, 212, 255, 0.2);
    backdrop-filter: blur(5px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
    display: flex;
    flex-direction: column;
    gap: 20px;
}

/* File upload area styling */
.upload-box {
    border: 3px dashed #00d4ff !important;
    border-radius: 15px !important;
    background: rgba(0, 212, 255, 0.05) !important;
    transition: all 0.4s ease;
    min-height: 140px;
    position: relative;
    overflow: hidden;
}

.upload-box:hover {
    border-color: #0099cc !important;
    background: rgba(0, 212, 255, 0.1) !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 212, 255, 0.2);
}

.upload-box::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.1), transparent);
    transition: left 0.5s;
}

.upload-box:hover::before {
    left: 100%;
}

/* Card for preview and info display */
.preview-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    padding: 25px;
    border: 1px solid rgba(0, 212, 255, 0.2);
    backdrop-filter: blur(5px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
    min-height: 220px;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

/* Info box styling */
.info-box {
    background: rgba(0, 212, 255, 0.08);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 15px;
    padding: 20px;
    min-height: 140px;
    backdrop-filter: blur(5px);
    color: #e8f4fd;
}

/* Button group layout optimization */
.button-row {
    display: flex;
    gap: 20px;
    justify-content: center;
    align-items: center;
    margin-top: 20px;
}

/* Preview Button */
.preview-button {
    background: linear-gradient(45deg, #667eea, #764ba2) !important;
    border: none !important;
    border-radius: 25px !important;
    padding: 15px 30px !important;
    font-size: 1.1em !important;
    font-weight: 600 !important;
    color: white !important;
    transition: all 0.3s ease;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    position: relative;
    overflow: hidden;
}

.preview-button:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.6);
}

.preview-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.preview-button:hover::before {
    left: 100%;
}

/* Cut Button */
.cut-button {
    background: linear-gradient(45deg, #ff6b6b, #ee5a24) !important;
    border: none !important;
    border-radius: 25px !important;
    padding: 18px 35px !important;
    font-size: 1.2em !important;
    font-weight: 700 !important;
    color: white !important;
    transition: all 0.3s ease;
    box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4);
    position: relative;
    overflow: hidden;
}

.cut-button:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 35px rgba(255, 107, 107, 0.6);
}

.cut-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.cut-button:hover::before {
    left: 100%;
}

/* Results section styling */
.result-section {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: 30px;
}

.result-title {
    color: #00d4ff;
    font-size: 1.5em;
    font-weight: 600;
    margin-bottom: 20px;
    text-align: center;
    text-shadow: 0 0 15px rgba(0, 212, 255, 0.4);
}

.result-box {
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 15px;
    padding: 25px;
    width: 100%;
    color: #e8f4fd;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    white-space: pre-wrap;
    min-height: 220px;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

/* Responsive layout optimization */
@media (max-width: 900px) {
    .main-card {
        padding: 20px;
        flex-direction: column;
    }
    .main-grid {
        flex-direction: column;
        gap: 20px;
    }
    .button-row {
        flex-direction: column;
        gap: 15px;
    }
    .title {
        font-size: 2.5em;
    }
    .subtitle {
        font-size: 1.1em;
    }
    .status-info {
        display: none;
    }
}

/* Gradio's internal styles to override */
.gradio-container .form {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
}
::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(45deg, #00d4ff, #0099cc);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(45deg, #0099cc, #00d4ff);
}
"""

# Create Gradio interface
with gr.Blocks(css=custom_css, title="视频切割软件") as demo:
    # Status indicator (positioned at the top)
    status_indicator = gr.HTML(
        update_status(None)
    )
    
    with gr.Column(elem_classes="main-wrapper"):
        with gr.Column(elem_classes="main-card"):
            # Header section
            gr.HTML('<div class="header-section"><h1 class="title">🎬 智能视频切割器</h1><p class="subtitle">专业级视频切割工具 - 支持MP4格式，每隔1秒切割一段自定义时长的视频</p></div>')
            
            # Main operational area
            with gr.Row(elem_classes="main-grid"):
                # Left side: File upload and control settings
                with gr.Column(scale=1, elem_classes="input-card"):
                    gr.HTML('<h3 class="section-title">📁 选择视频文件</h3>')
                    video_input = gr.Video(
                        label="上传MP4视频文件",
                        elem_classes="upload-box",
                        height=140,
                        interactive=True
                    )

                    gr.HTML('<h3 class="section-title">⏱️ 切割设置</h3>')
                    clip_duration_input = gr.Number(
                        label="每段视频时长 (秒)",
                        value=3,
                        minimum=1,
                        maximum=300,
                        step=1,
                        info="每隔1秒切割一段指定时长的视频，不足指定时长的片段将被忽略。"
                    )
                    
                    with gr.Row(elem_classes="button-row"):
                        preview_btn = gr.Button(
                            "🔍 预览视频",
                            variant="secondary",
                            size="lg",
                            elem_classes="preview-button"
                        )
                        
                        cut_btn = gr.Button(
                            "✂️ 开始切割",
                            variant="primary",
                            size="lg",
                            elem_classes="cut-button"
                        )
                
                # Right side: Preview and information display
                with gr.Column(scale=1, elem_classes="preview-card"):
                    gr.HTML('<h3 class="section-title">🖼️ 视频预览</h3>')
                    preview_image = gr.Image(
                        label="视频预览",
                        elem_classes="preview-container",
                        height=220,
                        interactive=False,
                        container=False
                    )
                    
                    gr.HTML('<h3 class="section-title">📊 视频信息</h3>')
                    info_text = gr.Textbox(
                        label="视频详情",
                        elem_classes="info-box",
                        lines=8,
                        interactive=False
                    )

            # Cutting results display area
            with gr.Column(elem_classes="result-section"):
                gr.HTML('<h3 class="result-title">📋 切割结果</h3>')
                result_text = gr.Textbox(
                    label="处理结果",
                    elem_classes="result-box",
                    lines=15,
                    interactive=False
                )
        
    # Bind events
    video_input.change(
        fn=update_status,
        inputs=[video_input],
        outputs=[status_indicator]
    )
    
    preview_btn.click(
        fn=preview_video,
        inputs=[video_input],
        outputs=[preview_image, info_text]
    )
    
    cut_btn.click(
        fn=cut_video,
        inputs=[video_input, clip_duration_input],
        outputs=[result_text]
    )

# Launch the application
if __name__ == "__main__":
    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=True,
            show_error=True,
            quiet=False,
        )
    except Exception as e:
        print(f"Failed to launch: {e}")
        try:
            demo.launch(
                server_name="127.0.0.1",
                server_port=7861,
                share=True,
                show_error=True,
                quiet=False,
            )
        except Exception as e2:
            print(f"Alternate port launch also failed: {e2}")
            print("Please check if the port is occupied or try specifying a port manually")