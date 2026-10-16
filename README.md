# Teclado x Mouse Virtual — Visor de cámara

Aplicación en Python para mostrar la imagen de una cámara web en tiempo real usando **OpenCV** y detectar los puntos de referencia de una mano mediante **MediaPipe**.

## Requisitos

- Python 3.9 o superior.
- Una cámara web conectada y disponible.
- OpenCV para Python.
- MediaPipe para Python.

## Instalación

Desde la carpeta del proyecto, instala las dependencias:

```bash
pip install opencv-python mediapipe
```

También puedes instalarla usando el intérprete del entorno virtual:

```bash
.venv\Scripts\python.exe -m pip install opencv-python mediapipe
```

## Ejecución

```bash
python main.py
```

Al iniciar, el programa utiliza automáticamente la configuración guardada en `config.json`. La cámara predeterminada es la cámara `0` y la resolución inicial es `1920x1080`.

La aplicación procesa cada fotograma con **MediaPipe Tasks Hand Landmarker**, dibuja los 21 puntos de referencia de la mano detectada y muestra el estado de detección junto con los FPS aproximados. En el primer inicio descarga automáticamente el modelo `models/hand_landmarker.task` desde el repositorio oficial de modelos de MediaPipe.

## Controles

- **F1**: abrir o cerrar el menú de configuración.
- **Flechas arriba/abajo**: seleccionar cámara o resolución dentro del menú.
- **Flechas izquierda/derecha**: cambiar el valor seleccionado.
- **Enter**: guardar y aplicar la configuración.
- **Esc**: cancelar los cambios.
- **Q**: cerrar la cámara y salir correctamente.

También se pueden usar las teclas `W`, `A`, `S` y `D` como alternativa a las flechas dentro del menú.

## Cámaras disponibles

El menú permite probar los índices de cámara `0`, `1`, `2`, `3` y `4`.

OpenCV identifica los dispositivos por índice, por lo que el nombre mostrado será `Cámara 0`, `Cámara 1`, etc. Si una cámara no existe o está siendo utilizada por otra aplicación, el programa mostrará un mensaje de error.

## Resoluciones

El menú incluye estas resoluciones:

1. `640x480` — VGA
2. `1280x720` — HD
3. `1920x1080` — Full HD

Al aplicar una resolución, el tamaño de la ventana se actualiza automáticamente.

## Configuración persistente

Las preferencias se guardan automáticamente en `config.json` al presionar **Enter** en el menú:

```json
{
    "indice_camara": 0,
    "resolucion": [
        1920,
        1080
    ]
}
```

Para volver a los valores iniciales, elimina `config.json` y ejecuta nuevamente el programa.

## Solución de problemas

### OpenCV o MediaPipe no están instalados

Ejecuta:

```bash
pip install opencv-python mediapipe
```

También puedes instalar solo MediaPipe si OpenCV ya está disponible:

```bash
pip install mediapipe
```

Si el primer inicio no puede descargar el modelo, descarga `hand_landmarker.task` desde la URL oficial indicada por el programa y guárdalo en la carpeta `models` del proyecto.

### No se puede abrir la cámara

Comprueba lo siguiente:

1. La cámara está conectada.
2. Otra aplicación no la está utilizando.
3. Windows permite el acceso a la cámara para Python o PyCharm.
4. Has seleccionado el índice correcto en el menú F1.

### La resolución no es exactamente la solicitada

Algunas cámaras solo admiten determinadas resoluciones. OpenCV solicita la resolución elegida, pero el controlador de la cámara puede seleccionar la más cercana disponible.
