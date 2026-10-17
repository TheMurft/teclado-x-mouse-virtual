# Teclado x Mouse Virtual — Visor de cámara

Aplicación en Python para mostrar la imagen de una cámara web en tiempo real usando **OpenCV** y detectar los puntos de referencia de una mano mediante **MediaPipe**.

## Requisitos

- Python 3.9 o superior.
- Una cámara web conectada y disponible.
- OpenCV para Python.
- MediaPipe para Python.
- PyAutoGUI para controlar el cursor.

## Instalación

Desde la carpeta del proyecto, instala las dependencias:

```bash
pip install opencv-python mediapipe pyautogui
```

También puedes instalarla usando el intérprete del entorno virtual:

```bash
.venv\Scripts\python.exe -m pip install opencv-python mediapipe pyautogui
```

## Ejecución

```bash
python main.py
```

Al iniciar, el programa utiliza automáticamente la configuración guardada en `config.json`. La cámara predeterminada es la cámara `0` y la resolución inicial es `1920x1080`.

La aplicación procesa cada fotograma con **MediaPipe Tasks Hand Landmarker**, dibuja los 21 puntos de referencia de la mano detectada y muestra el estado de detección junto con los FPS aproximados. También identifica la pinza entre el pulgar y el índice. En el primer inicio descarga automáticamente el modelo `models/hand_landmarker.task` desde el repositorio oficial de modelos de MediaPipe.

## Detección de pinza

La distancia entre el pulgar (landmark 4) y el índice (landmark 8) se calcula en píxeles. La pinza se considera detectada cuando la distancia es menor que `30 px` durante tres fotogramas consecutivos. Para evitar cambios por temblor, la liberación se confirma cuando la distancia supera `40 px` durante tres fotogramas.

El umbral se guarda en `config.json` como `umbral_pinza` y puede ajustarse entre `10` y `100` píxeles sin cambiar el código.

## Controles

- **F1**: abrir o cerrar el menú de configuración.
- **Flechas arriba/abajo**: seleccionar cámara o resolución dentro del menú.
- **Flechas izquierda/derecha**: cambiar el valor seleccionado.
- **Enter**: guardar y aplicar la configuración.
- **Esc**: cancelar los cambios.
- **Q**: cerrar la cámara y salir correctamente.
- **F2**: activar o pausar el control del mouse.

También se pueden usar las teclas `W`, `A`, `S` y `D` como alternativa a las flechas dentro del menú.

## Control del mouse

Presiona **F2** para activar el control. La punta del dedo índice mueve el cursor y la pinza entre pulgar e índice controla automáticamente el clic izquierdo. Presiona **F2** nuevamente para pausar el control. El movimiento se suaviza para reducir los saltos.

La detección es automática. Una pinza corta genera un clic izquierdo. Dos pinzas cortas consecutivas dentro del intervalo normal de Windows se reconocen como doble clic. Si mantienes la pinza aproximadamente `0.45` segundos, se ejecuta `mouseDown`; el botón permanece presionado hasta que separes los dedos y entonces se ejecuta `mouseUp`. Si se pierde la mano o se pausa el mouse, el botón se libera automáticamente.

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
    ],
    "umbral_pinza": 30
}
```

Para volver a los valores iniciales, elimina `config.json` y ejecuta nuevamente el programa.

## Solución de problemas

### OpenCV, MediaPipe o PyAutoGUI no están instalados

Ejecuta:

```bash
pip install opencv-python mediapipe pyautogui
```

También puedes instalar solo MediaPipe si OpenCV ya está disponible:

```bash
pip install mediapipe
```

Si OpenCV y MediaPipe ya están instalados, instala únicamente el control del cursor:

```bash
pip install pyautogui
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
