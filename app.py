import os
import tempfile
import redis
from rq import Queue, Worker
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash, jsonify, make_response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from faster_whisper import WhisperModel
import logging
import subprocess
from datetime import datetime, date
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_should_be_in_env') # Needed for Flask-Login
# Database configuration - supports PostgreSQL (Railway) or SQLite (local)
database_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PUBLIC_URL')
if database_url and database_url.startswith('postgres://'):
    # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Configuration for generating external URLs correctly in production
app.config['SERVER_NAME'] = os.environ.get('FLASK_SERVER_NAME') # e.g., 'your-domain.railway.app'
app.config['PREFERRED_URL_SCHEME'] = os.environ.get('FLASK_PREFERRED_URL_SCHEME', 'https')

# Configure Redis Queue
app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

app.config['APPLE_CLIENT_ID'] = os.environ.get('APPLE_CLIENT_ID')
app.config['APPLE_CLIENT_SECRET'] = os.environ.get('APPLE_CLIENT_SECRET') # Apple requires a client secret generated from a .p8 key

app.config['DISCORD_CLIENT_ID'] = os.environ.get('DISCORD_CLIENT_ID')
app.config['DISCORD_CLIENT_SECRET'] = os.environ.get('DISCORD_CLIENT_SECRET')


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Specify the login view
login_manager.login_message_category = 'error' # Make login required messages appear as errors


# Initialize Authlib OAuth
from authlib.integrations.flask_client import OAuth
oauth = OAuth(app)

oauth.register(
    name='google',
    client_id=app.config.get('GOOGLE_CLIENT_ID'),
    client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Apple OAuth (more complex setup, often requires JWT for client_secret)
# This is a basic placeholder, actual Apple integration can be more involved
oauth.register(
    name='apple',
    client_id=app.config.get('APPLE_CLIENT_ID'),
    client_secret=app.config.get('APPLE_CLIENT_SECRET'), # This will likely need to be a dynamically generated JWT
    server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'name email'},
    # Apple uses a specific "response_mode=form_post" for auth code, may need customization
)

oauth.register(
    name='discord',
    client_id=app.config.get('DISCORD_CLIENT_ID'),
    client_secret=app.config.get('DISCORD_CLIENT_SECRET'),
    api_base_url='https://discord.com/api/',
    access_token_url='https://discord.com/api/oauth2/token',
    authorize_url='https://discord.com/api/oauth2/authorize',
    client_kwargs={'scope': 'identify email'}
)

# Initialize Redis and RQ queue
redis_conn = redis.from_url(app.config['REDIS_URL'])
q = Queue(connection=redis_conn)

# Define model storage directory within /tmp for Vercel
# Vercel's /tmp directory is cleared between invocations, but cached for cold starts
MODEL_DIR = os.path.join(tempfile.gettempdir(), "faster_whisper_models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Global variable to hold the model, loaded once
_faster_whisper_model = None

def load_faster_whisper_model(model_size="base", device="cpu", compute_type="int8"):
    global _faster_whisper_model
    if _faster_whisper_model is None:
        app.logger.info(f"Loading faster-whisper model '{model_size}' to {MODEL_DIR}...")
        _faster_whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type, download_root=MODEL_DIR)
        app.logger.info(f"Faster-whisper model '{model_size}' loaded successfully.")
    return _faster_whisper_model

# model = whisper.load_model("base") # REMOVE THIS LINE - model loaded via function


class User(UserMixin, db.Model):
    __tablename__ = 'user' # Explicitly define table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True) # Username is now nullable
    password_hash = db.Column(db.String(256), nullable=True) # Password can be null for OAuth users
    email = db.Column(db.String(120), unique=True, nullable=False) # Email is now required and unique for all users
    oauth_provider = db.Column(db.String(50), nullable=True)
    oauth_id = db.Column(db.String(256), nullable=True)
    is_subscribed = db.Column(db.Boolean, default=False)
    daily_tries_count = db.Column(db.Integer, default=0)
    last_try_date = db.Column(db.Date, default=date.min) # Store as date
    
    # Tiered limits
    max_duration_minutes = db.Column(db.Integer, default=1) # Default for unregistered/free
    max_daily_tries = db.Column(db.Integer, default=2) # Default for unregistered/free

    # Relationship for jobs
    processing_jobs = db.relationship('VideoProcessingJob', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_max_duration(self):
        return self.max_duration_minutes

    def get_max_daily_tries(self):
        return self.max_daily_tries

class VideoProcessingJob(db.Model):
    id = db.Column(db.String(36), primary_key=True) # Use RQ job_id as primary key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_video_filepath = db.Column(db.String(256), nullable=False)
    generated_srt_filepath = db.Column(db.String(256), nullable=True) # Nullable until transcription is done
    edited_srt_filepath = db.Column(db.String(256), nullable=True) # Path to user-edited SRT
    output_video_filepath = db.Column(db.String(256), nullable=True) # Path to final burned video
    original_filename = db.Column(db.String(256), nullable=False) # Original filename uploaded by user
    status = db.Column(db.String(50), default='pending') # pending, transcribed, editing, burning, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolution = db.Column(db.String(20), nullable=True) # Store selected resolution
    language = db.Column(db.String(10), nullable=True) # Store selected language
    subtitle_pos_x = db.Column(db.Float, default=50.0) # Subtitle X position (percentage)
    subtitle_pos_y = db.Column(db.Float, default=15.0) # Subtitle Y position (percentage)
    word_level_captions_json = db.Column(db.Text, nullable=True) # Store word-level captions as JSON

    def __repr__(self):
        return f"<VideoProcessingJob {self.id} - {self.status}>"



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    videos_processed = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref=db.backref('usage_logs', lazy=True))

    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

    def __repr__(self):
        return f'<UsageLog {self.user.username} {self.date} - {self.videos_processed} videos>'


