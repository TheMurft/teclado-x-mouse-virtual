import json
import math
import time
from pathlib import Path
from urllib.request import urlretrieve

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
except ImportError:
    mp = None
    mp_python = None
    vision = None


NOMBRE_VENTANA = "Cámara"
ARCHIVO_CONFIGURACION = Path(__file__).with_name("config.json")
ARCHIVO_MODELO = Path(__file__).with_name("models") / "hand_landmarker.task"
URL_MODELO = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
CONEXIONES_MANO = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
)
RESOLUCIONES = (
    (640, 480),
    (1280, 720),
    (1920, 1080),
)
CAMARA_PREDETERMINADA = 0
RESOLUCION_PREDETERMINADA = RESOLUCIONES[2]
CAMARAS_EN_MENU = 5
UMBRAL_PINZA_PREDETERMINADO = 30
UMBRAL_CLIC_DERECHO = 40
FRAMES_ESTABLES_PINZA = 3
TIEMPO_RESPUESTA_CURSOR = 0.08
MARGEN_CURSOR = 0.08
TIEMPO_CLIC_SOSTENIDO = 0.45
FRAMES_ESTABLES_PUNO = 4
INTERVALO_CAPTURA_SEGUNDOS = 1.5
UMBRAL_PULGARES_JUNTOS = 60
TIEMPO_ACTIVACION_MOUSE = 2.0
TIEMPO_DESACTIVAR_MODOS = 0.8
TECLAS_VIRTUALES = (
    ("Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"),
    ("A", "S", "D", "F", "G", "H", "J", "K", "L", ";"),
    ("Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"),
    ("COPIAR", "PEGAR"),
)
ANCHO_TECLA_VIRTUAL = 0.085
ALTO_TECLA_VIRTUAL = 52
SEPARACION_TECLA_VIRTUAL = 6
FRAMES_TECLA_VIRTUAL = 3


def configuracion_predeterminada():

    return {
        "indice_camara": CAMARA_PREDETERMINADA,
        "resolucion": list(RESOLUCION_PREDETERMINADA),
        "umbral_pinza": UMBRAL_PINZA_PREDETERMINADO,
    }


def cargar_configuracion():

    configuracion = configuracion_predeterminada()

    try:
        with ARCHIVO_CONFIGURACION.open("r", encoding="utf-8") as archivo:
            guardada = json.load(archivo)

        if not isinstance(guardada, dict):
            return configuracion

        indice = guardada.get("indice_camara", CAMARA_PREDETERMINADA)
        resolucion = tuple(guardada.get("resolucion", RESOLUCION_PREDETERMINADA))
        umbral_pinza = guardada.get("umbral_pinza", UMBRAL_PINZA_PREDETERMINADO)

        if isinstance(indice, int) and not isinstance(indice, bool) and indice >= 0:
            configuracion["indice_camara"] = indice
        if resolucion in RESOLUCIONES:
            configuracion["resolucion"] = list(resolucion)
        if (
            isinstance(umbral_pinza, (int, float))
            and not isinstance(umbral_pinza, bool)
            and math.isfinite(umbral_pinza)
            and 10 <= umbral_pinza <= 100
        ):
            configuracion["umbral_pinza"] = float(umbral_pinza)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):

        pass

    return configuracion


def guardar_configuracion(indice_camara, resolucion, umbral_pinza=None):

    configuracion = {
        "indice_camara": indice_camara,
        "resolucion": list(resolucion),
        "umbral_pinza": (
            UMBRAL_PINZA_PREDETERMINADO
            if umbral_pinza is None
            else umbral_pinza
        ),
    }
    try:
        with ARCHIVO_CONFIGURACION.open("w", encoding="utf-8") as archivo:
            json.dump(configuracion, archivo, indent=4, ensure_ascii=False)
    except OSError as error:
        print(f"Error: no se pudo guardar {ARCHIVO_CONFIGURACION.name}: {error}")


def nombre_camara(indice_camara):


    return f"Cámara {indice_camara}"


def abrir_camara(indice_camara, resolucion):

    camara = cv2.VideoCapture(indice_camara)
    if not camara.isOpened():
        camara.release()
        return None

    ancho, alto = resolucion
    camara.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
    camara.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
    return camara


