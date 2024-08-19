from flask import Flask, request, render_template, send_file
import yt_dlp
import traceback
import os

app = Flask(__name__)

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
            'outtmpl': 'video.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferredformat': 'mp4',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = 'video.mp4'  # Asegura que apunte al archivo convertido

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
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = 'audio.mp3'  # Asegura que apunte al archivo convertido

        response = send_file(filename, as_attachment=True)
        os.remove(filename)  # Elimina el archivo después de enviarlo
        return response
    except Exception as e:
        return f"Ocurrió un error al descargar el audio: {traceback.format_exc()}", 500

if __name__ == '__main__':
    app.run(debug=True)
