# log_handler.py
from queue import Queue
from datetime import datetime
import TermTk as ttk

log_queue = Queue()

def write_log(*args, level="INFO", **kwargs):
    """
    Función dedicada para enviar mensajes a la TUI
    """
    message = " ".join(str(arg) for arg in args)
    timestamped = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {level} {message}"

    # Enviar a la cola para procesar en el hilo principal
    msg = HighlightCode.highlight(ttk.TTkString(timestamped))
    log_queue.put(msg)

    # Opcional: imprimir en consola si se está en modo TUI
    # __builtins__.print(timestamped, **kwargs)


class HighlightCode:

    color_library = []

    def __init__(self, description, regex, color):
        """

        :param regex:
        :param color:
        """
        self.description = description
        self.regex = regex
        self.color = color

        HighlightCode.color_library.append(self)

    @staticmethod
    def highlight(txt):
        """

        :return:
        """

        ret = txt
        for each_definition in HighlightCode.color_library:
            if m := txt.findall(regexp=each_definition.regex):
                for match in m:
                    ret = ret.setColor(ttk.TTkColor.fg(each_definition.color), match=match)

        return ret