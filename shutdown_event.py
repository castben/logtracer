# shutdown_event.py
import threading
import os
import sys

shutdown_event = threading.Event()

def request_shutdown():
    """Solicita cierre ordenado del programa"""
    if shutdown_event.is_set():
        os._exit(1)

    #write_log("Request to close received, finish pending tasks...", level="INFO")
    shutdown_event.set()

    # Programar cierre forzado en 15 segundos
    threading.Timer(15.0, lambda: os._exit(1)).start()
