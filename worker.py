import os
import redis
import json
import subprocess
import time
from rq import Worker, Queue
from app import app, redis_conn, transcribe_video_task, burn_subtitles_task

def generate_ass_subtitles(captions, style, width, height):
    """
    Generate ASS subtitle content from captions with styling
    """
    # Extract style settings
    font_family = style.get('fontFamily', 'Inter')
    font_size = style.get('fontSize', 42)
    font_color = style.get('color', '#FFFFFF')
    bg_color = style.get('backgroundColor', 'transparent')
    stroke_color = style.get('strokeColor', '#000000')
    stroke_width = style.get('strokeWidth', 2)
    
    # Convert hex colors to ASS format (BGR)
    def hex_to_ass(hex_color):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"&H00{b:02X}{g:02X}{r:02X}"
    
    font_color_ass = hex_to_ass(font_color)
    stroke_color_ass = hex_to_ass(stroke_color)
    
    # Calculate vertical position (bottom center)
    margin_v = height - int(font_size * 3)
    
    ass_content = f"""[Script Info]
Title: AutoAI Export
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_family},{font_size},{font_color_ass},{font_color_ass},{stroke_color_ass},&H00000000,0,0,0,0,100,100,0,0,1,{stroke_width},0,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Convert seconds to ASS time format (H:MM:SS.cc)
    def seconds_to_ass(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"
    
    # Generate dialogue lines
    for caption in captions:
        start_time = seconds_to_ass(caption.get('start', 0))
        end_time = seconds_to_ass(caption.get('end', 0))
        text = caption.get('text', '')
        
        # Escape special ASS characters
        text = text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
        
        # Add karaoke-style word highlighting if words are present
        words = caption.get('words', [])
        if words:
            # Build text with word timing
            highlighted_text = ""
            for i, word in enumerate(words):
                word_text = word.get('text', '')
                word_start = word.get('start', 0)
                word_end = word.get('end', 0)
                duration = word_end - word_start
                
                # Escape special chars
                word_text = word_text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
                
                # Add karaoke tag (\k duration in centiseconds)
                duration_cs = int(duration * 100)
                highlighted_text += f"{{\\k{duration_cs}}}{word_text} "
            text = highlighted_text.strip()
        
        ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
    
    return ass_content

def export_video_task(job_id, export_id, video_path, captions, style, settings):
    """
    Professional video export with FFmpeg - ACTUALLY burns subtitles
    """
    from app import redis_conn
    
    def update_status(status, progress, message, download_url=None):
        status_data = {
            "export_id": export_id,
            "status": status,
            "progress": progress,
            "message": message
        }
        if download_url:
            status_data["download_url"] = download_url
        redis_conn.setex(f"export_status:{export_id}", 3600, json.dumps(status_data))
    
    try:
        update_status("processing", 10, "Preparing video...")
        
        print(f"Export task started: export_id={export_id}")
        print(f"Video path: {video_path}")
        print(f"Video exists: {os.path.exists(video_path)}")
        
        # Verify input video exists
        if not os.path.exists(video_path):
            raise Exception(f"Input video file not found: {video_path}")
        
        # Get settings
        resolution = settings.get('resolution', '1080x1920')
        fps = settings.get('fps', 30)
        quality = settings.get('quality', 'high')
        
        # Parse resolution
        width, height = map(int, resolution.split('x'))
        
        update_status("processing", 30, "Generating subtitles...")
        
        # Generate ASS subtitle file
        tmp_dir = os.path.join(os.getcwd(), 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        
        ass_content = generate_ass_subtitles(captions, style, width, height)
        ass_path = os.path.join(tmp_dir, f"{export_id}.ass")
        
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        print(f"Generated ASS file: {ass_path}")
        
        update_status("processing", 50, "Encoding video with subtitles...")
        
        # Output path
        output_path = os.path.join(tmp_dir, f"{export_id}_final.mp4")
        print(f"Output path: {output_path}")
        
        # Build video filter with subtitles
        # First scale/pad, then burn subtitles
        video_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,ass={ass_path}"
        
        # Memory-optimized FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',
            '-threads', '2',
            '-i', video_path,
            '-vf', video_filter,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '28',
            '-r', str(fps),
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            output_path
        ]
        
        print(f"Starting FFmpeg: {' '.join(cmd)}")
        
        # Run FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Capture output
        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            if len(output_lines) > 100:
                output_lines.pop(0)
            print(f"FFmpeg: {line.strip()}")
        
        process.wait()
        
        print(f"FFmpeg exit code: {process.returncode}")
        
        if process.returncode != 0:
            full_output = ''.join(output_lines)
            print(f"FFmpeg failed:\n{full_output}")
            raise Exception("FFmpeg encoding failed")
        
        # Verify output
        if not os.path.exists(output_path):
            raise Exception("Output file was not created")
        
        file_size = os.path.getsize(output_path)
        print(f"Output file size: {file_size} bytes")
        
        if file_size < 1000:
            raise Exception(f"Output file too small ({file_size} bytes)")
        
        update_status("processing", 90, "Saving file...")
        
        # Move to uploads folder
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        final_output = os.path.join(upload_folder, f"{export_id}.mp4")
        
        import shutil
        shutil.copy2(output_path, final_output)
        os.remove(output_path)
        os.remove(ass_path)  # Clean up subtitle file
        
        # Verify final file
        if not os.path.exists(final_output):
            raise Exception("Failed to save output file")
        
        final_size = os.path.getsize(final_output)
        print(f"Final file saved: {final_output} ({final_size} bytes)")
        
        # Generate download URL
        download_url = f"/uploads/{export_id}.mp4"
        
        update_status("completed", 100, "Export complete!", download_url)
        
        return {"status": "success", "download_url": download_url, "file_size": final_size}
        
    except Exception as e:
        error_msg = f"Export failed: {str(e)}"
        print(error_msg)
        update_status("failed", 0, error_msg)
        raise

# Preload Flask app context for db access within tasks
with app.app_context():
    if __name__ == '__main__':
        # Define the queue(s) to listen to
        queues = [
            Queue('default', connection=redis_conn),
            Queue('exports', connection=redis_conn)
        ]
        worker = Worker(queues, connection=redis_conn)
        worker.work()
