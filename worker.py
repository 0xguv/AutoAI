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
        
        # Generate ASS subtitle file with styling
        ass_content = generate_ass_subtitles(captions, style, width, height)
        ass_path = f"/tmp/{export_id}.ass"
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        update_status("processing", 40, "Rendering video...")
        
        # Output path
        output_path = f"/tmp/{export_id}_final.mp4"
        
        # FFmpeg command with professional encoding
        crf = {'standard': '23', 'high': '18', 'ultra': '15'}[quality]
        preset = 'medium'
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'ass={ass_path},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',
            '-c:v', 'libx264',
            '-preset', preset,
            '-crf', crf,
            '-r', str(fps),
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        # Run FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitor progress
        while process.poll() is None:
            update_status("processing", 70, "Encoding video...")
            import time
            time.sleep(2)
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg failed: {process.stderr.read()}")
        
        update_status("processing", 90, "Finalizing...")
        
        # Move to uploads folder for serving
        final_output = os.path.join(app.config['UPLOAD_FOLDER'], f"{export_id}.mp4")
        os.rename(output_path, final_output)
        
        # Clean up
        os.remove(ass_path)
        
        # Generate download URL
        from flask import url_for
        download_url = f"/uploads/{export_id}.mp4"
        
        update_status("completed", 100, "Export complete!", download_url)
        
        return {"status": "success", "download_url": download_url}
        
    except Exception as e:
        update_status("failed", 0, f"Export failed: {str(e)}")
        raise

def generate_ass_subtitles(captions, style, width, height):
    """Generate ASS subtitle format with advanced styling"""
    
    # Map style settings to ASS
    font_name = style.get('fontFamily', 'Arial')
    font_size = style.get('fontSize', 48)
    bold = 1 if style.get('fontWeight') in ['bold', '900'] else 0
    color = style.get('color', '#FFFFFF').replace('#', '')
    primary_color = f"&H00{color[4:6]}{color[2:4]}{color[0:2]}&"
    
    # Position based on setting
    margin_v = {
        'top': 50,
        'middle': height // 2,
        'bottom': height - 100
    }.get(style.get('position', 'bottom'), height - 100)
    
    # Animation style
    animation = style.get('animation', 'pop')
    
    ass_header = f"""[Script Info]
Title: AutoAI Generated Subtitles
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF&,&H00000000&,&H00000000&,{bold},0,0,0,100,100,0,0,1,2,0,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    ass_body = []
    for caption in captions:
        start = format_ass_time(caption['start'])
        end = format_ass_time(caption['end'])
        text = caption['text'].replace('\n', '\\N')
        
        # Add animation effects
        if animation == 'pop':
            text = f"{{\\fscx0\\fscy0\\t(0,200,\\fscx100\\fscy100)}}{text}"
        elif animation == 'fade':
            text = f"{{\\fade(0,255,255,0,200,0,0)}}{text}"
        
        ass_body.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    
    return ass_header + '\n'.join(ass_body)

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
