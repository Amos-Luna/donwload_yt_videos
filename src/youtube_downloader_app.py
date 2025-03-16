import streamlit as st
import os
import tempfile
import subprocess
import time
import yt_dlp
import base64
import shutil
import re
from pathlib import Path


st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF0000;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-title {
        font-size: 1.5rem;
        color: #999999;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-message {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .error-message {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF0000;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def create_progress_bar():
    progress_bar = st.progress(0)
    status_text = st.empty()
    return progress_bar, status_text


def update_progress(progress_bar, status_text, progress, message):
    progress_bar.progress(progress)
    status_text.text(message)


def extract_percentage(percent_str):
    try:

        clean_str = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', percent_str)
        match = re.search(r'(\d+\.\d+|\d+)', clean_str)
        if match:
            return float(match.group(1))
        return 0.0
    except Exception:
        return 0.0


def my_hook(d):
    if d['status'] == 'downloading':
        try:
            percentage = 0.0
            if '_percent_str' in d:
                percentage = extract_percentage(d['_percent_str'])
            elif 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes'] > 0:
                percentage = (d['downloaded_bytes'] / d['total_bytes']) * 100
            

            speed_str = d.get('_speed_str', 'N/A')
            if isinstance(speed_str, str) and '\x1b' in speed_str:
                speed_str = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', speed_str)
                
            eta_str = d.get('_eta_str', 'N/A')
            if isinstance(eta_str, str) and '\x1b' in eta_str:
                eta_str = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', eta_str)
                
            message = f"Descargando: {percentage:.1f}% | Velocidad: {speed_str} | ETA: {eta_str}"
            
            update_progress(
                st.session_state.progress_bar, 
                st.session_state.status_text, 
                min(percentage/100, 1.0),  
                message
            )
        except Exception as e:
            update_progress(st.session_state.progress_bar, st.session_state.status_text, 0.5, "Descargando...")
    
    elif d['status'] == 'finished':
        update_progress(st.session_state.progress_bar, st.session_state.status_text, 1.0, "Descarga completa. Procesando archivo...")


def download_youtube_video(url, output_path, format_id="mp4"):
    try:
        if format_id == "mp4":
            format_spec = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else: 
            format_spec = 'bestaudio/best'
            
        ydl_opts = {
            'format': format_spec,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [my_hook],
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
            'geo_bypass': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                base_name = os.path.splitext(filename)[0]
                for file in os.listdir(output_path):
                    if file.startswith(os.path.basename(base_name)):
                        filename = os.path.join(output_path, file)
                        break
            
            return filename, info.get('title', 'Video')
    
    except Exception as e:
        st.error(f"Error al descargar: {str(e)}")
        raise e


def extract_audio_to_wav(input_path, output_dir="./"):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"[FFmpeg] Input file not found: {input_path}")

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    wav_path = os.path.join(output_dir, f"{base_name}.wav")

    update_progress(st.session_state.progress_bar, 
                   st.session_state.status_text, 
                   0.5, 
                   "Extrayendo audio en formato WAV...")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        wav_path,
    ]
    
    try:
        process = subprocess.run(
            cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        update_progress(st.session_state.progress_bar, 
                       st.session_state.status_text, 
                       1.0, 
                       "¡Conversión completada!")
        return wav_path
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
        st.error(f"Error con FFmpeg: {error_msg}")
        raise e
    except Exception as e:
        st.error(f"Error al extraer audio: {str(e)}")
        raise e


def get_binary_file_downloader_html(file_path, link_text):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        file_name = os.path.basename(file_path)
        mime_type = "audio/wav" if file_path.endswith(".wav") else "video/mp4"
        
        b64 = base64.b64encode(data).decode()
        dl_link = f'<a href="data:{mime_type};base64,{b64}" download="{file_name}" style="display:inline-block; padding:0.5em 1em; color:white; background-color:#FF0000; text-decoration:none; border-radius:4px; text-align:center;">{link_text}</a>'
        return dl_link
    except Exception as e:
        return f"Error generando enlace: {str(e)}"


if 'progress_bar' not in st.session_state:
    st.session_state.progress_bar, st.session_state.status_text = create_progress_bar()


st.markdown('<div class="main-title">YouTube Downloader</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Descarga videos o extrae audio en formato WAV</div>', unsafe_allow_html=True)


with st.form(key='download_form'):
    url = st.text_input("URL del video de YouTube", placeholder="https://www.youtube.com/watch?v=...")
    
    format_option = st.selectbox(
        "Formato de descarga",
        options=["Video (MP4)", "Audio (WAV)"],
        index=0
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        download_button = st.form_submit_button(label="DESCARGAR")


if download_button and url:
    try:

        st.session_state.status_text.empty()
        temp_dir = tempfile.mkdtemp()
        format_id = "mp4" if format_option == "Video (MP4)" else "wav"
        st.info(f"Procesando URL: {url}")
        

        try:
            video_path, video_title = download_youtube_video(url, temp_dir, format_id)
            
            if format_option == "Audio (WAV)":
                st.info("Convirtiendo a formato WAV...")
                output_path = extract_audio_to_wav(video_path, temp_dir)
                download_file_path = output_path
                file_type = "audio"
            else:
                download_file_path = video_path
                file_type = "video"
            
            if os.path.exists(download_file_path):
                st.markdown(f'<div class="success-message">¡Descarga completada! "{video_title}"</div>', unsafe_allow_html=True)
                st.markdown(get_binary_file_downloader_html(download_file_path, f"Descargar {file_type}"), unsafe_allow_html=True)
                
                if format_option == "Video (MP4)" and os.path.exists(download_file_path):
                    st.video(download_file_path)
            else:
                st.error(f"El archivo {download_file_path} no se encontró después de la descarga.")
                
        except Exception as e:
            st.error(f"Error en el proceso de descarga: {str(e)}")
        
    except Exception as e:
        st.markdown(f'<div class="error-message">Error: {str(e)}</div>', unsafe_allow_html=True)


with st.expander("ℹ️ Cómo usar esta aplicación"):
    st.markdown("""
    1. Pega la URL del video de YouTube en el campo de texto
    2. Selecciona el formato deseado (MP4 o WAV)
    3. Haz clic en el botón DESCARGAR
    4. Espera a que se complete el proceso
    5. Haz clic en el enlace de descarga para guardar el archivo
    """)

st.markdown("---")
st.markdown("Creado por Amos Luna :D")