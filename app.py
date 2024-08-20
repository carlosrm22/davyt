from flask import Flask, request, render_template, send_file, after_this_request
import yt_dlp
import os
from openai import OpenAI
from dotenv import load_dotenv
import traceback

load_dotenv()  # Cargar las variables de entorno desde el archivo .env

app = Flask(__name__, static_folder='static')

# Inicializar el cliente de OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info_dict).replace('.mkv', '.mp4')

        @after_this_request
        def remove_file(response):
            try:
                os.remove(filename)
            except Exception as error:
                app.logger.error(f"Error al eliminar el archivo: {error}")
            return response

        return send_file(filename, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Ocurrió un error al descargar el video: {traceback.format_exc()}")
        return f"Ocurrió un error al descargar el video: {traceback.format_exc()}", 500

@app.route('/download_audio', methods=['POST'])
def download_audio():
    video_url = request.form['video_url']
    if not video_url:
        return "URL del video no proporcionada", 400

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')

        @after_this_request
        def remove_file(response):
            try:
                os.remove(filename)
            except Exception as error:
                app.logger.error(f"Error al eliminar el archivo: {error}")
            return response

        return send_file(filename, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Ocurrió un error al descargar el audio: {traceback.format_exc()}")
        return f"Ocurrió un error al descargar el audio: {traceback.format_exc()}", 500

@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    app.logger.info("Transcription route was accessed")

    video_url = request.form['video_url']
    if not video_url:
        return "URL del video no proporcionada", 400

    try:
        # Descargar el audio usando yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')

        # Transcripción del audio con OpenAI Whisper usando la nueva API
        audio_file_path = filename  # No es necesario añadir 'downloads/' porque filename ya lo incluye
        with open(audio_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            transcript_text = response.text
            # Verificar si existe el atributo language, si no usar un valor por defecto
            language_detected = getattr(response, 'language', 'unknown')

        # Opcional: traducción y resumen (puedes ajustar esto según sea necesario)
        if language_detected != 'es':  # Ajuste básico para verificar el idioma
            translation_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un traductor muy hábil."},
                    {"role": "user", "content": f"Traduce el siguiente texto al español:\n\n{transcript_text}"}
                ]
            )
            translated_text = translation_response.choices[0].message.content.strip()
        else:
            translated_text = transcript_text

        summary_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que genera resúmenes precisos y concisos."},
                {"role": "user", "content": f"Resume lo siguiente en español:\n\n{translated_text}"}
            ]
        )
        summary_text = summary_response.choices[0].message.content.strip()

        # Eliminar el archivo de audio después de procesarlo
        @after_this_request
        def remove_file(response):
            try:
                os.remove(audio_file_path)
            except Exception as error:
                app.logger.error(f"Error al eliminar el archivo: {error}")
            return response

        # Retornar la transcripción, traducción (si aplica), y resumen
        return {
            "transcripción": transcript_text,
            "traducción": translated_text,
            "resumen": summary_text
        }
    except Exception as e:
        app.logger.error(f"Error en la transcripción: {traceback.format_exc()}")
        return f"Ocurrió un error al transcribir el audio: {traceback.format_exc()}", 500

if __name__ == '__main__':
    app.run(debug=True)