def seconds_to_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int((seconds % 60) // 1)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def transcribe_video_task(user_id, original_filepath, filename, language, user_max_duration):
    from rq import get_current_job
    from app import app, db, User, UsageLog, seconds_to_srt_time, load_faster_whisper_model, get_video_duration, MODEL_DIR, os, subprocess, logging, date, tempfile
    
    with app.app_context():
        current_job_id = get_current_job().id
        user = User.query.get(user_id)
        if not user:
            app.logger.error(f"User with ID {user_id} not found for transcription job {current_job_id}")
            return {"status": "failed", "error": "User not found"}

        app.logger.info(f"Starting video transcription for job {current_job_id}, user {user_id}, file {filename}")
        
        try:
            video_duration = get_video_duration(original_filepath)
            if video_duration is None:
                app.logger.error(f"Could not determine video duration for transcription job {current_job_id}. Skipping processing.")
                return {"status": "failed", "error": "Could not determine video duration. Is ffprobe installed?"}

            if video_duration > user_max_duration * 60:
                app.logger.error(f"Video duration ({video_duration / 60:.1f} min) exceeds limit of {user_max_duration} minutes for transcription job {current_job_id}. Skipping processing.")
                return {"status": "failed", "error": f"Video duration ({video_duration / 60:.1f} min) exceeds your limit of {user_max_duration} minutes."}
            
            audio_filename_base = os.path.splitext(filename)[0]
            # Use a temporary directory for audio extraction
            temp_dir = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])
            audio_filepath = os.path.join(temp_dir, f"{audio_filename_base}.mp3")

            ffmpeg_audio_command = ["ffmpeg", "-i", original_filepath, "-y", audio_filepath]
            app.logger.info(f"Running FFmpeg audio extraction for job {current_job_id}: {' '.join(ffmpeg_audio_command)}")
            subprocess.run(ffmpeg_audio_command, check=True, capture_output=True)

            model_ft = load_faster_whisper_model()
            segments, info = model_ft.transcribe(
                audio_filepath, 
                beam_size=5, 
                language=language if language else None,
                word_timestamps=True # Enable word-level timestamps
            )
            
            # Process segments to extract word-level data
            word_level_captions = []
            for i, segment in enumerate(segments):
                segment_words = []
                # Ensure segment.words is iterable
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        segment_words.append({
                            "text": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": getattr(word, 'probability', 0.0) # Confidence score, default to 0.0 if not present
                        })
                
                word_level_captions.append({
                    "id": f"segment_{i+1}", # Unique ID for each segment
                    "text": segment.text.strip(),
                    "start": segment.start,
                    "end": segment.end,
                    "words": segment_words
                })
            
            # Save word-level data as JSON in the database
            job_entry = VideoProcessingJob.query.get(current_job_id)
            if job_entry:
                job_entry.word_level_captions_json = json.dumps(word_level_captions)
                # The generated_srt_filepath is no longer directly used for content storage
                # but might be referenced elsewhere. Point it to a placeholder.
                job_entry.generated_srt_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{current_job_id}_word_level_data.json")
                job_entry.status = 'transcribed'
                db.session.commit()
            else:
                app.logger.error(f"VideoProcessingJob with ID {current_job_id} not found after transcription.")
            
            # Clean up audio file and temp directory
            os.remove(audio_filepath)
            os.rmdir(temp_dir)

            return {
                "status": "transcribed",
                "original_video_filepath": original_filepath,
                "word_level_captions": word_level_captions
            }

            return {
                "status": "transcribed",
                "original_video_filepath": original_filepath,
                "generated_srt_filepath": srt_filepath
            }

        except subprocess.CalledProcessError as e:
            # Update job status to failed
            job_entry = VideoProcessingJob.query.get(current_job_id)
            if job_entry:
                job_entry.status = 'failed'
                db.session.commit()
            app.logger.error(f"FFmpeg command failed for transcription job {current_job_id} with exit code {e.returncode}")
            app.logger.error(f"FFmpeg stdout: {e.stdout.decode(errors='ignore')}")
            app.logger.error(f"FFmpeg stderr: {e.stderr.decode(errors='ignore')}")
            return {"status": "failed", "error": f"FFmpeg audio extraction error: {e.stderr.decode(errors='ignore')}"}
        except Exception as e:
            # Update job status to failed
            job_entry = VideoProcessingJob.query.get(current_job_id)
            if job_entry:
                job_entry.status = 'failed'
                db.session.commit()
            app.logger.error(f"An unexpected error occurred for transcription job {current_job_id}: {e}")
            return {"status": "failed", "error": f"An unexpected error occurred during transcription: {e}"}


@app.cli.command("init-db")
def init_db_command():
    """Drops and creates the database tables."""
    with app.app_context():
        db.drop_all()
        db.create_all()
    print("Dropped and initialized the database.")

@app.route('/')
def index():
    message = request.args.get('message')
    return render_template('index.html', message=message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required!', 'error')
            return redirect(url_for('register'))
        
        # Basic email validation (can be more robust with regex)
        if '@' not in email or '.' not in email:
            flash('Invalid email address!', 'error')
            return redirect(url_for('register'))

        # Password validation
        if len(password) < 5:
            flash('Password must be at least 5 characters long!', 'error')
            return redirect(url_for('register'))
        if len(password) > 10:
            flash('Password cannot exceed 10 characters!', 'error')
            return redirect(url_for('register'))
        if not any(char.isdigit() for char in password):
            flash('Password must contain at least one number!', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return redirect(url_for('register'))
        
        # Generate a username from email, or leave it null.
        # For simplicity, let's set username to be the part before '@' in email.
        # This can be made more sophisticated later if usernames are still desired.
        username_from_email = email.split('@')[0]
        
        new_user = User(email=email, username=username_from_email, max_duration_minutes=5, max_daily_tries=5)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user) # Log in the user immediately after registration
        return redirect(url_for('index', message='Registration successful! Welcome!')) # Redirect to index with message
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first() # Find user by email
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index', message='Success! Logged in successfully!'))
        else:
            flash('Invalid email or password.', 'error') # Update flash message
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        flash('If an account with that email exists, you will receive a password reset link.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')



# Helper function to find or create a user from OAuth data
def create_or_login_oauth_user(oauth_provider, oauth_id, email, username):
    user = User.query.filter_by(oauth_provider=oauth_provider, oauth_id=oauth_id).first()
    if user:
        login_user(user)
        return True

    # Try to link by email if user exists with this email but not this OAuth provider
    if email:
        existing_user_by_email = User.query.filter_by(email=email).first()
        if existing_user_by_email:
            # Link existing account
            existing_user_by_email.oauth_provider = oauth_provider
            existing_user_by_email.oauth_id = oauth_id
            db.session.commit()
            login_user(existing_user_by_email)
            return True

    # Create new user
    # Generate a unique username from email if OAuth provider doesn't provide one
    if not username and email:
        base_username = email.split('@')[0]
    elif not username: # Fallback if neither username nor email is present
        base_username = "oauth_user"
    else:
        base_username = username
        
    generated_username = base_username
    counter = 1
    # Ensure generated_username is unique (only if username is still unique=True)
    # The User model is still unique=True for username, so keep this check.
    while User.query.filter_by(username=generated_username).first():
        generated_username = f"{base_username}{counter}"
        counter += 1
    
    new_user = User(
        username=generated_username, # Use generated_username
        email=email,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
        max_duration_minutes=5, # Default limits for new users
        max_daily_tries=5
    )
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return True

# OAuth login routes
@app.route('/login/<name>')
def oauth_login(name):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    client = oauth.create_client(name)
    if not client:
        flash(f'OAuth client "{name}" not configured.', 'error')
        return redirect(url_for('login'))
    
    redirect_uri = url_for(f'auth_{name}_callback', _external=True)
    return client.authorize_redirect(redirect_uri)

# Google OAuth Callback
@app.route('/auth/google/callback')
def auth_google_callback():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token)
        
        email = user_info.get('email')
        username = user_info.get('name') # Google provides 'name'
        oauth_id = user_info.get('sub') # Google's unique user ID
        
        if create_or_login_oauth_user('google', oauth_id, email, username):
            flash('Successfully logged in with Google!', 'success')
            return redirect(url_for('index'))
        
        flash('Could not log in with Google.', 'error')
        return redirect(url_for('login'))
    except Exception as e:
        flash(f'Google login failed: {e}', 'error')
        app.logger.error(f"Google OAuth error: {e}")
        return redirect(url_for('login'))

