import gradio as gr
import cv2
import os
import numpy as np
from pathlib import Path
import tempfile
import shutil
import time

# 创建输出目录
CLIP_VIDEO_DIR = "CLIP_VIDEO"
os.makedirs(CLIP_VIDEO_DIR, exist_ok=True)

def extract_frame(video_path, frame_number):
    """从视频中提取指定帧"""
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if ret:
            # 转换BGR到RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame_rgb
        return None
    except Exception as e:
        print(f"提取帧失败: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()

def get_video_info(video_path):
    """获取视频信息"""
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
        print(f"获取视频信息失败: {e}")
        return None
    finally:
        if cap is not None:
            cap.release()

def preview_video(video_path):
    """预览视频"""
    if not video_path:
        return None, "请先选择视频文件"
    
    try:
        # 检查文件是否存在且可访问
        if not os.path.exists(video_path):
            return None, "视频文件不存在或无法访问"
        
        info = get_video_info(video_path)
        if info is None:
            return None, "无法读取视频文件信息"
        
        # 检查视频信息是否有效
        if info['duration'] <= 0 or info['fps'] <= 0:
            return None, "视频文件格式无效或损坏"
        
        # 提取第一帧作为预览
        preview_frame = extract_frame(video_path, 0)
        
        if preview_frame is None:
            return None, "无法提取视频预览帧"
        
        info_text = f"""
        📹 视频信息:
        • 时长: {info['duration']:.2f} 秒
        • 帧率: {info['fps']:.1f} fps
        • 分辨率: {info['width']} x {info['height']}
        • 总帧数: {info['frame_count']}
        """
        
        return preview_frame, info_text
    except Exception as e:
        return None, f"预览失败: {str(e)}"

def update_status(video_path):
    """更新状态指示器"""
    if not video_path:
        return '''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: inline-block; background: rgba(0, 212, 255, 0.1); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 20px; padding: 10px 20px;">
                <span style="color: #00d4ff; font-weight: 600;">🚀 系统就绪</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 支持MP4格式</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 自动切割</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 高质量输出</span>
            </div>
        </div>
        '''
    
    try:
        info = get_video_info(video_path)
        if info is None:
            return '''
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="display: inline-block; background: rgba(231, 76, 60, 0.1); border: 1px solid rgba(231, 76, 60, 0.3); border-radius: 20px; padding: 10px 20px;">
                    <span style="color: #e74c3c; font-weight: 600;">⚠️ 文件读取失败</span>
                    <span style="color: #b8c6db; margin-left: 15px;">• 请检查文件格式</span>
                    <span style="color: #b8c6db; margin-left: 15px;">• 确保文件完整</span>
                </div>
            </div>
            '''
        
        return f'''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: inline-block; background: rgba(46, 204, 113, 0.1); border: 1px solid rgba(46, 204, 113, 0.3); border-radius: 20px; padding: 10px 20px;">
                <span style="color: #2ecc71; font-weight: 600;">✅ 视频已上传</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 时长: {info['duration']:.1f}s</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 分辨率: {info['width']}x{info['height']}</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 帧率: {info['fps']:.1f}fps</span>
            </div>
        </div>
        '''
    except Exception as e:
        print(f"状态更新失败: {e}")
        return '''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: inline-block; background: rgba(231, 76, 60, 0.1); border: 1px solid rgba(231, 76, 60, 0.3); border-radius: 20px; padding: 10px 20px;">
                <span style="color: #e74c3c; font-weight: 600;">⚠️ 文件读取失败</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 请检查文件格式</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 确保文件完整</span>
            </div>
        </div>
        '''

def cut_video(video_path, progress=gr.Progress()):
    """切割视频"""
    if not video_path:
        return "请先选择视频文件"
    
    try:
        # 检查文件是否存在且可访问
        if not os.path.exists(video_path):
            return "❌ 错误：视频文件不存在或无法访问"
        
        # 获取视频信息
        info = get_video_info(video_path)
        if info is None:
            return "❌ 错误：无法读取视频文件信息"
        
        fps = info['fps']
        duration = info['duration']
        
        # 验证视频信息
        if duration <= 0 or fps <= 0:
            return "❌ 错误：视频文件格式无效或损坏"
        
        if duration < 3:
            return "❌ 错误：视频时长太短，无法进行3秒切割（至少需要3秒）"
        
        # 计算切割段数
        total_clips = int(duration)
        progress(0, desc="开始切割视频...")
        
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 设置输出编码器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        cut_info = []
        
        # 获取当前时间戳用于文件命名
        current_timestamp = int(time.time())
        
        for i in range(total_clips):
            progress((i + 1) / total_clips, desc=f"正在切割第 {i + 1}/{total_clips} 段...")
            
            # 计算时间范围：从第i秒开始，持续3秒
            start_time = i
            end_time = min(i + 3, duration)
            
            # 计算帧范围
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            # 设置输出文件名
            output_filename = f"{current_timestamp}_{i}.mp4"
            output_path = os.path.join(CLIP_VIDEO_DIR, output_filename)
            
            # 创建视频写入器
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 设置起始帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # 写入帧
            frame_count = 0
            max_frames = int((end_time - start_time) * fps)
            
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                frame_count += 1
            
            out.release()
            
            # 记录切割信息
            cut_info.append(f"✅ {output_filename} - {start_time:.1f}s 到 {end_time:.1f}s")
        
        cap.release()
        
        # 生成结果报告
        result = f"""
🎬 视频切割完成！

📊 切割统计:
• 总段数: {total_clips}
• 输出目录: {CLIP_VIDEO_DIR}
• 每段时长: 3秒
• 输出格式: MP4 (30fps)

📁 切割详情:
{chr(10).join(cut_info)}

✨ 所有视频文件已保存到 CLIP_VIDEO 目录
        """
        
        return result
        
    except Exception as e:
        return f"切割失败: {str(e)}"

# 自定义CSS样式 - 现代化深色主题
custom_css = """
.gradio-container {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 25%, #0f3460 50%, #16213e 75%, #1a1a2e 100%);
    min-height: 100vh;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding: 0;
}

.main-container {
    background: linear-gradient(135deg, rgba(22, 33, 62, 0.95) 0%, rgba(15, 52, 96, 0.95) 100%);
    border-radius: 20px;
    padding: 30px;
    margin: 20px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
}

.title {
    background: linear-gradient(45deg, #00d4ff, #0099cc, #00d4ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    font-size: 3em;
    font-weight: 800;
    margin-bottom: 20px;
    text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
    letter-spacing: 2px;
}

.subtitle {
    color: #b8c6db;
    text-align: center;
    font-size: 1.3em;
    margin-bottom: 40px;
    opacity: 0.9;
    font-weight: 300;
}

.section-title {
    color: #00d4ff;
    font-size: 1.4em;
    font-weight: 600;
    margin-bottom: 15px;
    text-align: center;
    text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

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

.preview-container {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    padding: 25px;
    border: 1px solid rgba(0, 212, 255, 0.2);
    min-height: 220px;
    backdrop-filter: blur(5px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.info-box {
    background: rgba(0, 212, 255, 0.08);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 15px;
    padding: 20px;
    margin: 15px 0;
    min-height: 140px;
    backdrop-filter: blur(5px);
}

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
    margin: 15px 0;
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
    margin: 15px 0;
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

.result-box {
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 15px;
    padding: 25px;
    margin: 25px 0;
    color: #e8f4fd;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    white-space: pre-wrap;
    min-height: 220px;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.result-title {
    color: #00d4ff;
    font-size: 1.5em;
    font-weight: 600;
    margin-bottom: 20px;
    text-align: center;
    text-shadow: 0 0 15px rgba(0, 212, 255, 0.4);
}

/* 响应式布局优化 */
@media (max-width: 768px) {
    .main-container {
        margin: 10px;
        padding: 20px;
    }
    
    .title {
        font-size: 2.2em;
    }
    
    .subtitle {
        font-size: 1.1em;
    }
}

/* 动画效果 */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.fade-in-up {
    animation: fadeInUp 0.6s ease-out;
}

/* 按钮组布局优化 */
.button-row {
    display: flex;
    gap: 20px;
    justify-content: center;
    align-items: center;
    margin: 20px 0;
}

/* 滚动条美化 */
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

/* 响应式按钮布局 */
@media (max-width: 768px) {
    .button-row {
        flex-direction: column;
        gap: 15px;
    }
}
"""

# 创建Gradio界面
with gr.Blocks(css=custom_css, title="视频切割软件") as demo:
    with gr.Column(elem_classes="main-container"):
        # 标题区域
        gr.HTML('<h1 class="title">🎬 智能视频切割器</h1>')
        gr.HTML('<p class="subtitle">专业级视频切割工具 - 支持MP4格式，30fps输出</p>')
        
        # 状态指示器
        status_indicator = gr.HTML('''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: inline-block; background: rgba(0, 212, 255, 0.1); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 20px; padding: 10px 20px;">
                <span style="color: #00d4ff; font-weight: 600;">🚀 系统就绪</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 支持MP4格式</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 自动切割</span>
                <span style="color: #b8c6db; margin-left: 15px;">• 高质量输出</span>
            </div>
        </div>
        ''')
        
        # 主要操作区域
        with gr.Row():
            # 左侧：文件上传和控制按钮
            with gr.Column(scale=1, min_width=450):
                gr.HTML('<h3 class="section-title">📁 选择视频文件</h3>')
                video_input = gr.Video(
                    label="上传MP4视频文件",
                    elem_classes="upload-box",
                    height=140
                )
                
                # 按钮组
                gr.HTML('<div style="margin: 20px 0;"></div>')
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
            
            # 右侧：预览和信息显示
            with gr.Column(scale=1, min_width=450):
                gr.HTML('<h3 class="section-title">🖼️ 视频预览</h3>')
                preview_image = gr.Image(
                    label="视频预览",
                    elem_classes="preview-container",
                    height=220
                )
                
                gr.HTML('<h3 class="section-title" style="margin-top: 25px;">📊 视频信息</h3>')
                info_text = gr.Textbox(
                    label="视频详情",
                    elem_classes="info-box",
                    lines=8,
                    interactive=False
                )
        
        # 切割结果显示区域
        gr.HTML('<h3 class="result-title">📋 切割结果</h3>')
        result_text = gr.Textbox(
            label="处理结果",
            elem_classes="result-box",
            lines=15,
            interactive=False
        )
        
        # 绑定事件
        # 视频上传时自动更新状态
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
            inputs=[video_input],
            outputs=[result_text]
        )

# 启动应用
if __name__ == "__main__":
    try:
        demo.launch(
            server_name="127.0.0.1",  # 改为本地地址，避免网络问题
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False,
        )
    except Exception as e:
        print(f"启动失败: {e}")
        # 尝试使用备用端口
        try:
            demo.launch(
                server_name="127.0.0.1",
                server_port=7861,
                share=False,
                show_error=True,
                quiet=False,
            )
        except Exception as e2:
            print(f"备用端口也启动失败: {e2}")
            print("请检查端口是否被占用或尝试手动指定端口")
