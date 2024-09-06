import os
import traceback
import threading
import time
from urllib.parse import urlparse
import logging

from flask import Flask, request, render_template, send_file, jsonify
from dotenv import load_dotenv
import yt_dlp
from openai import OpenAI

app = Flask(__name__, static_folder='static')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Crear las carpetas de descargas si no existen
os.makedirs('downloads/videos', exist_ok=True)
os.makedirs('downloads/audios', exist_ok=True)
os.makedirs('downloads/outputs', exist_ok=True)


def validate_youtube_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ('http', 'https'):
        return False, "La URL debe comenzar con http:// o https://.", 400
    return True, None, None


def clean_old_files(directory, max_age=600):
    current_time = time.time()
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.stat(file_path).st_mtime < current_time - max_age:
            try:
                os.remove(file_path)
                logger.info(f"Archivo eliminado: {file_path}")
            except OSError as error:
                logger.error(f"Error al eliminar el archivo {
                             file_path}: {error}")


def download_media(video_url, ydl_opts, filename):
    """
    Descarga un archivo de video o audio usando yt-dlp con las opciones dadas y nombre fijo.

    Args:
        video_url (str): La URL del video de YouTube a descargar.
        ydl_opts (dict): Opciones de configuración para yt-dlp.
        filename (str): El nombre fijo del archivo a guardar.

    Returns:
        str: El nombre del archivo descargado si tiene éxito, o None si falla.
    """
    try:
        # Define la plantilla de salida para usar un nombre de archivo fijo
        ydl_opts['outtmpl'] = filename
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=True)
        return filename
    except yt_dlp.utils.DownloadError:
        logger.error(f"Error de descarga con yt-dlp: {traceback.format_exc()}")
        return None
    except Exception:
        logger.error(f"Error al descargar media: {traceback.format_exc()}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download_video', methods=['POST'])
def download_video():
    video_url = request.form.get('video_url')
    valid, message, status = validate_youtube_url(video_url)
    if not valid:
        return jsonify({"error": message}), status

    # Nombre fijo para los videos
    filename = os.path.join(
        'downloads/videos', 'Davit_Planck_Video_Descargado.mp4')
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'merge_output_format': 'mp4',
    }

    result = download_media(video_url, ydl_opts, filename)
    if not result:
        logger.error(
            f"Error en /download_video: No se pudo descargar el video.")
        return jsonify({"error": "Error al descargar el video."}), 500

    # Verifica y asegura que el archivo existe antes de enviarlo
    if not os.path.exists(filename):
        logger.error(f"Archivo no encontrado para enviar: {filename}")
        return jsonify({"error": "Archivo no encontrado después de la descarga."}), 500

    return send_file(filename, as_attachment=True)


@app.route('/download_audio', methods=['POST'])
def download_audio():
    video_url = request.form.get('video_url')
    valid, message, status = validate_youtube_url(video_url)
    if not valid:
        return jsonify({"error": message}), status

    # Nombre fijo para los audios
    filename = os.path.join(
        'downloads/audios', 'Davit_Planck_Audio_Descargado.mp3')
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'keepvideo': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'verbose': True,
        'ignoreerrors': True,
        'nocheckcertificate': True,
    }

    result = download_media(video_url, ydl_opts, filename)
    if not result:
        logger.error(
            f"Error en /download_audio: No se pudo descargar el audio.")
        return jsonify({"error": "Error al descargar el audio."}), 500

    if not os.path.exists(filename):
        logger.error(f"Archivo no encontrado para enviar: {filename}")
        return jsonify({"error": "Archivo no encontrado después de la descarga."}), 500

    return send_file(filename, as_attachment=True)


@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    video_url = request.form.get('video_url')
    valid, message, status = validate_youtube_url(video_url)
    if not valid:
        return jsonify({"error": message}), status

    try:
        # Descargar el audio usando yt-dlp
        filename = os.path.join(
            'downloads/audios', 'Davit_Planck_Audio_Descargado.mp3')
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'keepvideo': True,
        }
        download_media(video_url, ydl_opts, filename)

        # Transcripción del audio con OpenAI Whisper
        with open(filename, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            transcript_text = response.text

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

        # Nombre fijo para la transcripción
        output_filename = os.path.join(
            'downloads/outputs', 'Davit_Planck_Transcripcion_Descargada.txt')
        with open(output_filename, "w", encoding="utf-8") as output_file:
            output_file.write("Resumen:\n")
            output_file.write(summary_text + "\n\n")
            output_file.write("Transcripción:\n")
            output_file.write(transcript_text + "\n\n")
            output_file.write("Análisis:\n")
            output_file.write(detailed_analysis_text)

        return send_file(output_filename, as_attachment=True)

    except Exception as e:
        logger.error(f"Error en la transcripción: {traceback.format_exc()}")
        return jsonify({"error": f"Ocurrió un error al transcribir el audio: {str(e)}"}), 500

# Función para ejecutar la limpieza de archivos antiguos periódicamente
def start_cleanup():
    while True:
        clean_old_files('downloads/videos')
        clean_old_files('downloads/audios')
        clean_old_files('downloads/outputs')
        time.sleep(600)  # Espera 10 minutos antes de limpiar de nuevo


if __name__ == '__main__':
    # Inicia el hilo para la limpieza automática de archivos antiguos
    cleanup_thread = threading.Thread(target=start_cleanup)
    # Hilo daemon para que se cierre con la aplicación principal
    cleanup_thread.daemon = True
    cleanup_thread.start()

    # Inicia el servidor Flask
    app.run(debug=False)