# Discord OAuth Callback
@app.route('/auth/discord/callback')
def auth_discord_callback():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    try:
        token = oauth.discord.authorize_access_token()
        # Discord returns user info directly in the token response if scope 'identify' is used
        user_info = oauth.discord.get('users/@me').json()
        
        email = user_info.get('email')
        username = user_info.get('username') # Discord provides 'username'
        oauth_id = user_info.get('id') # Discord's unique user ID

        if create_or_login_oauth_user('discord', oauth_id, email, username):
            flash('Successfully logged in with Discord!', 'success')
            return redirect(url_for('index'))

        flash('Could not log in with Discord.', 'error')
        return redirect(url_for('login'))
    except Exception as e:
        flash(f'Discord login failed: {e}', 'error')
        app.logger.error(f"Discord OAuth error: {e}")
        return redirect(url_for('login'))

# Apple OAuth Callback (Note: Apple requires POST for authorization code exchange)
@app.route('/auth/apple/callback', methods=['GET', 'POST'])
def auth_apple_callback():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Apple often sends the authorization code as a form post parameter
            # Authlib handles this with authorize_access_token which expects GET params,
            # but if it's a POST, we need to extract the 'code' and 'id_token' manually if Authlib doesn't handle it
            # For simplicity, Authlib's authorize_access_token should still work if it can read POST body.
            token = oauth.apple.authorize_access_token()
            user_info = oauth.apple.parse_id_token(token)

            email = user_info.get('email')
            # Apple might not provide a 'name' directly, can construct from 'given_name'/'family_name' or use email part
            username = user_info.get('email', '').split('@')[0] 
            oauth_id = user_info.get('sub') # Apple's unique user ID

            if create_or_login_oauth_user('apple', oauth_id, email, username):
                flash('Successfully logged in with Apple!', 'success')
                return redirect(url_for('index'))
            
            flash('Could not log in with Apple.', 'error')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Apple login failed: {e}', 'error')
            app.logger.error(f"Apple OAuth error: {e}")
            return redirect(url_for('login'))
    else: # GET request, usually for errors or initial redirect if not form_post
        flash('Apple login requires POST callback, please try again.', 'error')
        return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index', message="Info! You have been logged out."))

@app.route('/upgrade')
@login_required
def upgrade():
    # Placeholder for subscription logic - disabled for now
    # In a real app, this would integrate with a payment gateway
    # current_user.is_subscribed = True
    # current_user.max_duration_minutes = 60 # 1 hour
    # current_user.max_daily_tries = -1 # Unlimited
    # db.session.commit()
    return redirect(url_for('index', message="Info! Upgrade feature coming soon!"))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/api/user_usage')
@login_required
def user_usage_data():
    # Fetch usage data for the current user
    # Order by date to ensure correct plotting
    usage_data = UsageLog.query.filter_by(user_id=current_user.id).order_by(UsageLog.date).all()

    dates = [log.date.strftime('%Y-%m-%d') for log in usage_data]
    videos_processed = [log.videos_processed for log in usage_data]

    return jsonify({
        'dates': dates,
        'videos_processed': videos_processed
    })