def obtener_resolucion_camara(camara, alternativa):

    try:
        ancho = int(camara.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(camara.get(cv2.CAP_PROP_FRAME_HEIGHT))
    except (OverflowError, TypeError, ValueError):
        return tuple(alternativa)
    if ancho > 0 and alto > 0:
        return ancho, alto
    return tuple(alternativa)


def es_tecla_f1(tecla):


    return tecla in (0x70000, 0x700000, 65470) or ((tecla >> 16) & 0xFF) == 0x70


def es_tecla_f2(tecla):

    return tecla in (0x71, 0x70001, 0x710000, 65471) or ((tecla >> 16) & 0xFF) == 0x71


def dibujar_menu(imagen, indice_camara, indice_resolucion, opcion, mensaje=""):

    alto, ancho = imagen.shape[:2]
    panel = imagen.copy()
    borde_derecho = min(ancho - 30, 780)
    borde_inferior = min(alto - 30, 430)
    cv2.rectangle(panel, (30, 30), (borde_derecho, borde_inferior), (20, 20, 20), -1)
    imagen[:] = cv2.addWeighted(panel, 0.88, imagen, 0.12, 0)
    cv2.rectangle(imagen, (30, 30), (borde_derecho, borde_inferior), (0, 180, 255), 2)

    resolucion = RESOLUCIONES[indice_resolucion]
    selector_camara = ">>" if opcion == 0 else "  "
    selector_resolucion = ">>" if opcion == 1 else "  "
    lineas = [
        "MENU DE CONFIGURACION",
        f"{selector_camara} Camara:       {nombre_camara(indice_camara)}",
        f"{selector_resolucion} Resolucion:   {resolucion[0]}x{resolucion[1]}",
        "",
        "ARRIBA / ABAJO   Seleccionar opcion",
        "IZQUIERDA / DERECHA   Cambiar valor",
        "ENTER   Guardar y aplicar",
        "ESC   Cancelar     F1   Cerrar menu",
    ]
    if mensaje:
        lineas.append(mensaje)

    for numero, linea in enumerate(lineas):
        color = (0, 220, 255) if numero == 0 else (235, 235, 235)
        cv2.putText(
            imagen,
            linea,
            (55, 75 + numero * 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )


def obtener_indice_resolucion(resolucion):

    try:
        return RESOLUCIONES.index(tuple(resolucion))
    except ValueError:
        return RESOLUCIONES.index(RESOLUCION_PREDETERMINADA)


def asegurar_modelo_manos():

    if ARCHIVO_MODELO.exists() and ARCHIVO_MODELO.stat().st_size > 0:
        return True

    try:
        ARCHIVO_MODELO.parent.mkdir(parents=True, exist_ok=True)
        print("Descargando el modelo de detección de manos...")
        urlretrieve(URL_MODELO, ARCHIVO_MODELO)
        return ARCHIVO_MODELO.exists() and ARCHIVO_MODELO.stat().st_size > 0
    except (OSError, ValueError) as error:
        try:
            if ARCHIVO_MODELO.exists():
                ARCHIVO_MODELO.unlink()
        except OSError:
            pass
        print(f"Error: no se pudo descargar el modelo de MediaPipe: {error}")
        print(f"Descárgalo manualmente desde: {URL_MODELO}")
        print(f"Guárdalo como: {ARCHIVO_MODELO}")
        return False


def dibujar_landmarks_mano(imagen, landmarks):

    alto, ancho = imagen.shape[:2]
    puntos = []

    for landmark in landmarks:
        x = min(max(int(landmark.x * ancho), 0), ancho - 1)
        y = min(max(int(landmark.y * alto), 0), alto - 1)
        puntos.append((x, y))

    for inicio, fin in CONEXIONES_MANO:
        cv2.line(imagen, puntos[inicio], puntos[fin], (255, 180, 0), 2, cv2.LINE_AA)

    for punto in puntos:
        cv2.circle(imagen, punto, 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(imagen, punto, 5, (40, 120, 255), 1, cv2.LINE_AA)


def distancia_pulgar_indice(landmarks, ancho, alto):

    pulgar = landmarks[4]
    indice = landmarks[8]
    pulgar_xy = (pulgar.x * ancho, pulgar.y * alto)
    indice_xy = (indice.x * ancho, indice.y * alto)
    return math.hypot(
        indice_xy[0] - pulgar_xy[0],
        indice_xy[1] - pulgar_xy[1],
    ), pulgar_xy, indice_xy


def distancia_pulgar_medio(landmarks, ancho, alto):

    pulgar = landmarks[4]
    medio = landmarks[12]
    pulgar_xy = (pulgar.x * ancho, pulgar.y * alto)
    medio_xy = (medio.x * ancho, medio.y * alto)
    return math.hypot(
        medio_xy[0] - pulgar_xy[0],
        medio_xy[1] - pulgar_xy[1],
    ), pulgar_xy, medio_xy


def actualizar_estado_pinza(distancia, pinza_activa, frames_candidatos, umbral):

    umbral_liberacion = max(umbral + 10, umbral * 1.25)
    if pinza_activa:
        if distancia > umbral_liberacion:
            frames_candidatos += 1
            if frames_candidatos >= FRAMES_ESTABLES_PINZA:
                return False, 0
        else:
            frames_candidatos = 0
        return True, frames_candidatos

    if distancia < umbral:
        frames_candidatos += 1
        if frames_candidatos >= FRAMES_ESTABLES_PINZA:
            return True, 0
    else:
        frames_candidatos = 0
    return False, frames_candidatos


def obtener_lateralidad_mano(resultado_manos, indice_mano):


    try:
        clasificaciones = resultado_manos.handedness[indice_mano]
        if not clasificaciones:
            return "DESCONOCIDA"

        clasificacion = clasificaciones[0]
        nombre = getattr(clasificacion, "category_name", "").lower()
        confianza = getattr(clasificacion, "score", None)
        lateralidad = {
            "left": "DERECHA",
            "right": "IZQUIERDA",
        }.get(nombre, nombre.upper() or "DESCONOCIDA")
        if isinstance(confianza, (int, float)):
            return f"{lateralidad} ({confianza:.0%})"
        return lateralidad
    except (AttributeError, IndexError, TypeError):
        return "DESCONOCIDA"


def es_mano_derecha(resultado_manos, indice_mano):

    try:
        clasificacion = resultado_manos.handedness[indice_mano][0]
        return getattr(clasificacion, "category_name", "").lower() == "left"
    except (AttributeError, IndexError, TypeError):
        return False


def es_mano_izquierda(resultado_manos, indice_mano):

    try:
        clasificacion = resultado_manos.handedness[indice_mano][0]
        return getattr(clasificacion, "category_name", "").lower() == "right"
    except (AttributeError, IndexError, TypeError):
        return False


def mano_cerrada(landmarks):

    pares_dedo = ((8, 6), (12, 10), (16, 14), (20, 18))
    dedos_cerrados = sum(
        1 for punta, articulacion in pares_dedo
        if landmarks[punta].y > landmarks[articulacion].y
    )
    return dedos_cerrados >= 3


def distancia_pulgares(landmarks_a, landmarks_b, ancho, alto):

    pulgar_a = landmarks_a[4]
    pulgar_b = landmarks_b[4]
    return math.hypot(
        (pulgar_a.x - pulgar_b.x) * ancho,
        (pulgar_a.y - pulgar_b.y) * alto,
    )


def distancia_pulgar_dedo(landmarks, indice_dedo, ancho, alto):

    pulgar = landmarks[4]
    dedo = landmarks[indice_dedo]
    return math.hypot(
        (pulgar.x - dedo.x) * ancho,
        (pulgar.y - dedo.y) * alto,
    )


def construir_teclado_visual(ancho, alto):

    teclado = []
    margen = max(18, int(ancho * 0.035))
    separacion = max(4, int(ancho * 0.006))
    alto_tecla = max(38, min(ALTO_TECLA_VIRTUAL, int(alto * 0.075)))
    ancho_disponible = ancho - 2 * margen
    ancho_tecla = (ancho_disponible - separacion * 9) / 10
    y_inicial = alto - (alto_tecla * len(TECLAS_VIRTUALES) + separacion * (len(TECLAS_VIRTUALES) - 1)) - max(18, int(alto * 0.03))

    for fila, teclas in enumerate(TECLAS_VIRTUALES):
        cantidad_teclas = len(teclas)
        ancho_tecla_fila = (
            ancho_disponible - separacion * (cantidad_teclas - 1)
        ) / cantidad_teclas
        desplazamiento = (ancho - (ancho_tecla_fila * cantidad_teclas + separacion * (cantidad_teclas - 1))) / 2
        for columna, etiqueta in enumerate(teclas):
            x1 = int(desplazamiento + columna * (ancho_tecla_fila + separacion))
            y1 = int(y_inicial + fila * (alto_tecla + separacion))
            teclado.append((etiqueta, x1, y1, int(x1 + ancho_tecla_fila), y1 + alto_tecla))
    return teclado


def tecla_bajo_punto(teclado, x, y):

    for tecla in teclado:
        etiqueta, x1, y1, x2, y2 = tecla
        if x1 <= x <= x2 and y1 <= y <= y2:
            return tecla
    return None


def dibujar_teclado_visual(imagen, teclado, tecla_seleccionada, tecla_presionada):

    for etiqueta, x1, y1, x2, y2 in teclado:
        bajo_indice = etiqueta == tecla_seleccionada
        presionada = etiqueta == tecla_presionada
        color_relleno = (0, 190, 80) if presionada else (0, 120, 220) if bajo_indice else (45, 45, 55)
        color_borde = (80, 255, 120) if presionada else (0, 240, 255) if bajo_indice else (180, 180, 190)
        cv2.rectangle(imagen, (x1, y1), (x2, y2), color_relleno, -1)
        cv2.rectangle(imagen, (x1, y1), (x2, y2), color_borde, 2)
        escala = 0.65 if len(etiqueta) == 1 else 0.42
        tam, _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, escala, 2)
        cv2.putText(
            imagen,
            etiqueta,
            (x1 + (x2 - x1 - tam[0]) // 2, y1 + (y2 - y1 + tam[1]) // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            escala,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def ejecutar_tecla_virtual(etiqueta):

    if etiqueta == "COPIAR":
        pyautogui.hotkey("ctrl", "c")
    elif etiqueta == "PEGAR":
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.press(etiqueta.lower())


def mostrar_camara():

    if cv2 is None:
        print(
            "Error: OpenCV no está instalado. "
            "Instálalo con: pip install opencv-python"
        )
        return

    if mp is None or mp_python is None or vision is None:
        print(
            "Error: MediaPipe Tasks no está disponible. "
            "Instálalo con: pip install --upgrade mediapipe"
        )
        return

    if pyautogui is None:
        print(
            "Error: PyAutoGUI no está instalado. "
            "Instálalo con: pip install pyautogui"
        )
        return

    if not asegurar_modelo_manos():
        return

    opciones_manos = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(ARCHIVO_MODELO)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    manos = vision.HandLandmarker.create_from_options(opciones_manos)

    configuracion = cargar_configuracion()
    indice_camara = configuracion["indice_camara"]
    indice_resolucion_config = obtener_indice_resolucion(configuracion["resolucion"])
    resolucion = RESOLUCIONES[indice_resolucion_config]
    umbral_pinza = configuracion["umbral_pinza"]
    camara = abrir_camara(indice_camara, resolucion)

    if camara is None:
        manos.close()
        print(
            f"Error: no se pudo abrir {nombre_camara(indice_camara)}. "
            "Verifica que esté conectada y que ninguna otra aplicación la use."
        )
        return


    guardar_configuracion(indice_camara, resolucion, umbral_pinza)
    menu_abierto = False
    opcion_menu = 0
    mensaje_menu = ""
    ultimo_tiempo = time.perf_counter()
    inicio_video = ultimo_tiempo
    ultimo_timestamp_ms = -1
    fps = 0.0
    pinza_activa = False
    frames_candidatos_pinza = 0
    control_mouse_activo = False
    teclado_visual_activo = False
    cursor_x = None
    cursor_y = None
    pantalla_ancho, pantalla_alto = pyautogui.size()
    pyautogui.PAUSE = 0
    boton_presionado = False
    inicio_pinza = None
    pinza_anterior = False
    pinza_medio_activa = False
    frames_candidatos_medio = 0
    pinza_medio_anterior = False
    frames_puno_izquierdo = 0
    puno_izquierdo_activo = False
    ultima_captura = 0.0
    inicio_pulgares_juntos = None
    gesto_pulgares_resuelto = False
    inicio_indices_juntos = None
    gesto_indices_resuelto = False
    pinza_copiar_activa = False
    frames_candidatos_copiar = 0
    pinza_copiar_anterior = False
    pinza_pegar_activa = False
    frames_candidatos_pegar = 0
    pinza_pegar_anterior = False
    tecla_candidata = None
    frames_tecla_candidata = 0
    tecla_virtual_bloqueada = False
    tecla_virtual_presionada = None

    try:
        cv2.namedWindow(NOMBRE_VENTANA, cv2.WINDOW_NORMAL)
        resolucion_real = obtener_resolucion_camara(camara, resolucion)
        cv2.resizeWindow(NOMBRE_VENTANA, resolucion_real[0], resolucion_real[1])

        while True:
            lectura_exitosa, imagen = camara.read()
            if not lectura_exitosa:
                print("Error: no se pudo leer una imagen de la cámara.")
                break
            imagen = cv2.flip(imagen, 1)
            teclado_visual = construir_teclado_visual(imagen.shape[1], imagen.shape[0])
            tecla_hover_actual = None

            tiempo_actual = time.perf_counter()
            intervalo = tiempo_actual - ultimo_tiempo
            ultimo_tiempo = tiempo_actual
            if intervalo > 0:
                fps = 1.0 / intervalo

            imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
            timestamp_ms = max(
                ultimo_timestamp_ms + 1,
                int((tiempo_actual - inicio_video) * 1000),
            )
            ultimo_timestamp_ms = timestamp_ms
            imagen_mediapipe = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=imagen_rgb,
            )
            resultado_manos = manos.detect_for_video(imagen_mediapipe, timestamp_ms)
            mano_detectada = bool(resultado_manos.hand_landmarks)
            distancia = None
            pulgar_xy = None
            indice_xy = None
            distancia_medio = None
            medio_xy = None
            pinza_anterior = pinza_activa
            pinza_medio_anterior = pinza_medio_activa
            pinza_copiar_anterior = pinza_copiar_activa
            pinza_pegar_anterior = pinza_pegar_activa
            mano_derecha_detectada = False
            mano_izquierda_detectada = False
            puno_izquierdo_actual = False
            landmarks_derecha = None
            landmarks_izquierda = None

            if mano_detectada:
                for numero_mano, puntos_mano in enumerate(resultado_manos.hand_landmarks):
                    dibujar_landmarks_mano(imagen, puntos_mano)
                    punta_indice = puntos_mano[8]
                    lateralidad = obtener_lateralidad_mano(resultado_manos, numero_mano)
                    cv2.putText(
                        imagen,
                        f"{lateralidad} | Mano {numero_mano + 1}",
                        (max(int(punta_indice.x * imagen.shape[1]) - 45, 5),
                         max(int(punta_indice.y * imagen.shape[0]) - 15, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 220, 100),
                        2,
                        cv2.LINE_AA,
                    )
                    if es_mano_izquierda(resultado_manos, numero_mano):
                        mano_izquierda_detectada = True
                        landmarks_izquierda = puntos_mano
                        puno_izquierdo_actual = mano_cerrada(puntos_mano)
                        if puno_izquierdo_actual:
                            frames_puno_izquierdo += 1
                            if (
                                frames_puno_izquierdo >= FRAMES_ESTABLES_PUNO
                                and not puno_izquierdo_activo
                                and tiempo_actual - ultima_captura >= INTERVALO_CAPTURA_SEGUNDOS
                            ):
                                try:
                                    pyautogui.hotkey("winleft", "printscreen")
                                    ultima_captura = tiempo_actual
                                    puno_izquierdo_activo = True
                                    print("Captura de pantalla completa realizada.")
                                except Exception as error:
                                    print(f"Error al realizar la captura de pantalla: {error}")
                        else:
                            frames_puno_izquierdo = 0
                            puno_izquierdo_activo = False
                        continue

                    if not es_mano_derecha(resultado_manos, numero_mano):
                        continue
                    mano_derecha_detectada = True
                    landmarks_derecha = puntos_mano
                    if control_mouse_activo and not menu_abierto:
                        x_normalizado = min(
                            max((punta_indice.x - MARGEN_CURSOR) / (1 - 2 * MARGEN_CURSOR), 0.0),
                            1.0,
                        )
                        y_normalizado = min(
                            max((punta_indice.y - MARGEN_CURSOR) / (1 - 2 * MARGEN_CURSOR), 0.0),
                            1.0,
                        )
                        objetivo_x = x_normalizado * (pantalla_ancho - 1)
                        objetivo_y = y_normalizado * (pantalla_alto - 1)
                        if cursor_x is None or cursor_y is None:
                            cursor_x, cursor_y = objetivo_x, objetivo_y
                        else:
                            factor_suavizado = 1 - math.exp(
                                -intervalo / TIEMPO_RESPUESTA_CURSOR
                            )
                            cursor_x += (objetivo_x - cursor_x) * factor_suavizado
                            cursor_y += (objetivo_y - cursor_y) * factor_suavizado
                        pyautogui.moveTo(round(cursor_x), round(cursor_y), duration=0)
                    distancia, pulgar_xy, indice_xy = distancia_pulgar_indice(
                        puntos_mano,
                        imagen.shape[1],
                        imagen.shape[0],
                    )
                    pinza_activa, frames_candidatos_pinza = actualizar_estado_pinza(
                        distancia,
                        pinza_activa,
                        frames_candidatos_pinza,
                        umbral_pinza,
                    )
                    if control_mouse_activo and not menu_abierto:
                        if pinza_activa and not pinza_anterior:
                            inicio_pinza = tiempo_actual
                        elif pinza_activa and inicio_pinza is not None:
                            if (
                                tiempo_actual - inicio_pinza >= TIEMPO_CLIC_SOSTENIDO
                                and not boton_presionado
                            ):
                                pyautogui.mouseDown(button="left")
                                boton_presionado = True
                        elif not pinza_activa and pinza_anterior:
                            if boton_presionado:
                                pyautogui.mouseUp(button="left")
                                boton_presionado = False
                            else:
                                pyautogui.click()
                            inicio_pinza = None
                    distancia_medio, _, medio_xy = distancia_pulgar_medio(
                        puntos_mano,
                        imagen.shape[1],
                        imagen.shape[0],
                    )
                    pinza_medio_activa, frames_candidatos_medio = actualizar_estado_pinza(
                        distancia_medio,
                        pinza_medio_activa,
                        frames_candidatos_medio,
                        UMBRAL_CLIC_DERECHO,
                    )
                    if (
                        control_mouse_activo
                        and not menu_abierto
                        and not pinza_medio_activa
                        and pinza_medio_anterior
                    ):
                        pyautogui.rightClick()
                    cv2.line(
                        imagen,
                        tuple(map(int, pulgar_xy)),
                        tuple(map(int, indice_xy)),
                        (0, 255, 255) if pinza_activa else (160, 160, 160),
                        3,
                        cv2.LINE_AA,
                    )
                    cv2.line(
                        imagen,
                        tuple(map(int, pulgar_xy)),
                        tuple(map(int, medio_xy)),
                        (0, 140, 255) if pinza_medio_activa else (100, 100, 100),
                        2,
                        cv2.LINE_AA,
                    )

            distancia_copiar = None
            distancia_pegar = None


            if not teclado_visual_activo and landmarks_izquierda is not None:
                distancia_copiar = distancia_pulgar_dedo(
                    landmarks_izquierda, 8, imagen.shape[1], imagen.shape[0]
                )
                pinza_copiar_activa, frames_candidatos_copiar = actualizar_estado_pinza(
                    distancia_copiar,
                    pinza_copiar_activa,
                    frames_candidatos_copiar,
                    umbral_pinza,
                )
                if not pinza_copiar_activa and pinza_copiar_anterior:
                    pyautogui.hotkey("ctrl", "c")

                distancia_pegar = distancia_pulgar_dedo(
                    landmarks_izquierda, 12, imagen.shape[1], imagen.shape[0]
                )
                pinza_pegar_activa, frames_candidatos_pegar = actualizar_estado_pinza(
                    distancia_pegar,
                    pinza_pegar_activa,
                    frames_candidatos_pegar,
                    umbral_pinza,
                )
                if not pinza_pegar_activa and pinza_pegar_anterior:
                    pyautogui.hotkey("ctrl", "v")
            else:
                pinza_copiar_activa = False
                frames_candidatos_copiar = 0
                pinza_pegar_activa = False
                frames_candidatos_pegar = 0


            if teclado_visual_activo and not menu_abierto:
                candidatos_teclado = []
                for mano_teclado in (landmarks_derecha, landmarks_izquierda):
                    if mano_teclado is None:
                        continue
                    punta_indice = mano_teclado[8]
                    x_indice = int(punta_indice.x * imagen.shape[1])
                    y_indice = int(punta_indice.y * imagen.shape[0])
                    tecla_detectada = tecla_bajo_punto(teclado_visual, x_indice, y_indice)
                    distancia_teclado = math.hypot(
                        (mano_teclado[4].x - mano_teclado[8].x) * imagen.shape[1],
                        (mano_teclado[4].y - mano_teclado[8].y) * imagen.shape[0],
                    )
                    if tecla_detectada is not None and distancia_teclado < UMBRAL_PINZA_PREDETERMINADO:
                        candidatos_teclado.append(tecla_detectada[0])
                    elif tecla_detectada is not None and not candidatos_teclado:
                        tecla_hover_actual = tecla_detectada[0]
                if candidatos_teclado:
                    tecla_hover_actual = candidatos_teclado[0]
                    if tecla_hover_actual == tecla_candidata:
                        frames_tecla_candidata += 1
                    else:
                        tecla_candidata = tecla_hover_actual
                        frames_tecla_candidata = 1
                    if (
                        frames_tecla_candidata >= FRAMES_TECLA_VIRTUAL
                        and not tecla_virtual_bloqueada
                    ):
                        ejecutar_tecla_virtual(tecla_candidata)
                        tecla_virtual_bloqueada = True
                        tecla_virtual_presionada = tecla_candidata
                else:
                    frames_tecla_candidata = 0
                    tecla_candidata = None
                    tecla_virtual_bloqueada = False
                    tecla_virtual_presionada = None
            else:
                tecla_candidata = None
                frames_tecla_candidata = 0
                tecla_virtual_bloqueada = False
                tecla_virtual_presionada = None

            if landmarks_izquierda is not None:
                pulgar_izquierdo = landmarks_izquierda[4]
                indice_izquierdo = landmarks_izquierda[8]
                medio_izquierdo = landmarks_izquierda[12]
                pulgar_xy_izquierdo = (
                    int(pulgar_izquierdo.x * imagen.shape[1]),
                    int(pulgar_izquierdo.y * imagen.shape[0]),
                )
                indice_xy_izquierdo = (
                    int(indice_izquierdo.x * imagen.shape[1]),
                    int(indice_izquierdo.y * imagen.shape[0]),
                )
                medio_xy_izquierdo = (
                    int(medio_izquierdo.x * imagen.shape[1]),
                    int(medio_izquierdo.y * imagen.shape[0]),
                )
                cv2.line(
                    imagen,
                    pulgar_xy_izquierdo,
                    indice_xy_izquierdo,
                    (0, 255, 0) if pinza_copiar_activa else (80, 100, 80),
                    3,
                    cv2.LINE_AA,
                )
                cv2.line(
                    imagen,
                    pulgar_xy_izquierdo,
                    medio_xy_izquierdo,
                    (255, 120, 0) if pinza_pegar_activa else (100, 80, 60),
                    3,
                    cv2.LINE_AA,
                )

            distancia_pulgares_actual = None
            segundos_pulgares = 0.0
            if landmarks_derecha is not None and landmarks_izquierda is not None:
                distancia_pulgares_actual = distancia_pulgares(
                    landmarks_derecha,
                    landmarks_izquierda,
                    imagen.shape[1],
                    imagen.shape[0],
                )
                if distancia_pulgares_actual <= UMBRAL_PULGARES_JUNTOS:
                    if inicio_pulgares_juntos is None:
                        inicio_pulgares_juntos = tiempo_actual
                        gesto_pulgares_resuelto = False
                    segundos_pulgares = tiempo_actual - inicio_pulgares_juntos
                    if segundos_pulgares >= TIEMPO_ACTIVACION_MOUSE and not gesto_pulgares_resuelto:
                        if control_mouse_activo:
                            control_mouse_activo = False
                            teclado_visual_activo = True
                        else:
                            control_mouse_activo = True
                            teclado_visual_activo = False
                        gesto_pulgares_resuelto = True
                        cursor_x = None
                        cursor_y = None
                        pinza_activa = False
                        frames_candidatos_pinza = 0
                        pinza_medio_activa = False
                        frames_candidatos_medio = 0
                        inicio_pinza = None
                        if not control_mouse_activo and boton_presionado:
                            pyautogui.mouseUp(button="left")
                            boton_presionado = False
                else:
                    inicio_pulgares_juntos = None
                    gesto_pulgares_resuelto = False
            else:
                inicio_pulgares_juntos = None
                gesto_pulgares_resuelto = False

            distancia_indices_actual = None
            if landmarks_derecha is not None and landmarks_izquierda is not None:
                indice_derecho = landmarks_derecha[8]
                indice_izquierdo = landmarks_izquierda[8]
                distancia_indices_actual = math.hypot(
                    (indice_derecho.x - indice_izquierdo.x) * imagen.shape[1],
                    (indice_derecho.y - indice_izquierdo.y) * imagen.shape[0],
                )
                if distancia_indices_actual <= UMBRAL_PULGARES_JUNTOS:
                    if inicio_indices_juntos is None:
                        inicio_indices_juntos = tiempo_actual
                        gesto_indices_resuelto = False
                    if (
                        tiempo_actual - inicio_indices_juntos >= TIEMPO_DESACTIVAR_MODOS
                        and not gesto_indices_resuelto
                    ):
                        control_mouse_activo = False
                        teclado_visual_activo = False
                        gesto_indices_resuelto = True
                        if boton_presionado:
                            pyautogui.mouseUp(button="left")
                            boton_presionado = False
                else:
                    inicio_indices_juntos = None
                    gesto_indices_resuelto = False
            else:
                inicio_indices_juntos = None
                gesto_indices_resuelto = False

            if not mano_izquierda_detectada:
                frames_puno_izquierdo = 0
                puno_izquierdo_activo = False

            if not mano_derecha_detectada:
                pinza_activa = False
                frames_candidatos_pinza = 0
                pinza_sostenida = boton_presionado
                if boton_presionado:
                    pyautogui.mouseUp(button="left")
                    boton_presionado = False
                if control_mouse_activo and pinza_anterior and not pinza_sostenida:
                    pyautogui.click()
                inicio_pinza = None
                pinza_medio_activa = False
                frames_candidatos_medio = 0
                if control_mouse_activo and pinza_medio_anterior:
                    pyautogui.rightClick()

            cantidad_manos = len(resultado_manos.hand_landmarks)
            estado_mano = (
                f"{cantidad_manos} MANO(S) DETECTADA(S)"
                if mano_detectada
                else "SIN MANO"
            )
            color_estado = (255, 255, 255) if mano_detectada else (80, 180, 255)
            cv2.putText(
                imagen,
                f"{estado_mano} | FPS: {fps:.1f}",
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color_estado,
                2,
                cv2.LINE_AA,
            )
            if control_mouse_activo:
                estado_modo = "MODO MOUSE ACTIVO"
            elif teclado_visual_activo:
                estado_modo = "MODO TECLADO ACTIVO"
            else:
                estado_modo = "MOUSE Y TECLADO DESACTIVADOS"
            cv2.putText(
                imagen,
                estado_modo,
                (15, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (0, 220, 255) if control_mouse_activo else (0, 255, 120) if teclado_visual_activo else (180, 180, 180),
                2,
                cv2.LINE_AA,
            )
            if distancia_pulgares_actual is not None and inicio_pulgares_juntos is not None:
                cv2.putText(
                    imagen,
                    f"PULGARES JUNTOS: {min(segundos_pulgares, TIEMPO_ACTIVACION_MOUSE):.1f}/{TIEMPO_ACTIVACION_MOUSE:.1f} s",
                    (15, 260),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 180, 0),
                    2,
                    cv2.LINE_AA,
                )
            modo_clic = "CLIC AUTOMATICO: CORTO / SOSTENIDO"
            cv2.putText(
                imagen,
                modo_clic,
                (15, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 220, 255) if control_mouse_activo else (170, 170, 170),
                2,
                cv2.LINE_AA,
            )
            if distancia is not None:
                estado_pinza = "PINZA DETECTADA" if pinza_activa else "MANO ABIERTA"
                color_pinza = (0, 255, 255) if pinza_activa else (235, 235, 235)
                cv2.putText(
                    imagen,
                    f"{estado_pinza} | Distancia: {distancia:.1f}px / Umbral: {umbral_pinza:.0f}px",
                    (15, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.58,
                    color_pinza,
                    2,
                    cv2.LINE_AA,
                )
            if distancia_medio is not None:
                estado_medio = "CLIC DERECHO LISTO" if pinza_medio_activa else "MEDIO ABIERTO"
                cv2.putText(
                    imagen,
                    f"{estado_medio} | Pulgar-medio: {distancia_medio:.1f}px",
                    (15, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 140, 255) if pinza_medio_activa else (190, 190, 190),
                    2,
                    cv2.LINE_AA,
                )
            estado_captura = (
                "PUÑO IZQUIERDO: CAPTURA"
                if puno_izquierdo_actual
                else "CAPTURA: PUÑO IZQUIERDO"
            )
            cv2.putText(
                imagen,
                estado_captura,
                (15, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (0, 255, 0) if puno_izquierdo_actual else (170, 170, 170),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                imagen,
                (
                    "COPIAR / PEGAR: USA LOS BOTONES DEL TECLADO"
                    if teclado_visual_activo
                    else "COPIAR: PULGAR + INDICE IZQUIERDO" + (" [LISTO]" if pinza_copiar_activa else "")
                ),
                (15, 210),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (0, 255, 0) if pinza_copiar_activa else (170, 170, 170),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                imagen,
                "PULGAR + INDICE PARA PULSAR TECLAS" if teclado_visual_activo else "PEGAR: PULGAR + MEDIO IZQUIERDO" + (" [LISTO]" if pinza_pegar_activa else ""),
                (15, 235),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 120, 0) if pinza_pegar_activa else (170, 170, 170),
                2,
                cv2.LINE_AA,
            )
            if teclado_visual_activo and not menu_abierto:
                dibujar_teclado_visual(
                    imagen,
                    teclado_visual,
                    tecla_hover_actual,
                    tecla_virtual_presionada,
                )
            if menu_abierto:
                dibujar_menu(imagen, indice_camara, indice_resolucion_config, opcion_menu, mensaje_menu)

            cv2.imshow(NOMBRE_VENTANA, imagen)
            tecla = cv2.waitKeyEx(1)
            tecla_simple = tecla & 0xFF

            if tecla_simple in (ord("q"), ord("Q")):
                break

            if es_tecla_f1(tecla):
                menu_abierto = not menu_abierto
                mensaje_menu = ""
                if menu_abierto and boton_presionado:
                    pyautogui.mouseUp(button="left")
                    boton_presionado = False
                pinza_medio_activa = False
                frames_candidatos_medio = 0
                inicio_pinza = None
                continue

            if es_tecla_f2(tecla) and not menu_abierto:
                if control_mouse_activo:
                    control_mouse_activo = False
                    teclado_visual_activo = True
                elif teclado_visual_activo:
                    control_mouse_activo = True
                    teclado_visual_activo = False
                else:
                    teclado_visual_activo = True
                cursor_x = None
                cursor_y = None
                pinza_activa = False
                frames_candidatos_pinza = 0
                inicio_pinza = None
                pinza_medio_activa = False
                frames_candidatos_medio = 0
                pinza_medio_anterior = False
                if not control_mouse_activo and boton_presionado:
                    pyautogui.mouseUp(button="left")
                    boton_presionado = False
                continue

            if not menu_abierto:
                continue

            if tecla_simple == 27:
                menu_abierto = False
                mensaje_menu = "Cambios cancelados."
            elif tecla_simple in (13, 10):
                nueva_resolucion = RESOLUCIONES[indice_resolucion_config]
                nueva_camara = abrir_camara(indice_camara, nueva_resolucion)
                if nueva_camara is None:
                    mensaje_menu = f"No se pudo abrir {nombre_camara(indice_camara)}."
                else:
                    camara.release()
                    camara = nueva_camara
                    resolucion = nueva_resolucion
                    resolucion_real = obtener_resolucion_camara(nueva_camara, nueva_resolucion)
                    cv2.resizeWindow(NOMBRE_VENTANA, resolucion_real[0], resolucion_real[1])
                    guardar_configuracion(indice_camara, resolucion, umbral_pinza)
                    menu_abierto = False
                    mensaje_menu = "Configuración guardada."
            elif tecla_simple == ord("w") or tecla in (2490368,):
                opcion_menu = max(0, opcion_menu - 1)
            elif tecla_simple == ord("s") or tecla in (2621440,):
                opcion_menu = min(1, opcion_menu + 1)
            elif tecla_simple == ord("a") or tecla in (2424832,):
                if opcion_menu == 0:
                    indice_camara = max(0, indice_camara - 1)
                else:
                    indice_resolucion_config = max(0, indice_resolucion_config - 1)
            elif tecla_simple == ord("d") or tecla in (2555904,):
                if opcion_menu == 0:
                    indice_camara = min(CAMARAS_EN_MENU - 1, indice_camara + 1)
                else:
                    indice_resolucion_config = min(len(RESOLUCIONES) - 1, indice_resolucion_config + 1)
    finally:
        if boton_presionado and pyautogui is not None:
            try:
                pyautogui.mouseUp(button="left")
            except Exception as error:
                print(f"Error al liberar el botón del mouse: {error}")
        try:
            manos.close()
        finally:
            try:
                camara.release()
            finally:
                cv2.destroyAllWindows()


if __name__ == "__main__":
    mostrar_camara()
