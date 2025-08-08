# shutdown_event.py
import threading
import os
import sys
from log_handler import write_log  # Asegúrate de importar tu write_log

shutdown_event = threading.Event()

def request_shutdown():
    """Solicita cierre ordenado del programa"""
    if shutdown_event.is_set():
        write_log("Forcing to close...", level="WARN")
        os._exit(1)

    write_log("Request to close received, finish pending tasks...", level="INFO")
    shutdown_event.set()

    # Programar cierre forzado en 15 segundos
    threading.Timer(15.0, lambda: os._exit(1)).start()