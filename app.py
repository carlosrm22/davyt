from flask import Flask, request, render_template, send_file
import yt_dlp
import traceback
import os

app = Flask(__name__)

# Crear la carpeta de descargas si no existe
if not os.path.exists('downloads'):
    os.makedirs('downloads')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download_video', methods=['POST'])
def download_video():
    video_url = request.form['video_url']
    if not video_url:
        return "URL del video no proporcionada", 400

    try:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': 'downloads/video.%(ext)s',  # Descargar en la carpeta 'downloads'
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferredformat': 'mp4',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = os.path.join('downloads', 'video.mp4')  # Apuntar al archivo convertido en 'downloads/'

        response = send_file(filename, as_attachment=True)
        os.remove(filename)  # Elimina el archivo después de enviarlo
        return response
    except Exception as e:
        return f"Ocurrió un error al descargar el video: {traceback.format_exc()}", 500

@app.route('/download_audio', methods=['POST'])
def download_audio():
    video_url = request.form['video_url']
    if not video_url:
        return "URL del video no proporcionada", 400

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/audio.%(ext)s',  # Descargar en la carpeta 'downloads'
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = os.path.join('downloads', 'audio.mp3')  # Apuntar al archivo convertido en 'downloads/'

        response = send_file(filename, as_attachment=True)
        os.remove(filename)  # Elimina el archivo después de enviarlo
        return response
    except Exception as e:
        return f"Ocurrió un error al descargar el audio: {traceback.format_exc()}", 500

if __name__ == '__main__':
    app.run(debug=True)
