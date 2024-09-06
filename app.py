# Importaciones estándar de Python
import os
import traceback
import time
from urllib.parse import urlparse

# Importaciones de terceros
from flask import Flask, request, render_template, send_file, after_this_request
from dotenv import load_dotenv
import yt_dlp
from openai import OpenAI

# Cargar variables de entorno
load_dotenv()

# Configuración de la aplicación Flask
app = Flask(__name__, static_folder='static')

# Inicializar el cliente de OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Crear las carpetas de descargas si no existen
os.makedirs('downloads/videos', exist_ok=True)
os.makedirs('downloads/audios', exist_ok=True)
os.makedirs('downloads/outputs', exist_ok=True)

# Función para verificar URLs


def validate_url(url):
    if not url or not is_valid_url(url):
        return False, "URL del video no proporcionada o es inválida", 400
    return True, None, None

# Función para limpiar las descargas después de 10 minutos


def clean_old_files(directory, max_age=600):
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

# Función para manejar la descarga y conversión de media


def download_media(video_url, ydl_opts, subdir='downloads'):
    ydl_opts['outtmpl'] = f'{subdir}/%(title)s.%(ext)s'
    ydl_opts['cookiesfrombrowser'] = ('chrome', 'firefox', 'safari', 'edge',)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename
    except Exception:
        app.logger.error(f"Error al descargar media: {traceback.format_exc()}")
        return None


def handle_download(video_url, ydl_opts, subdir, output_format=None):
    filename = download_media(video_url, ydl_opts, subdir)
    if filename is None:
        return False, "Ocurrió un error al descargar el archivo", 500

    if output_format and filename.endswith('.mkv'):
        filename = filename.replace('.mkv', f'.{output_format}')
    return True, filename, None

# Uso de decoradores para manejar eventos de limpieza


def remove_file_after_request(filename):
    @after_this_request
    def remove_file(response):
        try:
            os.remove(filename)
        except OSError as error:
            app.logger.error(f"Error al eliminar el archivo: {error}")
        return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download_video', methods=['POST'])
def download_video():
    video_url = request.form['video_url']
    valid, message, status = validate_url(video_url)
    if not valid:
        return message, status

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    success, filename, error = handle_download(
        video_url, ydl_opts, 'downloads/videos', 'mp4')
    if not success:
        return error

    remove_file_after_request(filename)
    return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))


@app.route('/download_audio', methods=['POST'])
def download_audio():
    video_url = request.form['video_url']
    valid, message, status = validate_url(video_url)
    if not valid:
        return message, status

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'keepvideo': True,
        'outtmpl': 'downloads/audios/%(title)s.%(ext)s',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'verbose': True,
        'ignoreerrors': True,
        'nocheckcertificate': True,
        'cookiesfrombrowser': ('chrome', 'firefox', 'safari', 'edge',),
    }

    success, filename, error = handle_download(
        video_url, ydl_opts, 'downloads/audios', 'mp3')
    if not success:
        return error

    remove_file_after_request(filename)
    return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))


@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    video_url = request.form['video_url']
    valid, message, status = validate_url(video_url)
    if not valid:
        return message, status

    try:
        # Descargar el audio usando yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'keepvideo': True,
            'outtmpl': 'downloads/audios/%(title)s.%(ext)s',
            'cookiesfrombrowser': ('chrome', 'firefox', 'safari', 'edge',),
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
                {"role": "user", "content": f"A continuación se presenta la transcripción del contenido:\n\n{transcript_text}"}
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

        remove_file_after_request(output_filename)
        return send_file(output_filename, as_attachment=True, download_name=os.path.basename(output_filename))

    except Exception:
        app.logger.error(f"Error en la transcripción: {traceback.format_exc()}")
        return f"Ocurrió un error al transcribir el audio: {traceback.format_exc()}", 500


if __name__ == '__main__':
    app.run(debug=True)