# Define a function to encapsulate the video processing logic
# This function will be enqueued by RQ
def burn_subtitles_task(original_job_id, user_id, original_video_filepath, srt_filepath, filename_for_output, resolution):
    from rq import get_current_job
    from app import app, db, User, UsageLog, VideoProcessingJob, seconds_to_srt_time, load_faster_whisper_model, get_video_duration, MODEL_DIR, os, subprocess, logging, date, re
    
    with app.app_context():
        current_rq_job_id = get_current_job().id
        user = User.query.get(user_id)
        job_entry = VideoProcessingJob.query.get(original_job_id)
        
        if not user:
            app.logger.error(f"User with ID {user_id} not found for burning job {original_job_id}")
            return {"status": "failed", "error": "User not found"}

        app.logger.info(f"Starting video burning with Hormozi-style subtitles for original job {original_job_id}, user {user_id}, file {filename_for_output}")
        
        try:
            # Check if original video file still exists
            if not os.path.exists(original_video_filepath):
                app.logger.error(f"Original video file not found for burning job {original_job_id}: {original_video_filepath}")
                if job_entry:
                    job_entry.status = 'failed'
                    db.session.commit()
                if os.path.exists(srt_filepath):
                    os.remove(srt_filepath)
                return {"status": "failed", "error": "Original video file not found. It might have been deleted or moved."}
            
            # Check if SRT file exists
            if not os.path.exists(srt_filepath):
                app.logger.error(f"SRT file not found for burning job {original_job_id}: {srt_filepath}")
                if job_entry:
                    job_entry.status = 'failed'
                    db.session.commit()
                if os.path.exists(original_video_filepath):
                    os.remove(original_video_filepath)
                return {"status": "failed", "error": "SRT file not found. It might have been deleted or moved."}

            output_video_filename = f"subtitled_{filename_for_output}"
            output_video_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_video_filename)
            
            # Get video dimensions using ffprobe
            try:
                ffprobe_cmd = [
                    'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0',
                    original_video_filepath
                ]
                result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
                video_width, video_height = map(int, result.stdout.strip().split('x'))
                app.logger.info(f"Video dimensions: {video_width}x{video_height}")
            except Exception as e:
                app.logger.warning(f"Could not get video dimensions: {e}, using defaults")
                video_width, video_height = 1080, 1920
            
            # Get subtitle position from database (as percentages)
            subtitle_x_pct = job_entry.subtitle_pos_x if job_entry else 50.0
            subtitle_y_pct = job_entry.subtitle_pos_y if job_entry else 15.0
            
            # Parse SRT file to get word-level timing
            def parse_srt(srt_content):
                captions = []
                blocks = re.split(r'\n\n+', srt_content.strip())
                
                for block in blocks:
                    lines = block.strip().split('\n')
                    if len(lines) >= 3:
                        time_line = lines[1]
                        time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', time_line)
                        if time_match:
                            start_time = time_match.group(1)
                            end_time = time_match.group(2)
                            text = ' '.join(lines[2:])
                            captions.append({
                                'start': start_time,
                                'end': end_time,
                                'text': text
                            })
                return captions
            
            def srt_time_to_seconds(srt_time):
                """Convert SRT time format to seconds"""
                hours, minutes, seconds_millis = srt_time.split(':')
                seconds, millis = seconds_millis.split(',')
                return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000
            
            # Read SRT file
            with open(srt_filepath, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            captions = parse_srt(srt_content)
            app.logger.info(f"Parsed {len(captions)} captions from SRT")
            
            # Build word timestamps with variable timing
            word_timestamps = []
            
            for caption in captions:
                words = caption['text'].split()
                if not words:
                    continue
                
                start_sec = srt_time_to_seconds(caption['start'])
                end_sec = srt_time_to_seconds(caption['end'])
                duration = end_sec - start_sec
                
                # Calculate word weights based on length
                word_weights = [max(1, len(word) * 0.5) for word in words]
                total_weight = sum(word_weights)
                
                current_time = start_sec
                
                for i, word in enumerate(words):
                    word_duration = (word_weights[i] / total_weight) * duration
                    word_start = current_time
                    word_end = current_time + word_duration
                    current_time = word_end
                    
                    word_timestamps.append({
                        'word': word,
                        'start': word_start,
                        'end': word_end
                    })
            
            # Build filters - Clear-and-Draw with phrase visibility
            # Strategy: Show phrase of 3-4 words, highlight active word by showing it alone with box
            max_words_per_phrase = 3
            filter_parts = []
            
            # Group words into phrases
            phrases = []
            for i in range(0, len(word_timestamps), max_words_per_phrase):
                phrase = word_timestamps[i:i + max_words_per_phrase]
                phrases.append(phrase)
            
            # Limit to avoid complexity
            phrases = phrases[:20]
            
            for phrase in phrases:
                if not phrase:
                    continue
                
                phrase_start = phrase[0]['start']
                phrase_end = phrase[-1]['end']
                
                # Build full phrase text
                full_text = ' '.join([w['word'] for w in phrase])
                escaped_full = full_text.replace('\\', '\\\\').replace("'", "'\''").replace(':', '\\:')
                
                # For each word in the phrase, create TWO states:
                # 1. SHOW PHRASE: Show all words in white during inactive time
                # 2. HIGHLIGHT: Show only active word with red box during its time
                
                for idx, word_data in enumerate(phrase):
                    word = word_data['word']
                    word_start = word_data['start']
                    word_end = word_data['end']
                    
                    escaped_word = word.replace('\\', '\\\\').replace("'", "'\''").replace(':', '\\:')
                    
                    # STATE 1: Show full phrase in white (NO red box) during this word's time
                    # This shows context of all words
                    phrase_filter = (
                        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                        f"text='{escaped_full}':"
                        f"fontcolor=white:"
                        f"fontsize={int(video_width * 0.07)}:"
                        f"x=(w-text_w)/2:"
                        f"y=h*{(100 - subtitle_y_pct) / 100}:"
                        f"enable=between(t\\,{word_start:.3f}\\,{word_end:.3f})"
                    )
                    filter_parts.append(phrase_filter)
                    
                    # STATE 2: Show ONLY the active word with red box (drawn ON TOP)
                    # This creates the highlight effect
                    highlight_filter = (
                        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                        f"text='{escaped_word}':"
                        f"fontcolor=white:"
                        f"fontsize={int(video_width * 0.07)}:"
                        f"box=1:"
                        f"boxcolor=red@0.95:"
                        f"boxborderw=10:"
                        f"x=(w-text_w)/2:"
                        f"y=h*{(100 - subtitle_y_pct) / 100}:"
                        f"enable=between(t\\,{word_start:.3f}\\,{word_end:.3f})"
                    )
                    filter_parts.append(highlight_filter)
            
            app.logger.info(f"Created {len(filter_parts)} filters for {len(phrases)} phrases")
            app.logger.info(f"Position: x={subtitle_x_pct}%, y={subtitle_y_pct}% from bottom")
            
            # Build FFmpeg command with filter_complex for proper layering
            vf_string = ','.join(filter_parts)
            
            if resolution != 'original':
                width, height = resolution.split('x')
                vf_string += f",scale={width}x{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            
            ffmpeg_burn_command = [
                "ffmpeg",
                "-i", original_video_filepath,
                "-y",
                "-vf", vf_string,
                "-preset", "ultrafast",
                "-threads", "2",
                output_video_filepath
            ]
            
            app.logger.info(f"Running FFmpeg burn command for job {original_job_id}")
            
            result = subprocess.run(
                ffmpeg_burn_command,
                check=True,
                capture_output=True
            )
            
            app.logger.info(f"FFmpeg completed successfully for job {original_job_id}")

            # Clean up original uploaded file and SRT file after processing
            if os.path.exists(original_video_filepath):
                os.remove(original_video_filepath)
            if os.path.exists(srt_filepath):
                os.remove(srt_filepath)

            # Record usage in UsageLog
            today = date.today()
            usage_log = UsageLog.query.filter_by(user_id=user.id, date=today).first()
            if usage_log:
                usage_log.videos_processed += 1
            else:
                usage_log = UsageLog(user_id=user.id, date=today, videos_processed=1)
                db.session.add(usage_log)
            db.session.commit()

            # Increment daily tries count for the user only on successful completion
            if user.max_daily_tries != -1: # Only for users with limited tries
                user.daily_tries_count += 1
                user.last_try_date = date.today() # Update last_try_date to today for this successful try
                db.session.commit()

            video_download_url = f"/download/{output_video_filename}"
            
            # Update the VideoProcessingJob entry using original_job_id
            job_entry = VideoProcessingJob.query.get(original_job_id)
            if job_entry:
                job_entry.output_video_filepath = output_video_filepath
                job_entry.status = 'completed'
                db.session.commit()
                app.logger.info(f"Job {original_job_id} marked as completed")
            else:
                app.logger.error(f"VideoProcessingJob with ID {original_job_id} not found after burning.")

            return {
                "status": "completed",
                "video_url": video_download_url
            }

        except subprocess.CalledProcessError as e:
            # Update job status to failed
            job_entry = VideoProcessingJob.query.get(original_job_id)
            if job_entry:
                job_entry.status = 'failed'
                db.session.commit()
            app.logger.error(f"FFmpeg command failed for burning job {original_job_id} with exit code {e.returncode}")
            app.logger.error(f"FFmpeg stdout: {e.stdout.decode(errors='ignore')}")
            app.logger.error(f"FFmpeg stderr: {e.stderr.decode(errors='ignore')}")
            # Clean up original video and srt if burning failed
            if os.path.exists(original_video_filepath):
                os.remove(original_video_filepath)
            if os.path.exists(srt_filepath):
                os.remove(srt_filepath)
            return {"status": "failed", "error": f"FFmpeg burning error: {e.stderr.decode(errors='ignore')}"}
        except Exception as e:
            # Update job status to failed
            job_entry = VideoProcessingJob.query.get(original_job_id)
            if job_entry:
                job_entry.status = 'failed'
                db.session.commit()
            app.logger.error(f"An unexpected error occurred for burning job {original_job_id}: {e}")
            # Clean up original video and srt if burning failed
            if os.path.exists(original_video_filepath):
                os.remove(original_video_filepath)
            if os.path.exists(srt_filepath):
                os.remove(srt_filepath)
            return {"status": "failed", "error": f"An unexpected error occurred during burning: {e}"}


def get_video_duration(filepath):
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        app.logger.error(f"FFprobe failed: {e.stderr}")
        return None
    except Exception as e:
        app.logger.error(f"Error getting video duration: {e}")
        return None

@app.route('/upload', methods=['POST'])
@login_required # This decorator requires user to be logged in to upload
def upload_file():
    # Determine user limits
    user_max_duration = current_user.get_max_duration()
    user_max_tries = current_user.get_max_daily_tries()
    
    # Reset daily tries if date changed
    if current_user.last_try_date != date.today():
        current_user.daily_tries_count = 0
        current_user.last_try_date = date.today()
        db.session.commit()

    if user_max_tries != -1 and current_user.daily_tries_count >= user_max_tries:
        return jsonify({"status": "error", "message": f"Daily upload limit reached ({user_max_tries}). Upgrade or try again tomorrow."}), 403

    if 'video_file' not in request.files:
        return redirect(url_for('index', message="Error: No file part in the request."))
    file = request.files['video_file']
    if file.filename == '':
        return redirect(url_for('index', message="Error: No selected file."))
    if file:
        filename = secure_filename(file.filename)
        # Generate a unique filename to avoid conflicts and store temporarily
        unique_filename = f"{os.urandom(16).hex()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Extract resolution from form
        resolution = request.form.get('resolution', 'original')
        language = request.form.get('language', None) # New: Get language from form

        try:
            # ==> DIAGNOSTIC LOGGING <==
            upload_folder = app.config['UPLOAD_FOLDER']
            app.logger.info(f"Attempting to save file to: {filepath}")
            app.logger.info(f"Upload folder is: {upload_folder}")
            if not os.path.isdir(upload_folder):
                app.logger.error(f"Upload folder '{upload_folder}' does not exist or is not a directory.")
            else:
                app.logger.info(f"Upload folder '{upload_folder}' exists.")
            
            file.save(filepath)

            # ==> DIAGNOSTIC LOGGING <==
            if os.path.exists(filepath):
                app.logger.info(f"SUCCESS: File saved and found at {filepath}")
            else:
                app.logger.error(f"FAILURE: File not found at {filepath} immediately after save.")


            # Enqueue the video processing task
            job = q.enqueue(
                'app.transcribe_video_task', # Enqueue the new transcription task
                current_user.id,
                filepath,
                filename, # Pass original filename for output naming
                language,
                user_max_duration,
                job_timeout='1h' # Allow up to 1 hour for video processing
            )
            app.logger.info(f"Video transcription task enqueued with job ID: {job.id}")

            # Create a new VideoProcessingJob entry
            new_job_entry = VideoProcessingJob(
                id=job.id,
                user_id=current_user.id,
                original_video_filepath=filepath,
                original_filename=filename,
                status='pending',
                resolution=resolution, # Store resolution from upload form
                language=language # Store language from upload form
            )
            db.session.add(new_job_entry)
            db.session.commit()

            return jsonify({"status": "success", "job_id": job.id})

        except Exception as e:
            app.logger.error(f"An error occurred during file upload or enqueue: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/job_status/<job_id>')
@login_required
def job_status(job_id):
    job_entry = VideoProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()

    if not job_entry:
        return jsonify({"status": "error", "message": "Job not found or unauthorized access."}), 404

    # Fetch real-time status from RQ for jobs that are still processing
    rq_job = q.fetch_job(job_id)
    rq_status = rq_job.get_status() if rq_job else 'unknown' # Get status from RQ, fallback to unknown

    # Prefer DB status for 'transcribed', 'burning', 'completed', 'failed' states
    # Use RQ status for 'queued', 'started', 'deferred'
    if job_entry.status in ['transcribed', 'burning', 'completed', 'failed', 'editing']:
        status_to_report = job_entry.status
    else:
        status_to_report = rq_status


    if status_to_report == 'transcribed':
        return jsonify({
            "status": "transcribed",
            "progress_message": "Transcription completed. Redirecting to editor.",
            "redirect_url": url_for('edit_video', job_id=job_id)
        })
    elif status_to_report == 'completed':
        if job_entry.output_video_filepath and os.path.exists(job_entry.output_video_filepath):
            return jsonify({
                "status": "completed",
                "result": {"video_url": url_for('download_file', filename=os.path.basename(job_entry.output_video_filepath))},
                "progress_message": "Video processing completed successfully."
            })
        else:
            return jsonify({
                "status": "failed",
                "error": "Completed job, but output video file not found.",
                "progress_message": "Processing failed."
            })
    elif status_to_report == 'failed':
        # Retrieve error info from RQ job if available, otherwise rely on DB status
        error_message = job_entry.status_message if hasattr(job_entry, 'status_message') else "Processing failed." # Assuming status_message field if added
        if rq_job and rq_job.is_failed:
             error_message = str(rq_job.exc_info)
        return jsonify({
            "status": "failed",
            "error": error_message,
            "progress_message": "Processing failed."
        })
    else: # pending, started, deferred, unknown, etc.
        return jsonify({
            "status": status_to_report,
            "progress_message": f"Job is currently {status_to_report}."
        })

@app.route('/api/editor_data/<job_id>')
@login_required
def get_editor_data(job_id):
    job_entry = VideoProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()

    if not job_entry:
        return jsonify({"status": "error", "message": "Job not found or unauthorized."}), 404

    if job_entry.status not in ['transcribed', 'editing']:
        return jsonify({"status": "error", "message": f"Video is not ready for editing (current status: {job_entry.status})."}), 400

    video_url = url_for('download_file', filename=os.path.basename(job_entry.original_video_filepath))
    app.logger.info(f"Generated video_url for job {job_id}: {video_url}")
    
    # Now we fetch word-level captions directly from the DB
    word_level_captions = []
    if job_entry.word_level_captions_json:
        try:
            word_level_captions = json.loads(job_entry.word_level_captions_json)
        except json.JSONDecodeError:
            app.logger.error(f"Failed to decode word_level_captions_json for job {job_id}")
            return jsonify({"status": "error", "message": "Failed to load word-level captions."}), 500
    else:
        app.logger.warning(f"No word_level_captions_json for job {job_id}. This should not happen in new flow.")
        # If no word-level data, try to fall back to old SRT if it exists and parse it.
        # For now, we assume word_level_captions_json will always be present for new jobs.
        return jsonify({"status": "error", "message": "Word-level captions not available."}), 404

    job_entry.status = 'editing' # Update status to indicate it's being edited
    db.session.commit()

    return jsonify({
        "status": "success",
        "job_id": job_id,
        "video_url": video_url,
        "captions": word_level_captions, # New: directly provide parsed captions
        "original_filename": job_entry.original_filename,
        "resolution": job_entry.resolution,
        "language": job_entry.language
    })

@app.route('/edit/<job_id>')
@login_required
def edit_video(job_id):
    job_entry = VideoProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()

    if not job_entry:
        flash('Job not found or unauthorized.', 'error')
        return redirect(url_for('index'))

    if job_entry.status != 'transcribed' and job_entry.status != 'editing': # Allow re-editing
        flash(f'Video is not ready for editing (current status: {job_entry.status}).', 'error')
        return redirect(url_for('index'))

    video_url = url_for('download_file', filename=os.path.basename(job_entry.original_video_filepath))
    srt_url = url_for('download_file', filename=os.path.basename(job_entry.generated_srt_filepath))
    
    # Read SRT content directly to pass to the template for initial display
    srt_content = ""
    try:
        with open(job_entry.generated_srt_filepath, "r", encoding="utf-8") as f:
            srt_content = f.read()
    except FileNotFoundError:
        flash('Generated SRT file not found.', 'error')
        return redirect(url_for('index'))

    job_entry.status = 'editing' # Update status to indicate it's being edited
    db.session.commit()

    response = make_response(send_from_directory('static/dist', 'index.html'))
    response.headers['Content-Security-Policy'] = "script-src 'self' 'unsafe-eval' https://cdn.tailwindcss.com; object-src 'none'; base-uri 'self';"
    return response

@app.route('/api/queue_stats')
def queue_stats():
    # Get queued jobs
    queued_jobs = q.count
    # Get active jobs (jobs currently being worked on by a worker)
    started_jobs = q.started_job_registry.count
    # Get total workers by querying RQ
    total_workers = len(Worker.all(connection=redis_conn))
    
    return jsonify({
        'queued_jobs': queued_jobs,
        'started_jobs': started_jobs,
        'total_workers': total_workers
    })

@app.route('/save_and_burn', methods=['POST'])
@login_required
def save_and_burn():
    data = request.get_json()
    job_id = data.get('job_id')
    srt_content = data.get('srt_content')
    positional_data = data.get('positional_data') # Not directly used for burning, but good to store if needed later
    resolution = data.get('resolution')
    # language = data.get('language') # Language is already stored in VideoProcessingJob or passed to transcribe_video_task

    if not all([job_id, srt_content, resolution]):
        return jsonify({"status": "error", "message": "Missing required data."}), 400

    job_entry = VideoProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()

    if not job_entry:
        return jsonify({"status": "error", "message": "Job not found or unauthorized."}), 404
    
    # Ensure the job is in a state that allows saving/burning
    if job_entry.status not in ['transcribed', 'editing']:
        return jsonify({"status": "error", "message": f"Job is not in a state to be edited or burned ({job_entry.status})."}), 400

    try:
        # Overwrite the generated SRT file with the edited content
        edited_srt_filepath = job_entry.generated_srt_filepath # Use the same file for now
        with open(edited_srt_filepath, "w", encoding="utf-8") as f:
            f.write(srt_content)
        
        # Store subtitle position if provided
        if positional_data:
            job_entry.subtitle_pos_x = positional_data.get('x', 50.0)
            job_entry.subtitle_pos_y = positional_data.get('y', 15.0)
        
        job_entry.edited_srt_filepath = edited_srt_filepath # Point to the edited SRT (which is the same file)
        job_entry.status = 'burning'
        db.session.commit()

        # Enqueue the burn_subtitles_task - pass the original job_id to update the correct entry
        burn_job = q.enqueue(
            'app.burn_subtitles_task',
            job_id,  # Original VideoProcessingJob ID
            current_user.id,
            job_entry.original_video_filepath,
            edited_srt_filepath,
            job_entry.original_filename, # Pass original filename for output naming
            resolution,
            job_timeout='1h'
        )
        app.logger.info(f"Burn subtitles task enqueued with job ID: {burn_job.id} for original job {job_id}")

        return jsonify({"status": "success", "job_id": job_id, "message": "Subtitles saved and burning process started."})

    except Exception as e:
        app.logger.error(f"Error saving edited SRT and enqueuing burn task for job {job_id}: {e}")
        job_entry.status = 'failed'
        db.session.commit()
        return jsonify({"status": "error", "message": f"Failed to save and burn subtitles: {e}"}), 500

@app.after_request
def add_csp_header(response):
    # CSP policy allowing necessary CDN resources
    csp = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data:; media-src 'self'; object-src 'none'; base-uri 'self';"
    response.headers['Content-Security-Policy'] = csp
    return response

# Auto-create database tables before first request (for Railway deployment)
@app.before_request
def create_tables():
    create_tables.has_run = getattr(create_tables, 'has_run', False)
    if not create_tables.has_run:
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
            
            # Migration: Add subtitle_pos_x and subtitle_pos_y columns if they don't exist
            # This handles upgrading existing databases
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns('video_processing_job')]
                
                if 'subtitle_pos_x' not in columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text("ALTER TABLE video_processing_job ADD COLUMN subtitle_pos_x FLOAT DEFAULT 50.0"))
                        conn.commit()
                        app.logger.info("Added subtitle_pos_x column")
                
                if 'subtitle_pos_y' not in columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text("ALTER TABLE video_processing_job ADD COLUMN subtitle_pos_y FLOAT DEFAULT 15.0"))
                        conn.commit()
                        app.logger.info("Added subtitle_pos_y column")
            except Exception as migration_error:
                app.logger.warning(f"Migration warning (may already exist): {migration_error}")
                
        except Exception as e:
            app.logger.error(f"Error creating database tables: {e}")
        create_tables.has_run = True

