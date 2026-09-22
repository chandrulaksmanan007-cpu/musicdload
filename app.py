import streamlit as st
import yt_dlp
import os
import tempfile
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

# --- App Config ---
st.set_page_config(
    page_title="Universal Media Hub & Editor",
    page_icon="🎬",
    layout="wide"
)

# --- Custom Styling for Clean UX ---
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E88E5; }
    .sub-header { color: #616161; font-size: 1rem; margin-bottom: 2rem; }
    .step-card {
        padding: 1.2rem;
        border-radius: 10px;
        background-color: #f9f9f9;
        margin-bottom: 1.5rem;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎬 Universal Media Downloader & Editor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Fetch, preview, trim/edit, and export content from online URLs in custom formats and qualities.</div>', unsafe_allow_html=True)

# --- Session State Management ---
if "media_info" not in st.session_state:
    st.session_state.media_info = None
if "downloaded_file" not in st.session_state:
    st.session_state.downloaded_file = None
if "processed_file" not in st.session_state:
    st.session_state.processed_file = None


def fetch_metadata(url):
    """Fetch video metadata and format choices without downloading entire payload."""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info


def download_media(url, format_type, quality):
    """Download the media file based on user's target quality."""
    tmp_dir = tempfile.mkdtemp()
    
    if format_type == "Audio Only (MP3)":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality.replace('kbps', ''),
            }],
        }
    else:
        # Video + Audio combined
        height_filter = f"[height<={quality.replace('p', '')}]" if quality != "Best Available" else ""
        ydl_opts = {
            'format': f'bestvideo{height_filter}+bestaudio/best{height_filter}/best',
            'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4'
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(result)
        if format_type == "Audio Only (MP3)":
            filename = os.path.splitext(filename)[0] + ".mp3"
        elif not os.path.exists(filename):
            filename = os.path.splitext(filename)[0] + ".mp4"
            
        return filename


# --- Step 1: Input URL ---
st.subheader("Step 1: Enter Media Link")
url_input = st.text_input("Paste the URL below (YouTube, Vimeo, direct media links, etc.):", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("Fetch Media", type="primary", use_container_width=True):
        if url_input.strip():
            with st.spinner("Analyzing URL and fetching available streams..."):
                try:
                    info = fetch_metadata(url_input.strip())
                    st.session_state.media_info = info
                    st.session_state.downloaded_file = None
                    st.session_state.processed_file = None
                    st.success("Metadata loaded successfully!")
                except Exception as e:
                    st.error(f"Failed to fetch content: {str(e)}")
        else:
            st.warning("Please provide a valid URL.")

# --- Step 2: Content Preview & Initial Quality Selection ---
if st.session_state.media_info:
    info = st.session_state.media_info
    st.divider()
    st.subheader("Step 2: Preview Content & Choose Base Download")

    col_thumb, col_details = st.columns([1, 2])
    with col_thumb:
        if "thumbnail" in info and info["thumbnail"]:
            st.image(info["thumbnail"], caption=info.get("title", "Thumbnail"), use_container_width=True)
    
    with col_details:
        st.write(f"**Title:** {info.get('title', 'N/A')}")
        st.write(f"**Uploader:** {info.get('uploader', 'N/A')}")
        duration_sec = info.get('duration', 0)
        st.write(f"**Duration:** {int(duration_sec // 60)}m {int(duration_sec % 60)}s" if duration_sec else "Live/Unknown")

        st.markdown("#### Select Download Configuration")
        download_type = st.radio("Format Category:", ["Video (MP4)", "Audio Only (MP3)"], horizontal=True)

        if download_type == "Video (MP4)":
            quality_options = ["Best Available", "1080p", "720p", "480p", "360p"]
        else:
            quality_options = ["320kbps", "256kbps", "192kbps", "128kbps"]

        selected_quality = st.selectbox("Select Target Quality:", quality_options)

        if st.button("Prepare Media for Editing / Direct Download"):
            with st.spinner("Downloading stream to local workspace..."):
                try:
                    file_path = download_media(url_input.strip(), download_type, selected_quality)
                    st.session_state.downloaded_file = file_path
                    st.session_state.processed_file = file_path
                    st.success("Media ready for editor!")
                except Exception as e:
                    st.error(f"Download error: {str(e)}")

# --- Step 3: In-Browser Editor ---
if st.session_state.downloaded_file and os.path.exists(st.session_state.downloaded_file):
    filepath = st.session_state.downloaded_file
    is_audio = filepath.endswith(".mp3")

    st.divider()
    st.subheader("Step 3: In-Browser Editor")
    
    # Display preview player
    if is_audio:
        st.audio(filepath)
    else:
        st.video(filepath)

    st.markdown("#### Editing Options")
    
    # Trim Feature
    try:
        if is_audio:
            clip = AudioFileClip(filepath)
        else:
            clip = VideoFileClip(filepath)
        total_duration = clip.duration
        clip.close()
    except Exception:
        total_duration = 60.0

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        start_time = st.number_input("Start Time (seconds):", min_value=0.0, max_value=float(total_duration), value=0.0, step=0.5)
    with col_t2:
        end_time = st.number_input("End Time (seconds):", min_value=0.1, max_value=float(total_duration), value=float(total_duration), step=0.5)

    # Resolution resize (for video only)
    target_scale = "Keep Original"
    if not is_audio:
        target_scale = st.selectbox("Resize Video Resolution:", ["Keep Original", "1920x1080", "1280x720", "854x480", "640x360"])

    if st.button("Apply Edits & Render"):
        if start_time >= end_time:
            st.error("Start time must be less than end time.")
        else:
            with st.spinner("Processing edits with FFmpeg/MoviePy..."):
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
                        video.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
                        video.close()
                    
                    st.session_state.processed_file = output_path
                    st.success("Editing complete!")
                except Exception as e:
                    st.error(f"Processing failed: {str(e)}")

# --- Step 4: Download Section ---
if st.session_state.processed_file and os.path.exists(st.session_state.processed_file):
    st.divider()
    st.subheader("Step 4: Download Final File")
    
    final_file = st.session_state.processed_file
    ext = os.path.splitext(final_file)[1]
    mime_type = "audio/mpeg" if ext == ".mp3" else "video/mp4"

    with open(final_file, "rb") as f:
        file_bytes = f.read()

    st.download_button(
        label=f"💾 Download Final Output ({ext.upper().replace('.', '')})",
        data=file_bytes,
        file_name=f"output_{os.path.basename(final_file)}",
        mime=mime_type,
        type="primary"
    )