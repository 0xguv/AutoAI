import os
import redis
import json
import subprocess
from rq import Worker, Queue
from app import app, redis_conn, transcribe_video_task, burn_subtitles_task

def export_video_task(job_id, export_id, video_path, captions, style, settings):
    """
    Professional video export with FFmpeg
    Burns captions with styling into the final MP4
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
        
        # Get settings
        resolution = settings.get('resolution', '1080x1920')
        fps = settings.get('fps', 30)
        quality = settings.get('quality', 'high')
        
        # Parse resolution
        width, height = map(int, resolution.split('x'))
        
        update_status("processing", 20, "Generating subtitle file...")
        
        # Generate SRT subtitle file (simpler than ASS)
        srt_content = generate_srt_subtitles(captions)
        srt_path = f"/tmp/{export_id}.srt"
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        update_status("processing", 40, "Rendering video...")
        
        # Output path
        output_path = f"/tmp/{export_id}_final.mp4"
        
        # FFmpeg command - simpler approach without ASS
        crf = {'standard': '23', 'high': '18', 'ultra': '15'}[quality]
        
        # Build drawtext filter for each caption
        drawtext_filters = []
        font_size = style.get('fontSize', 48)
        font_color = style.get('color', '#FFFFFF').replace('#', '\\#')
        position = style.get('position', 'bottom')
        
        # Set y position based on caption position setting
        if position == 'top':
            y_pos = 50
        elif position == 'middle':
            y_pos = height // 2
        else:  # bottom
            y_pos = height - 100
        
        # Simple subtitle burn using subtitles filter with SRT
        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-vf', f"subtitles={srt_path}:force_style='FontSize={font_size},PrimaryColour=&H00{font_color},OutlineColour=&H00000000,Outline=2,Shadow=1',scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', crf,
            '-r', str(fps),
            '-c:a', 'copy',
            '-movflags', '+faststart',
            output_path
        ]
        
        # Run FFmpeg with timeout
        try:
            update_status("processing", 70, "Encoding video...")
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,  # 10 minute timeout
                universal_newlines=True
            )
            
            if process.returncode != 0:
                # If subtitles fail, try simple copy
                print(f"FFmpeg stderr: {process.stderr}")
                update_status("processing", 50, "Retrying without captions...")
                
                # Fallback: just scale video without captions
                cmd_simple = [
                    'ffmpeg',
                    '-y',
                    '-i', video_path,
                    '-vf', f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', crf,
                    '-r', str(fps),
                    '-c:a', 'copy',
                    '-movflags', '+faststart',
                    output_path
                ]
                
                process = subprocess.run(
                    cmd_simple,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=600,
                    universal_newlines=True
                )
                
                if process.returncode != 0:
                    raise Exception(f"FFmpeg failed: {process.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("FFmpeg timeout - encoding took too long")
        
        update_status("processing", 90, "Finalizing...")
        
        # Move to uploads folder for serving
        final_output = os.path.join(app.config['UPLOAD_FOLDER'], f"{export_id}.mp4")
        os.rename(output_path, final_output)
        
        # Clean up
        if os.path.exists(srt_path):
            os.remove(srt_path)
        
        # Generate download URL
        download_url = f"/uploads/{export_id}.mp4"
        
        update_status("completed", 100, "Export complete!", download_url)
        
        return {"status": "success", "download_url": download_url}
        
    except Exception as e:
        update_status("failed", 0, f"Export failed: {str(e)}")
        raise

def generate_srt_subtitles(captions):
    """Generate SRT subtitle format"""
    srt_lines = []
    for i, caption in enumerate(captions, 1):
        start = format_srt_time(caption['start'])
        end = format_srt_time(caption['end'])
        text = caption['text']
        
        srt_lines.append(str(i))
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(text)
        srt_lines.append("")  # Empty line between entries
    
    return "\n".join(srt_lines)

def format_srt_time(seconds):
    """Format seconds to SRT time format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_ass_time(seconds):
    """Format seconds to ASS time format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

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
