import os
import redis
import json
import subprocess
import time
from rq import Worker, Queue
from app import app, redis_conn, transcribe_video_task, burn_subtitles_task

def export_video_task(job_id, export_id, video_path, captions, style, settings):
    """
    Professional video export with FFmpeg
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
        
        update_status("processing", 40, "Encoding video...")
        
        # Output path - use tmp directory in current working directory for Railway compatibility
        tmp_dir = os.path.join(os.getcwd(), 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        output_path = os.path.join(tmp_dir, f"{export_id}_final.mp4")
        print(f"Output path: {output_path}")
        
        # FFmpeg command - use simpler approach
        crf = {'standard': '23', 'high': '18', 'ultra': '15'}[quality]
        
        # Memory-optimized FFmpeg command for Railway
        # Limit threads to prevent OOM kills
        cmd = [
            'ffmpeg',
            '-y',
            '-threads', '2',  # Limit threads to prevent OOM
            '-i', video_path,
            '-vf', f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # Fastest preset = less memory
            '-crf', '28',  # Higher CRF = smaller file, less processing
            '-r', str(fps),
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',  # Lower audio bitrate
            '-movflags', '+faststart',
            output_path
        ]
        
        print(f"Starting FFmpeg export: {' '.join(cmd)}")
        update_status("processing", 60, "Encoding...")
        
        # First check video file with ffprobe
        print("Checking input video with ffprobe...")
        probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 
                     'default=noprint_wrappers=1:nokey=1', video_path]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        print(f"Video duration check: {probe_result.stdout.strip() if probe_result.returncode == 0 else 'FAILED'}")
        if probe_result.returncode != 0:
            print(f"ffprobe stderr: {probe_result.stderr}")
        
        # Try simpler approach - just copy the video first
        print("Attempting simple video copy to verify file is readable...")
        simple_cmd = ['ffmpeg', '-y', '-i', video_path, '-c', 'copy', '-f', 'null', '-']
        simple_result = subprocess.run(simple_cmd, capture_output=True, text=True, timeout=30)
        print(f"Simple copy test exit code: {simple_result.returncode}")
        if simple_result.returncode != 0:
            print(f"Simple copy stderr: {simple_result.stderr[-500:]}")
        
        # Run FFmpeg with real-time output - use stderr for progress
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout to capture everything
            universal_newlines=True,
            bufsize=1
        )
        
        # Capture output in real-time
        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            if len(output_lines) > 100:  # Keep last 100 lines
                output_lines.pop(0)
            print(f"FFmpeg: {line.strip()}")
        
        process.wait()
        
        print(f"FFmpeg exit code: {process.returncode}")
        
        if process.returncode != 0:
            full_output = ''.join(output_lines)
            print(f"FFmpeg failed. Full output:\n{full_output}")
            raise Exception(f"FFmpeg encoding failed. Check logs for details.")
        
        # Verify output file exists and has content
        if not os.path.exists(output_path):
            raise Exception("Output file was not created")
        
        file_size = os.path.getsize(output_path)
        print(f"Output file size: {file_size} bytes")
        
        if file_size < 1000:  # Less than 1KB is probably empty
            raise Exception(f"Output file is too small ({file_size} bytes)")
        
        # Verify it's a valid video by checking duration
        probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                     '-of', 'default=noprint_wrappers=1:nokey=1', output_path]
        probe_process = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        if probe_process.returncode == 0:
            duration = probe_process.stdout.strip()
            print(f"Output video duration: {duration}s")
        
        update_status("processing", 90, "Saving file...")
        
        # Ensure upload folder exists
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        print(f"Upload folder: {upload_folder}")
        
        # Move to uploads folder
        final_output = os.path.join(upload_folder, f"{export_id}.mp4")
        
        # Copy instead of rename to avoid cross-device issues
        import shutil
        shutil.copy2(output_path, final_output)
        os.remove(output_path)
        
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
