# Teclado x Mouse Virtual

Este programa usa la cámara para controlar el mouse con la mano y escribir con un teclado que aparece en la pantalla.

## Qué necesitas

- Windows y Python instalado.
- Una cámara web.

## Cómo instalarlo

1. Descarga este proyecto desde GitHub y abre la carpeta.
2. Abre una terminal dentro de esa carpeta.
3. Instala lo necesario:

   ```powershell
   py -m pip install -r requirements.txt
   ```

4. Inicia el programa:

   ```powershell
   py main.py
   ```

La primera vez puede descargar el modelo de manos. Para esa descarga necesitas conexión a Internet.

## Cómo se usa

- **F1**: abre o cierra el menú para elegir cámara y resolución.
- **Flechas** o **W A S D**: cambian las opciones del menú.
- **Enter**: guarda la selección.
- **Esc**: cancela los cambios.
- **F2**: cambia entre el teclado y el mouse. Si ambos están apagados, activa el teclado.
- **Q**: cierra el programa.

Junta los dos pulgares durante 2 segundos para activar el mouse o cambiar entre los modos. Junta los dos índices para apagar ambos modos.

### Mouse

En modo mouse, mueve el índice de la mano derecha para mover el cursor. Junta el pulgar con el índice para hacer clic izquierdo y con el dedo medio para hacer clic derecho. Mantén la pinza del pulgar y el índice para dejar presionado el botón.

### Teclado en pantalla

En modo teclado, apunta a una tecla con el índice y junta el pulgar con ese índice para pulsarla. Los botones **COPIAR** y **PEGAR** también están en el teclado.

Fuera del modo teclado, la mano izquierda permite copiar con pulgar e índice y pegar con pulgar y medio. Cerrar la mano izquierda en puño toma una captura de pantalla.

## Si algo no funciona

- Si no aparece la cámara, prueba otro índice desde el menú **F1** y cierra otras aplicaciones que estén usando la cámara.
- Si Windows bloquea el acceso, permite que Python use la cámara en la configuración de privacidad.
- Si falta una dependencia, repite el paso de instalación.
- Para cerrar el programa, vuelve a la ventana de la cámara y presiona **Q**.
