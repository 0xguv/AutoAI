import os
import redis
import json
import subprocess
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
        
        # FFmpeg command - simple and reliable
        crf = {'standard': '23', 'high': '18', 'ultra': '15'}[quality]
        
        cmd = [
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
        
        # Run FFmpeg
        update_status("processing", 60, "Encoding...")
        
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,
                universal_newlines=True
            )
            
            # Log the return code and stderr for debugging
            print(f"FFmpeg return code: {process.returncode}")
            if process.stderr:
                print(f"FFmpeg stderr (last 500 chars): {process.stderr[-500:]}")
            
            # Check if output file was created successfully
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"Output file created successfully: {output_path} ({os.path.getsize(output_path)} bytes)")
            else:
                raise Exception(f"Output file not created or empty. FFmpeg stderr: {process.stderr[-500:]}")
                
        except subprocess.TimeoutExpired:
            raise Exception("FFmpeg timeout - encoding took too long")
        
        update_status("processing", 90, "Saving file...")
        
        # Move to uploads folder for serving
        final_output = os.path.join(app.config['UPLOAD_FOLDER'], f"{export_id}.mp4")
        os.rename(output_path, final_output)
        
        # Verify file was moved
        if not os.path.exists(final_output):
            raise Exception("Failed to move output file to uploads folder")
        
        # Generate download URL
        download_url = f"/uploads/{export_id}.mp4"
        
        update_status("completed", 100, "Export complete!", download_url)
        
        return {"status": "success", "download_url": download_url}
        
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