# Enhanced API Endpoints for Submagic-Style Editor

@app.route('/api/ai/generate', methods=['POST'])
@login_required
def generate_ai_content():
    """Generate viral hooks, descriptions, and hashtags using GPT-4o"""
    data = request.get_json()
    transcript = data.get('transcript', '')
    
    if not transcript:
        return jsonify({"error": "Transcript required"}), 400
    
    try:
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        if not openai.api_key:
            # Fallback mock data if no API key
            return jsonify({
                "hooks": [
                    "You won't believe what happens next...",
                    "This changed everything for me",
                    "Stop doing this mistake right now"
                ],
                "descriptions": [
                    f"An amazing video about: {transcript[:100]}..."
                ],
                "hashtags": ["#viral", "#trending", "#fyp", "#contentcreator", "#video"]
            })
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": "You are a viral content strategist. Generate engaging hooks, descriptions, and hashtags."
            }, {
                "role": "user",
                "content": f"Based on this transcript, generate:\n1. Three viral hook ideas\n2. One compelling description\n3. Ten relevant hashtags\n\nTranscript: {transcript[:2000]}"
            }]
        )
        
        content = response.choices[0].message.content
        
        # Parse the response
        lines = content.split('\n')
        hooks = [l.strip('- ') for l in lines if l.strip().startswith('-') or l.strip().startswith('1.') or l.strip().startswith('2.') or l.strip().startswith('3.')][:3]
        description = next((l for l in lines if 'description' in l.lower() or len(l) > 50), transcript[:150])
        hashtags = [tag.strip() for tag in content.split() if tag.startswith('#')][:10]
        
        return jsonify({
            "hooks": hooks if hooks else ["Amazing content!", "Don't miss this", "Watch till the end"],
            "descriptions": [description],
            "hashtags": hashtags if hashtags else ["#viral", "#trending"]
        })
        
    except Exception as e:
        app.logger.error(f"AI generation error: {e}")
        return jsonify({
            "hooks": ["Amazing content!", "Don't miss this", "Watch till the end"],
            "descriptions": [transcript[:150] + "..."],
            "hashtags": ["#viral", "#trending", "#fyp"]
        })

