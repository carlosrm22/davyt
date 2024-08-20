# Importaciones estándar de Python
import os
import traceback
import time
from urllib.parse import urlparse

# Importaciones de terceros
from flask import Flask, request, render_template, send_file, after_this_request
from dotenv import load_dotenv
from flask_sse import sse
import yt_dlp
from openai import OpenAI


def clean_old_files(directory, max_age=3600):
    current_time = time.time()
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.stat(file_path).st_mtime < current_time - max_age:
            os.remove(file_path)


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


load_dotenv()  # Cargar las variables de entorno desde el archivo .env

app = Flask(__name__, static_folder='static')
app.config["REDIS_URL"] = "redis://localhost:6379/0"
app.register_blueprint(sse, url_prefix='/stream')

# Inicializar el cliente de OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def download_media(video_url, ydl_opts, subdir='downloads'):
    ydl_opts['outtmpl'] = f'{subdir}/%(title)s.%(ext)s'
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename
    except Exception as e:
        app.logger.error(f"Error al descargar media: {traceback.format_exc()}")
        return None


# Crear la carpeta de descargas y subdirectorios si no existen
if not os.path.exists('downloads/videos'):
    os.makedirs('downloads/videos')
if not os.path.exists('downloads/audios'):
    os.makedirs('downloads/audios')
if not os.path.exists('downloads/outputs'):
    os.makedirs('downloads/outputs')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download_video', methods=['POST'])
def download_video():
    video_url = request.form['video_url']
    if not video_url or not is_valid_url(video_url):
        return "URL del video no proporcionada o es inválida", 400

    # Notificar al cliente que el proceso ha comenzado
    sse.publish({"message": "start"}, type='spinner')

    try:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }

        filename = download_media(
            video_url, ydl_opts, subdir='downloads/videos')
        if filename is None:
            return "Ocurrió un error al descargar el video", 500

        filename = filename.replace('.mkv', '.mp4')

        # Notificar al cliente que el proceso ha terminado
        sse.publish({"message": "end"}, type='spinner')

        @after_this_request
        def remove_file(response):
            try:
                os.remove(filename)
            except OSError as error:
                app.logger.error(f"Error al eliminar el archivo: {error}")
            return response

        return send_file(filename, as_attachment=True)

    except Exception as e:
        sse.publish({"message": "end"}, type='spinner')
        app.logger.error(f"Error al descargar el video: {
                         traceback.format_exc()}")
        return f"Ocurrió un error al descargar el video: {traceback.format_exc()}", 500


@app.route('/download_audio', methods=['POST'])
def download_audio():
    video_url = request.form['video_url']
    if not video_url or not is_valid_url(video_url):
        return "URL del video no proporcionada o es inválida", 400

    # Notificar al cliente que el proceso ha comenzado
    sse.publish({"message": "start"}, type='spinner')

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        filename = download_media(
            video_url, ydl_opts, subdir='downloads/audios')
        if filename is None:
            return "Ocurrió un error al descargar el audio", 500

        filename = filename.replace('.webm', '.mp3')

        # Notificar al cliente que el proceso ha terminado
        sse.publish({"message": "end"}, type='spinner')

        @after_this_request
        def remove_file(response):
            try:
                os.remove(filename)
            except OSError as error:
                app.logger.error(f"Error al eliminar el archivo: {error}")
            return response

        return send_file(filename, as_attachment=True)

    except Exception as e:
        sse.publish({"message": "end"}, type='spinner')
        app.logger.error(f"Error al descargar el audio: {
                         traceback.format_exc()}")
        return f"Ocurrió un error al descargar el audio: {traceback.format_exc()}", 500


@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    app.logger.info("Transcription route was accessed")

    video_url = request.form['video_url']
    if not video_url or not is_valid_url(video_url):
        return "URL del video no proporcionada o es inválida", 400

    # Notificar al cliente que el proceso ha comenzado
    sse.publish({"message": "start"}, type='spinner')

    try:
        # Descargar el audio usando yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'keepvideo': True,  # Evita que se borre el archivo original
            # Guardar en la carpeta de audios
            'outtmpl': 'downloads/audios/%(title)s.%(ext)s'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')

        # Transcripción del audio con OpenAI Whisper usando la nueva API
        audio_file_path = filename
        with open(audio_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            transcript_text = response.text
            language_detected = getattr(response, 'language', 'unknown')

        # Generar resumen de la transcripción
        summary_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente que genera resúmenes precisos y concisos."},
                {"role": "user", "content": f"Resume lo siguiente:\n\n{transcript_text}"}
            ]
        )
        summary_text = summary_response.choices[0].message.content.strip()

        # Generar análisis detallado de la transcripción
        detailed_analysis_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Separar los temas principales abordados en la transcripción. Utilizar recursos mnemotécnicos para ayudar a los estudiantes a recordar los conceptos clave. Incluir esquemas que faciliten la comprensión visual de los temas tratados. Destacar las palabras clave importantes en cada sección del resumen. Proporcionar recomendaciones para la mejor comprensión y estudio de los temas. Hacer un mapa mental del tema. Entender los Conceptos Clave. Autoevaluación. Referencias bibliográficas y recursos externos. Todo esto presentado en texto plano."},
                {"role": "user", "content": f"A continuación se presenta la transcripción del contenido:\n\n{
                    transcript_text}"}
            ]
        )
        detailed_analysis_text = detailed_analysis_response.choices[0].message.content.strip(
        )

        # Crear archivo de salida con la transcripción, resumen y análisis detallado
        output_filename = os.path.join(
            'downloads/outputs', f"{os.path.splitext(os.path.basename(filename))[0]}_output.txt")
        with open(output_filename, "w", encoding="utf-8") as output_file:
            output_file.write("Resumen:\n")
            output_file.write(summary_text + "\n\n")
            output_file.write("Transcripción:\n")
            output_file.write(transcript_text + "\n\n")
            output_file.write("Análisis:\n")
            output_file.write(detailed_analysis_text)

        # Notificar al cliente que el proceso ha terminado
        sse.publish({"message": "end"}, type='spinner')

        # Retornar el archivo de texto con la transcripción, resumen y análisis detallado
        return send_file(output_filename, as_attachment=True)

    except Exception as e:
        sse.publish({"message": "end"}, type='spinner')
        app.logger.error(f"Error en la transcripción: {
                         traceback.format_exc()}")
        return f"Ocurrió un error al transcribir el audio: {traceback.format_exc()}", 500


if __name__ == '__main__':
    app.run(debug=True)
