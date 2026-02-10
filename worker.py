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
        
        # Get settings
        resolution = settings.get('resolution', '1080x1920')
        fps = settings.get('fps', 30)
        quality = settings.get('quality', 'high')
        
        # Parse resolution
        width, height = map(int, resolution.split('x'))
        
        update_status("processing", 40, "Encoding video...")
        
        # Output path
        output_path = f"/tmp/{export_id}_final.mp4"
        
        # FFmpeg command - use simpler approach
        crf = {'standard': '23', 'high': '18', 'ultra': '15'}[quality]
        
        # First, let's just copy the video with proper scaling
        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-vf', f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', crf,
            '-r', str(fps),
            '-pix_fmt', 'yuv420p',  # Required for compatibility
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            output_path
        ]
        
        print(f"Starting FFmpeg export: {' '.join(cmd)}")
        update_status("processing", 60, "Encoding...")
        
        # Run FFmpeg with real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait for process to complete with timeout
        try:
            stdout, stderr = process.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("FFmpeg timeout after 10 minutes")
        
        print(f"FFmpeg exit code: {process.returncode}")
        
        if process.returncode != 0:
            error_msg = stderr[-1000:] if stderr else "Unknown error"
            print(f"FFmpeg failed: {error_msg}")
            raise Exception(f"FFmpeg encoding failed: {error_msg}")
        
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
        
        # Move to uploads folder
        final_output = os.path.join(app.config['UPLOAD_FOLDER'], f"{export_id}.mp4")
        
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
