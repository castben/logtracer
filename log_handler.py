# log_handler.py
import hashlib
import time
from collections import deque
from datetime import datetime
from queue import Queue

import TermTk as ttk

log_queue = Queue()

# --- Sistema de Throttling para evitar Spam ---
# Almacena hashes de mensajes recientes y sus últimos tiempos de registro
_recent_log_entries = deque(maxlen=200) # Mantener registro de los últimos N mensajes únicos
_log_suppression_counts = {} # {hash: (last_timestamp, suppression_count)}

def _should_suppress_message(message: str, level: str) -> tuple[bool, str | None]:
    """
    Determina si un mensaje debe suprimirse basado en su similitud reciente.

    Retorna:
        Tuple[bool, str | None]: (suppress_flag, suppression_message)
        - suppress_flag: True si se debe suprimir, False en caso contrario.
        - suppression_message: Mensaje de aviso sobre supresiones, o None.
    """
    # Crear una clave única para el mensaje (nivel + contenido, ignorando timestamp dinámico)
    # Esto hace que mensajes idénticos sean considerados repetidos.
    message_key = f"[{level}] {message}"
    message_hash = hashlib.md5(message_key.encode('utf-8')).hexdigest()
    current_time = time.time()

    # Limpiar entradas antiguas del diccionario de supresión (mayores a 2 segundos)
    # Esto evita fugas de memoria y asegura que solo se consideren mensajes recientes.
    global _log_suppression_counts
    _log_suppression_counts = {
        h: (t, c) for h, (t, c) in _log_suppression_counts.items()
        if current_time - t < 2.0 # Ventana de supresión de 2 segundos
    }

    # Verificar si el mensaje ya ha sido visto recientemente
    if message_hash in _log_suppression_counts:
        last_time, count = _log_suppression_counts[message_hash]
        # Si está dentro de la ventana de supresión (2s)
        if current_time - last_time < 2.0:
            # Incrementar el contador de supresiones
            _log_suppression_counts[message_hash] = (current_time, count + 1)
            # Suprimir si ya se ha mostrado al menos una vez recientemente
            # (count > 0 significa que ya se mostró el primero)
            if count > 0:
                return True, None # Suprimir silenciosamente después del primero
        else:
            # Si pasó más de 2 segundos, resetear el conteo
            _log_suppression_counts[message_hash] = (current_time, 1)
            return False, None # Mostrar el mensaje, resetea conteo
    else:
        # Primer mensaje de este tipo
        _log_suppression_counts[message_hash] = (current_time, 1)
        # Registrar el hash en la lista de recientes para mantenerlo fresco
        _recent_log_entries.append(message_hash)
        return False, None # Mostrar el primer mensaje

    return False, None # Por defecto, no suprimir


def write_log(message, level="INFO"):
    """
    Función dedicada para enviar mensajes a la TUI, con throttling para evitar spam.
    """

    # 1. Verificar si el mensaje debe suprimirse
    suppress, suppression_msg = _should_suppress_message(message, level)
    if suppress:
        # Si se debe suprimir, simplemente retorna sin hacer nada
        return

    # Si no se suprime, formatear y encolar el mensaje normalmente
    timestamped = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {level} {message}"
    msg = HighlightCode.highlight(ttk.TTkString(timestamped))
    log_queue.put(msg)

    # 2. Pequeña pausa para ceder control (yield) al hilo principal
    # Esto es crucial para evitar acaparamiento de CPU.
    # time.sleep(0) cede inmediatamente el control sin esperar tiempo fijo.
    time.sleep(0.05) # Yield al hilo principal


class HighlightCode:
    color_library = []

    def __init__(self, description, regex, color):
        self.description = description
        self.regex = regex
        self.color = color
        HighlightCode.color_library.append(self)

    @staticmethod
    def highlight(txt):
        ret = txt
        for each_definition in HighlightCode.color_library:
            # Manejar posibles errores en regex para evitar que rompan el logging
            try:
                if m := txt.findall(regexp=each_definition.regex):
                    for match in m:
                        ret = ret.setColor(ttk.TTkColor.fg(each_definition.color), match=match)
            except Exception:
                # Silenciar errores de regex
                pass
        return ret






# # log_handler.py
# from queue import Queue
# from datetime import datetime
# import TermTk as ttk
#
# log_queue = Queue()
#
# def write_log(*args, level="INFO", **kwargs):
#     """
#     Función dedicada para enviar mensajes a la TUI
#     """
#     message = " ".join(str(arg) for arg in args)
#     timestamped = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {level} {message}"
#
#     # Enviar a la cola para procesar en el hilo principal
#     msg = HighlightCode.highlight(ttk.TTkString(timestamped))
#     log_queue.put(msg)
#
#     # Opcional: imprimir en consola si se está en modo TUI
#     # __builtins__.print(timestamped, **kwargs)
#
#
# class HighlightCode:
#
#     color_library = []
#
#     def __init__(self, description, regex, color):
#         """
#
#         :param regex:
#         :param color:
#         """
#         self.description = description
#         self.regex = regex
#         self.color = color
#
#         HighlightCode.color_library.append(self)
#
#     @staticmethod
#     def highlight(txt):
#         """
#
#         :return:
#         """
#
#         ret = txt
#         for each_definition in HighlightCode.color_library:
#             if m := txt.findall(regexp=each_definition.regex):
#                 for match in m:
#                     ret = ret.setColor(ttk.TTkColor.fg(each_definition.color), match=match)
#
#         return ret