@app.route('/api/broll/search')
@login_required
def search_broll():
    """Search for B-roll footage from Pexels/Pixabay"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({"results": []})
    
    results = []
    
    # Try Pexels API
    pexels_key = os.environ.get('PEXELS_API_KEY')
    if pexels_key:
        try:
            response = requests.get(
                'https://api.pexels.com/videos/search',
                headers={'Authorization': pexels_key},
                params={'query': query, 'per_page': 8, 'orientation': 'portrait'}
            )
            if response.status_code == 200:
                data = response.json()
                for video in data.get('videos', []):
                    video_files = video.get('video_files', [])
                    if video_files:
                        results.append({
                            'id': str(video['id']),
                            'video_url': video_files[0]['link'],
                            'thumbnail': video['image'],
                            'source': 'pexels',
                            'duration': video.get('duration', 15)
                        })
        except Exception as e:
            app.logger.error(f"Pexels search error: {e}")
    
    # Try Pixabay API as fallback
    pixabay_key = os.environ.get('PIXABAY_API_KEY')
    if pixabay_key and len(results) < 5:
        try:
            response = requests.get(
                'https://pixabay.com/api/videos/',
                params={
                    'key': pixabay_key,
                    'q': query,
                    'per_page': 8 - len(results),
                    'orientation': 'vertical'
                }
            )
            if response.status_code == 200:
                data = response.json()
                for video in data.get('hits', []):
                    results.append({
                        'id': str(video['id']),
                        'video_url': video['videos']['medium']['url'],
                        'thumbnail': video['videos']['medium']['thumbnail'],
                        'source': 'pixabay',
                        'duration': video.get('duration', 15)
                    })
        except Exception as e:
            app.logger.error(f"Pixabay search error: {e}")
    
    # Return mock data if no APIs available
    if not results:
        results = [
            {
                'id': 'mock1',
                'video_url': 'https://example.com/video1.mp4',
                'thumbnail': f'https://source.unsplash.com/300x500/?{query},nature',
                'source': 'pexels',
                'duration': 10
            },
            {
                'id': 'mock2',
                'video_url': 'https://example.com/video2.mp4',
                'thumbnail': f'https://source.unsplash.com/300x500/?{query},city',
                'source': 'pixabay',
                'duration': 15
            }
        ]
    
    return jsonify({"results": results[:8]})

EMOJI_MAP = {
    "love": "❤️", "heart": "❤️", "happy": "😊", "smile": "😊", "joy": "😂",
    "sad": "😢", "cry": "😭", "angry": "😡", "fire": "🔥", "hot": "🔥",
    "money": "💰", "cash": "💵", "good": "👍", "great": "👍", "ok": "👌",
    "bad": "👎", "fail": "🤦", "idea": "💡", "think": "🤔", "question": "❓",
    "exclamation": "❗", "surprise": "😮", "wow": "🤩", "cool": "😎",
    "fun": "🥳", "party": "🎉", "music": "🎶", "dance": "💃", "food": "🍔",
    "drink": "🍹", "fast": "⚡", "slow": "🐢", "work": "💼", "📚": "study",
    "travel": "✈️", "home": "🏠", "yes": "✅", "no": "❌", "danger": "⚠️",
    "star": "⭐", "rocket": "🚀", "top": "🔝", "bottom": "⬇️", "up": "⬆️",
    "down": "⬇️", "left": "⬅️", "right": "➡️"
}

@app.route('/api/ai/generate_emojis', methods=['POST'])
@login_required
def generate_emojis():
    """Analyzes caption text and suggests relevant emojis."""
    data = request.get_json()
    captions = data.get('captions', [])

    if not captions:
        return jsonify({"error": "Captions required"}), 400

    processed_captions = []
    for segment in captions:
        updated_words = []
        for word_data in segment.get('words', []):
            word_text = word_data['text'].lower()
            found_emoji = None
            for keyword, emoji in EMOJI_MAP.items():
                if keyword in word_text:
                    found_emoji = emoji
                    break
            updated_words.append({**word_data, 'emoji': found_emoji})
        processed_captions.append({**segment, 'words': updated_words})

    return jsonify({"status": "success", "captions": processed_captions})

@app.route('/api/export/<job_id>', methods=['POST'])
@login_required
def start_export(job_id):
    """Start professional video export with FFmpeg"""
    data = request.get_json()
    settings = data.get('settings', {})
    style = data.get('style', {})
    captions = data.get('captions', [])
    
    job_entry = VideoProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job_entry:
        return jsonify({"error": "Job not found"}), 404
    
    # Create export job
    export_id = f"export_{job_id}_{int(time.time())}"
    
    # Queue the export task
    from rq import Queue
    from worker import export_video_task
    
    export_queue = Queue('exports', connection=redis_conn)
    export_job = export_queue.enqueue(
        export_video_task,
        job_id=job_id,
        export_id=export_id,
        video_path=job_entry.original_video_filepath,
        captions=captions,
        style=style,
        settings=settings,
        job_timeout='1h'
    )
    
    return jsonify({
        "export_id": export_id,
        "job_id": export_job.id,
        "status": "queued"
    })

@app.route('/api/export/status/<export_id>')
@login_required
def get_export_status(export_id):
    """Get export job status and progress"""
    # Check Redis for export status
    status_key = f"export_status:{export_id}"
    status_data = redis_conn.get(status_key)
    
    if status_data:
        return jsonify(json.loads(status_data))
    
    return jsonify({
        "export_id": export_id,
        "status": "processing",
        "progress": 0,
        "message": "Initializing..."
    })

# Enhanced transcription with word-level timestamps
@app.route('/api/transcribe_word_level', methods=['POST'])
@login_required
def transcribe_word_level():
    """Transcribe video with word-level timestamps using Whisper"""
    if 'video' not in request.files:
        return jsonify({"error": "No video file"}), 400
    
    video = request.files['video']
    language = request.form.get('language', None)
    
    try:
        import openai
        import tempfile
        
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        # Save video temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            video.save(tmp.name)
            video_path = tmp.name
        
        if not openai.api_key:
            # Fallback to faster-whisper without word timestamps
            model = load_faster_whisper_model()
            segments, info = model.transcribe(video_path, language=language)
            
            captions = []
            for i, segment in enumerate(segments):
                words = []
                # Split text into words and estimate timestamps
                text_words = segment.text.split()
                duration = segment.end - segment.start
                word_duration = duration / len(text_words) if text_words else 0
                
                for j, word in enumerate(text_words):
                    words.append({
                        "text": word,
                        "start": segment.start + (j * word_duration),
                        "end": segment.start + ((j + 1) * word_duration),
                        "confidence": 0.9
                    })
                
                captions.append({
                    "id": f"caption_{i}",
                    "text": segment.text.strip(),
                    "start": segment.start,
                    "end": segment.end,
                    "words": words
                })
        else:
            # Use OpenAI Whisper API with word timestamps
            with open(video_path, 'rb') as f:
                response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=f,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            # Parse word-level timestamps
            words = response.words if hasattr(response, 'words') else []
            segments = response.segments if hasattr(response, 'segments') else []
            
            captions = []
            for i, segment in enumerate(segments):
                segment_words = [
                    w for w in words 
                    if w.start >= segment.start and w.end <= segment.end
                ]
                
                captions.append({
                    "id": f"caption_{i}",
                    "text": segment.text.strip(),
                    "start": segment.start,
                    "end": segment.end,
                    "words": [
                        {
                            "text": w.word.strip(),
                            "start": w.start,
                            "end": w.end,
                            "confidence": getattr(w, 'probability', 0.9)
                        }
                        for w in segment_words
                    ]
                })
        
        # Clean up
        os.unlink(video_path)
        
        return jsonify({
            "status": "success",
            "captions": captions,
            "duration": captions[-1]['end'] if captions else 0
        })
        
    except Exception as e:
        app.logger.error(f"Word-level transcription error: {e}")
        return jsonify({"error": str(e)}), 500

# Serve Svelte frontend
@app.route('/editor-new')
@login_required
def editor_new():
    """Serve the new Svelte-based video editor"""
    return send_from_directory('static/dist', 'index.html')

# Serve Svelte static assets
@app.route('/assets/<path:filename>')
def serve_svelte_assets(filename):
    return send_from_directory('static/dist/assets', filename)

if __name__ == '__main__':
    app.run(debug=True)