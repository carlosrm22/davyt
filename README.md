# Davyt
Davyt es el acrónimo de:

**D**escarga **A**udio y **V**ideo de **Y**ou**T**ube

Es un proyecto personal para descargar audio y video de Youtube
y generar transcripciones con Whisper de Open Ai

Creado por *Carlos Romero*.


---

# Descargar y Transcribir Videos de YouTube

Esta aplicación Flask te permite descargar videos de YouTube, extraer el audio en formato MP3 y transcribir el audio utilizando la API de OpenAI Whisper. La interfaz está diseñada para ser amigable y fácil de usar, con una única entrada para la URL del video y botones separados para cada acción.

## Características

- **Descargar Videos**: Permite descargar el video completo de YouTube en el mejor formato disponible.
- **Descargar Audio**: Extrae y descarga solo el audio del video en formato MP3.
- **Transcribir Audio**: Utiliza la API de OpenAI Whisper para transcribir el audio descargado del video.

## Estructura del Proyecto

El proyecto está organizado de la siguiente manera:

```
/static
    /images
        itinnitus-20171130-0005.jpg  # Imagen usada en la interfaz
/templates
    index.html  # Plantilla HTML principal
/downloads
    # Carpeta temporal para almacenar descargas (ignoradas por git)
/env
    # Entorno virtual de Python (ignorado por git)
app.py  # Código principal de la aplicación Flask
requirements.txt  # Dependencias del proyecto
.gitignore  # Archivos y carpetas ignoradas por git
README.md  # Documentación del proyecto
```

## Configuración del Entorno

### Requisitos Previos

- Python 3.6 o superior
- pip (gestor de paquetes de Python)
- ffmpeg (para la conversión de formatos de audio/video)

### Instalación

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/tu-usuario/descargar-audio-yt.git
   cd descargar-audio-yt
   ```

2. **Crear y activar un entorno virtual:**

   ```bash
   python -m venv env
   source env/bin/activate  # En Windows, usa `env\Scripts\activate`
   ```

3. **Instalar las dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Asegurarse de que `ffmpeg` esté instalado:**

   Si `ffmpeg` no está instalado en tu sistema, puedes instalarlo con:

   - **En Windows:** Puedes descargar el ejecutable desde [ffmpeg.org](https://ffmpeg.org/download.html) y agregarlo a tu PATH.
   - **En macOS:** Usando Homebrew: `brew install ffmpeg`
   - **En Linux:** Usando el gestor de paquetes de tu distribución, por ejemplo: `sudo apt-get install ffmpeg`

## Uso de la Aplicación

1. **Ejecutar la aplicación:**

   Inicia el servidor Flask:

   ```bash
   python app.py
   ```

2. **Acceder a la aplicación:**

   Abre tu navegador y dirígete a `http://127.0.0.1:5000`.

3. **Interfaz de Usuario:**

   - Introduce la URL del video de YouTube en el campo correspondiente.
   - Haz clic en **Descargar Video** para descargar el video completo.
   - Haz clic en **Descargar Audio** para descargar solo el audio en formato MP3.

## Detalles Técnicos

### Archivos y Funcionalidad

- **`app.py`**:
  - Maneja las rutas principales para la interfaz de usuario (`/`), descarga de videos (`/download_video`), y descarga de audios (`/download_audio`).
  - Utiliza `yt-dlp` para manejar la descarga y conversión de los videos.
  - Los archivos se descargan temporalmente en la carpeta `downloads`, se envían al cliente, y luego se eliminan automáticamente.

- **`index.html`**:
  - Utiliza Bootstrap para ofrecer una interfaz de usuario moderna y responsiva.
  - Contiene un formulario simple donde los usuarios ingresan la URL de YouTube y eligen la acción deseada.

- **`static/`**:
  - Contiene la imagen que se muestra en la interfaz de usuario. Otros archivos estáticos (CSS, JS) también podrían almacenarse aquí si decides personalizar más la interfaz.

### Manejo de Errores y Limpieza

- La aplicación maneja errores comunes, como la falta de URL o problemas en la descarga, mostrando mensajes claros al usuario.
- Los archivos descargados se almacenan temporalmente y se eliminan automáticamente después de ser enviados al cliente, lo que asegura que el servidor se mantenga limpio.

## Personalización y Extensión

- **Personalización del Frontend:** Puedes modificar el archivo `index.html` para cambiar el diseño, los estilos, o agregar nuevas características.
- **Extensión de Funcionalidad:** Puedes añadir nuevas rutas en `app.py` para integrar más características, como la transcripción automática del audio o la descarga de videos en diferentes formatos.

## Contribuciones

¡Las contribuciones son bienvenidas! Si tienes alguna mejora o encuentras un error, por favor abre un issue o envía un pull request.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

---

Esta documentación te da una visión completa de cómo configurar, usar y extender tu aplicación. También ayuda a otros desarrolladores a entender el propósito del proyecto y cómo pueden contribuir o personalizarlo para sus propias necesidades.

Si necesitas alguna otra adición o modificación, estaré encantado de ayudarte. ¡Buena suerte con tu proyecto!