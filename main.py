"""Visualización de la cámara web en tiempo real usando OpenCV."""

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
    (640, 480),    # 1. VGA
    (1280, 720),   # 2. HD
    (1920, 1080),  # 3. Full HD
)
CAMARA_PREDETERMINADA = 0
RESOLUCION_PREDETERMINADA = RESOLUCIONES[2]
CAMARAS_EN_MENU = 5  # Índices 0, 1, 2, 3 y 4.
UMBRAL_PINZA_PREDETERMINADO = 30
UMBRAL_LIBERACION_PINZA = 40
FRAMES_ESTABLES_PINZA = 3
SUAVIZADO_CURSOR = 0.35
MARGEN_CURSOR = 0.08
TIEMPO_CLIC_SOSTENIDO = 0.45



def configuracion_predeterminada():
    """Devuelve una copia de la configuración inicial."""
    return {
        "indice_camara": CAMARA_PREDETERMINADA,
        "resolucion": list(RESOLUCION_PREDETERMINADA),
        "umbral_pinza": UMBRAL_PINZA_PREDETERMINADO,
    }



def cargar_configuracion():
    """Carga config.json y usa valores seguros si está ausente o es inválido."""
    configuracion = configuracion_predeterminada()

    try:
        with ARCHIVO_CONFIGURACION.open("r", encoding="utf-8") as archivo:
            guardada = json.load(archivo)

        indice = guardada.get("indice_camara", CAMARA_PREDETERMINADA)
        resolucion = tuple(guardada.get("resolucion", RESOLUCION_PREDETERMINADA))
        umbral_pinza = guardada.get("umbral_pinza", UMBRAL_PINZA_PREDETERMINADO)

        if isinstance(indice, int) and indice >= 0:
            configuracion["indice_camara"] = indice
        if resolucion in RESOLUCIONES:
            configuracion["resolucion"] = list(resolucion)
        if isinstance(umbral_pinza, (int, float)) and 10 <= umbral_pinza <= 100:
            configuracion["umbral_pinza"] = float(umbral_pinza)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        # Se conservan los valores predeterminados y se repara el archivo al guardar.
        pass

    return configuracion



def guardar_configuracion(indice_camara, resolucion, umbral_pinza=None):
    """Guarda la cámara y resolución elegidas para el siguiente inicio."""
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
    """Devuelve el nombre visible de la cámara seleccionada.

    OpenCV identifica las cámaras por índice, pero no expone el nombre comercial
    del dispositivo. Por eso se muestra un nombre estable basado en ese índice.
    """
    return f"Cámara {indice_camara}"



def abrir_camara(indice_camara, resolucion):
    """Abre una cámara y solicita la resolución indicada."""
    camara = cv2.VideoCapture(indice_camara)
    if not camara.isOpened():
        camara.release()
        return None

    ancho, alto = resolucion
    camara.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
    camara.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
    return camara


 
def es_tecla_f1(tecla):
    """Reconoce F1 en los códigos usados por OpenCV en distintos sistemas."""
    # En Windows waitKeyEx suele devolver VK_F1 desplazado 16 bits (0x700000).
    # En otros backends puede llegar como 65470 o con otros desplazamientos.
    return tecla in (0x70, 0x70000, 0x700000, 65470) or ((tecla >> 16) & 0xFF) == 0x70


def es_tecla_f2(tecla):
    """Reconoce F2 en los códigos usados por OpenCV en Windows."""
    return tecla in (0x71, 0x70001, 0x710000, 65471) or ((tecla >> 16) & 0xFF) == 0x71


def dibujar_menu(imagen, indice_camara, indice_resolucion, opcion, mensaje=""):
    """Dibuja el menú de configuración sobre el último fotograma."""
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
    """Obtiene el índice de una resolución, usando la predeterminada si no coincide."""
    try:
        return RESOLUCIONES.index(tuple(resolucion))
    except ValueError:
        return RESOLUCIONES.index(RESOLUCION_PREDETERMINADA)


def asegurar_modelo_manos():
    """Descarga el modelo oficial de MediaPipe Tasks si aún no existe."""
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
    """Dibuja los 21 landmarks normalizados de MediaPipe Tasks sobre la imagen."""
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
    """Calcula en píxeles la distancia entre los landmarks 4 y 8."""
    pulgar = landmarks[4]
    indice = landmarks[8]
    pulgar_xy = (pulgar.x * ancho, pulgar.y * alto)
    indice_xy = (indice.x * ancho, indice.y * alto)
    return math.hypot(
        indice_xy[0] - pulgar_xy[0],
        indice_xy[1] - pulgar_xy[1],
    ), pulgar_xy, indice_xy


def actualizar_estado_pinza(distancia, pinza_activa, frames_candidatos, umbral):
    """Aplica histéresis y exige varios frames para evitar falsos cambios."""
    if pinza_activa:
        if distancia > UMBRAL_LIBERACION_PINZA:
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


