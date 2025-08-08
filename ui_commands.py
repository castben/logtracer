# ui_commands.py
import threading
from queue import Queue

from log_handler import write_log
from shutdown_event import shutdown_event
from support_icons import Icons

# Cola para comandos de UI
ui_command_queue = Queue()

def schedule_ui_update(component_name, method, *args, **kwargs):
    """
    Programa una actualización de UI por nombre de componente

    :param component_name: Nombre del widget (ej: 'TTkLabel_status')
    :param method: Método a llamar (ej: 'setText')
    :param args: Argumentos posicionales para el método
    :param kwargs: Argumentos por nombre para el método
    """
    ui_command_queue.put({
        "component": component_name,
        "method": method,
        "args": args,
        "kwargs": kwargs
    })

def process_ui_commands(root_tui):
    """
    Procesa comandos de UI en el hilo principal

    :param root_tui: Referencia a la ventana principal para buscar widgets
    """
    while not ui_command_queue.empty():

        # Si se está cerrando, procesar solo mensajes pendientes
        if shutdown_event.is_set() and ui_command_queue.empty():
            return  # No programar más actualizaciones

        command = ui_command_queue.get_nowait()

        try:
            # Obtener widget por nombre
            widget = root_tui.getWidgetByName(command["component"])
            if not widget:
                write_log(
                    f"{Icons.WARNING} UI: Componente '{command['component']}' no encontrado",
                    level="WARN"
                )
                continue

            # Ejecutar método
            getattr(widget, command["method"])(*command["args"], **command["kwargs"])

        except Exception as e:
            write_log(
                f"{Icons.ERROR} UI: Error actualizando {command['component']}.{command['method']}: {str(e)}",
                level="ERROR"
            )

    # Programar próxima verificación
    if not shutdown_event.is_set():
        threading.Timer(0.05, lambda: process_ui_commands(root_tui)).start()