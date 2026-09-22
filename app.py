import streamlit as st
import yt_dlp
import os
import glob
import tempfile
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

# --- App Config ---
st.set_page_config(
    page_title="Universal Media Studio & Editor",
    page_icon="🎬",
    layout="wide"
)

# --- Styling ---
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E88E5; }
    .sub-header { color: #616161; font-size: 1rem; margin-bottom: 2rem; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎬 Universal Media Downloader & In-Browser Editor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Fetch, preview, trim, resize, and export media from online links.</div>', unsafe_allow_html=True)

# --- State Management ---
if "media_info" not in st.session_state:
    st.session_state.media_info = None
if "downloaded_file" not in st.session_state:
    st.session_state.downloaded_file = None
if "processed_file" not in st.session_state:
    st.session_state.processed_file = None


def fetch_metadata(url):
    """Inspects media information without downloading stream bytes."""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def download_media(url, format_type, quality):
    """Downloads requested media stream with robust format selection and client spoofing."""
    tmp_dir = tempfile.mkdtemp()
    
    # Generic options protecting against cloud-IP throttling
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': os.path.join(tmp_dir, 'source_media.%(ext)s'),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }

    if format_type == "Audio Only (MP3)":
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality.replace('kbps', ''),
            }],
        }
    else:
        # Fallback hierarchy: Target resolution -> lower resolution -> any best
        height_val = quality.replace('p', '') if quality != "Best Available" else "1080"
        ydl_opts = {
            **base_opts,
            'format': f'bestvideo[height<={height_val}]+bestaudio/best[height<={height_val}]/best',
            'merge_output_format': 'mp4',
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        
    # Reliable file discovery inside the temp directory
    candidates = glob.glob(os.path.join(tmp_dir, "*"))
    media_files = [f for f in candidates if not f.endswith(('.part', '.ytdl')) and os.path.isfile(f)]
    
    if not media_files:
        raise RuntimeError("The downloaded file is empty or stream was rejected by the server.")

    # Sort to grab the largest valid media payload
    return max(media_files, key=os.path.getsize)


# --- Step 1: Input URL ---
st.subheader("Step 1: Enter Media Link")
url_input = st.text_input("Paste the URL below (YouTube, Vimeo, Twitter, direct media):", placeholder="https://www.youtube.com/watch?v=...")

col1, _ = st.columns([1, 4])
with col1:
    if st.button("Fetch Media", type="primary", use_container_width=True):
        if url_input.strip():
            with st.spinner("Retrieving stream metadata..."):
                try:
                    info = fetch_metadata(url_input.strip())
                    st.session_state.media_info = info
                    st.session_state.downloaded_file = None
                    st.session_state.processed_file = None
                    st.success("Metadata loaded!")
                except Exception as e:
                    st.error(f"Failed to fetch content: {str(e)}")
        else:
            st.warning("Please provide a valid URL.")

# --- Step 2: Content Preview & Format Configuration ---
if st.session_state.media_info:
    info = st.session_state.media_info
    st.divider()
    st.subheader("Step 2: Preview Content & Download Configuration")

    col_thumb, col_details = st.columns([1, 2])
    with col_thumb:
        if info.get("thumbnail"):
            st.image(info["thumbnail"], caption=info.get("title", "Thumbnail"), use_container_width=True)
    
    with col_details:
        st.write(f"**Title:** {info.get('title', 'N/A')}")
        st.write(f"**Uploader:** {info.get('uploader', 'N/A')}")
        duration_sec = info.get('duration', 0)
        st.write(f"**Duration:** {int(duration_sec // 60)}m {int(duration_sec % 60)}s" if duration_sec else "Live/Unknown")

        st.markdown("#### Quality & Format Settings")
        download_type = st.radio("Format Category:", ["Video (MP4)", "Audio Only (MP3)"], horizontal=True)

        if download_type == "Video (MP4)":
            quality_options = ["Best Available", "1080p", "720p", "480p", "360p"]
        else:
            quality_options = ["320kbps", "256kbps", "192kbps", "128kbps"]

        selected_quality = st.selectbox("Select Target Quality:", quality_options)

        if st.button("Download Stream to Local Workspace"):
            with st.spinner("Downloading stream..."):
                try:
                    file_path = download_media(url_input.strip(), download_type, selected_quality)
                    st.session_state.downloaded_file = file_path
                    st.session_state.processed_file = file_path
                    st.success("Media successfully staged for editor!")
                except Exception as e:
                    st.error(f"Download error: {str(e)}")

# --- Step 3: In-Browser Editor ---
if st.session_state.downloaded_file and os.path.exists(st.session_state.downloaded_file):
    filepath = st.session_state.downloaded_file
    is_audio = filepath.lower().endswith(".mp3")

    st.divider()
    st.subheader("Step 3: In-Browser Editor")
    
    if is_audio:
        st.audio(filepath)
    else:
        st.video(filepath)

    st.markdown("#### Editing Options")
    
    # Extract actual clip duration
    try:
        clip = AudioFileClip(filepath) if is_audio else VideoFileClip(filepath)
        total_duration = clip.duration
        clip.close()
    except Exception:
        total_duration = 60.0

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        start_time = st.number_input("Start Time (seconds):", min_value=0.0, max_value=float(total_duration), value=0.0, step=0.5)
    with col_t2:
        end_time = st.number_input("End Time (seconds):", min_value=0.1, max_value=float(total_duration), value=float(total_duration), step=0.5)

    target_scale = "Keep Original"
    if not is_audio:
        target_scale = st.selectbox("Resize Video Resolution:", ["Keep Original", "1920x1080", "1280x720", "854x480", "640x360"])

    if st.button("Apply Edits & Render Output"):
        if start_time >= end_time:
            st.error("Start time must be less than end time.")
        else:
            with st.spinner("Processing edits with MoviePy & FFmpeg..."):
                try:
                    out_dir = tempfile.mkdtemp()
                    output_path = os.path.join(out_dir, f"edited_{os.path.basename(filepath)}")
                    
                    if is_audio:
                        audio = AudioFileClip(filepath).subclip(start_time, end_time)
                        audio.write_audiofile(output_path, logger=None)
                        audio.close()
                    else:
                        video = VideoFileClip(filepath).subclip(start_time, end_time)
                        if target_scale != "Keep Original":
                            w, h = map(int, target_scale.split("x"))
                            video = video.resize(newsize=(w, h))
                        video.write_videofile(
                            output_path, 
                            codec="libx264", 
                            audio_codec="aac", 
                            temp_audiofile=os.path.join(out_dir, "temp-audio.m4a"),
                            remove_temp=True, 
                            logger=None
                        )
                        video.close()
                    
                    st.session_state.processed_file = output_path
                    st.success("Editing complete!")
                except Exception as e:
                    st.error(f"Processing failed: {str(e)}")

# --- Step 4: Final Download ---
if st.session_state.processed_file and os.path.exists(st.session_state.processed_file):
    st.divider()
    st.subheader("Step 4: Download Processed File")
    
    final_file = st.session_state.processed_file
    ext = os.path.splitext(final_file)[1].lower()
    mime_type = "audio/mpeg" if ext == ".mp3" else "video/mp4"

    with open(final_file, "rb") as f:
        file_bytes = f.read()

    # Dynamic filename derived from original title
    base_title = st.session_state.media_info.get("title", "media")
    clean_title = "".join([c for c in base_title if c.isalnum() or c in (' ', '-', '_')]).strip()
    export_filename = f"{clean_title or 'output'}{ext}"

    st.download_button(
        label=f"💾 Download File ({ext.upper().replace('.', '')})",
        data=file_bytes,
        file_name=export_filename,
        mime=mime_type,
        type="primary"
    )