def mostrar_camara():
    """Muestra la cámara y permite cambiar configuración con F1."""
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
        num_hands=1,
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

    # Crea config.json incluso en el primer inicio, con cámara 0 como base.
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
    cursor_x = None
    cursor_y = None
    pantalla_ancho, pantalla_alto = pyautogui.size()
    pyautogui.PAUSE = 0
    boton_presionado = False
    inicio_pinza = None
    pinza_anterior = False

    try:
        cv2.namedWindow(NOMBRE_VENTANA, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(NOMBRE_VENTANA, resolucion[0], resolucion[1])

        while True:
            lectura_exitosa, imagen = camara.read()
            if not lectura_exitosa:
                print("Error: no se pudo leer una imagen de la cámara.")
                break

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
            pinza_anterior = pinza_activa

            if mano_detectada:
                for puntos_mano in resultado_manos.hand_landmarks:
                    dibujar_landmarks_mano(imagen, puntos_mano)
                    punta_indice = puntos_mano[8]
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
                            cursor_x += (objetivo_x - cursor_x) * SUAVIZADO_CURSOR
                            cursor_y += (objetivo_y - cursor_y) * SUAVIZADO_CURSOR
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
                    cv2.line(
                        imagen,
                        tuple(map(int, pulgar_xy)),
                        tuple(map(int, indice_xy)),
                        (0, 255, 255) if pinza_activa else (160, 160, 160),
                        3,
                        cv2.LINE_AA,
                    )

            if not mano_detectada:
                pinza_activa = False
                frames_candidatos_pinza = 0
                pinza_sostenida = boton_presionado
                if boton_presionado:
                    pyautogui.mouseUp(button="left")
                    boton_presionado = False
                if control_mouse_activo and pinza_anterior and not pinza_sostenida:
                    pyautogui.click()
                inicio_pinza = None

            estado_mano = "MANO DETECTADA" if mano_detectada else "SIN MANO"
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
            estado_mouse = "MOUSE ACTIVO (F2)" if control_mouse_activo else "MOUSE PAUSADO (F2)"
            cv2.putText(
                imagen,
                estado_mouse,
                (15, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (0, 220, 255) if control_mouse_activo else (180, 180, 180),
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

            if menu_abierto:
                dibujar_menu(imagen, indice_camara, indice_resolucion_config, opcion_menu, mensaje_menu)

            cv2.imshow(NOMBRE_VENTANA, imagen)
            tecla = cv2.waitKeyEx(1)

            if tecla & 0xFF == ord("q") and not menu_abierto:
                break

            if es_tecla_f1(tecla):
                menu_abierto = not menu_abierto
                mensaje_menu = ""
                if menu_abierto and boton_presionado:
                    pyautogui.mouseUp(button="left")
                    boton_presionado = False
                continue

            if es_tecla_f2(tecla) and not menu_abierto:
                control_mouse_activo = not control_mouse_activo
                cursor_x = None
                cursor_y = None
                pinza_activa = False
                frames_candidatos_pinza = 0
                inicio_pinza = None
                if not control_mouse_activo and boton_presionado:
                    pyautogui.mouseUp(button="left")
                    boton_presionado = False
                continue

            if not menu_abierto:
                continue

            tecla_simple = tecla & 0xFF
            if tecla_simple == 27:  # Esc
                menu_abierto = False
                mensaje_menu = "Cambios cancelados."
            elif tecla_simple in (13, 10):  # Enter
                nueva_resolucion = RESOLUCIONES[indice_resolucion_config]
                nueva_camara = abrir_camara(indice_camara, nueva_resolucion)
                if nueva_camara is None:
                    mensaje_menu = f"No se pudo abrir {nombre_camara(indice_camara)}."
                else:
                    camara.release()
                    camara = nueva_camara
                    resolucion = nueva_resolucion
                    cv2.resizeWindow(NOMBRE_VENTANA, resolucion[0], resolucion[1])
                    guardar_configuracion(indice_camara, resolucion, umbral_pinza)
                    menu_abierto = False
                    mensaje_menu = "Configuración guardada."
            elif tecla_simple == ord("w") or tecla in (2490368,):  # Arriba
                opcion_menu = max(0, opcion_menu - 1)
            elif tecla_simple == ord("s") or tecla in (2621440,):  # Abajo
                opcion_menu = min(1, opcion_menu + 1)
            elif tecla_simple == ord("a") or tecla in (2424832,):  # Izquierda
                if opcion_menu == 0:
                    indice_camara = max(0, indice_camara - 1)
                else:
                    indice_resolucion_config = max(0, indice_resolucion_config - 1)
            elif tecla_simple == ord("d") or tecla in (2555904,):  # Derecha
                if opcion_menu == 0:
                    indice_camara = min(CAMARAS_EN_MENU - 1, indice_camara + 1)
                else:
                    indice_resolucion_config = min(len(RESOLUCIONES) - 1, indice_resolucion_config + 1)
    finally:
        if boton_presionado and pyautogui is not None:
            pyautogui.mouseUp(button="left")
        manos.close()
        camara.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    mostrar_camara()
