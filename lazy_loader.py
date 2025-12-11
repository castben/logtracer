# lazy_loader.py
import os
import threading
from queue import Queue
from log_handler import write_log
from support_icons import Icons


class LazyTextLoader:
    def __init__(self, filepath, lines_per_chunk=500):
        self.filepath = filepath
        self.lines_per_chunk = lines_per_chunk
        self.chunk_boundaries = []  # Posiciones de inicio de cada chunk
        self.total_lines = 0
        self.current_chunk_index = 0
        self.chunk_cache = {}
        self.max_cache_size = 3  # Mantener 3 chunks en caché

        # Calcular límites de chunks
        self._find_chunk_boundaries()

        # Cola para carga asincrónica
        self.load_queue = Queue()
        self._start_loader_thread()

    def _find_chunk_boundaries(self):
        """Encuentra los límites de chunks basados en líneas completas (CONTEO PRECISO)"""
        try:
            with open(self.filepath, 'rb') as f:
                chunk_size = 65536 if os.path.getsize(self.filepath) > 100_000_000 else 8192
                position = 0
                lines_counted = 0
                self.chunk_boundaries = []  # Reiniciar

                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    # Contar líneas individualmente (no solo contar \n)
                    chunk_pos = 0
                    chunk_len = len(chunk)

                    while chunk_pos < chunk_len:
                        # Buscar el próximo \n
                        nl_pos = chunk.find(b'\n', chunk_pos)

                        if nl_pos == -1:
                            # No hay más \n en este chunk
                            lines_counted += 1  # Última línea sin \n
                            break

                        # Contar esta línea
                        lines_counted += 1
                        chunk_pos = nl_pos + 1

                        # Si hemos alcanzado el límite de líneas
                        if lines_counted >= self.lines_per_chunk:
                            # Calcular posición absoluta del final de esta línea
                            boundary = position + nl_pos + 1
                            self.chunk_boundaries.append(boundary)
                            lines_counted = 0

                    # Actualizar posición absoluta
                    position += chunk_len

                # Asegurar que haya al menos un chunk
                file_size = os.path.getsize(self.filepath)
                if not self.chunk_boundaries:
                    self.chunk_boundaries = [file_size]
                elif self.chunk_boundaries[-1] < file_size:
                    self.chunk_boundaries.append(file_size)

                # Contar líneas totales
                self.total_lines = sum(1 for _ in open(self.filepath, 'r'))

                # Depuración
                for i, boundary in enumerate(self.chunk_boundaries):
                    start = self.chunk_boundaries[i-1] if i > 0 else 0
                    # Calcular exceso de líneas
                    lines_in_chunk = self._count_lines_in_range(start, boundary)
                    excess = lines_in_chunk - self.lines_per_chunk if i > 0 else lines_in_chunk
                    write_log(f"DEBUG Chunk {i}: desde {start} hasta {boundary} exceso de lineas {max(0, excess)}")

        except Exception as e:
            write_log(f"{Icons.ERROR} Error analizando archivo {self.filepath}: {str(e)}", level="ERROR")
            self.total_lines = 0
            self.chunk_boundaries = [0]

    def _count_lines_in_range(self, start, end):
        """Cuenta líneas en un rango específico del archivo"""
        count = 0
        with open(self.filepath, 'rb') as f:
            f.seek(start)
            while f.tell() < end:
                if f.readline():
                    count += 1
        return count

    def get_chunk(self, chunk_index):
        """Obtiene un chunk específico del archivo"""
        if chunk_index >= len(self.chunk_boundaries):
            return [], 0

        if chunk_index in self.chunk_cache:
            return self.chunk_cache[chunk_index]

        # Calcular posiciones CORRECTAMENTE
        start_pos = self.chunk_boundaries[chunk_index - 1] if chunk_index > 0 else 0
        end_pos = self.chunk_boundaries[chunk_index] if chunk_index < len(self.chunk_boundaries) else None

        lines = []
        line_start = 0

        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(start_pos)
                line_start = start_pos

                # Leer exactamente self.lines_per_chunk líneas
                lines_read = 0
                while lines_read < self.lines_per_chunk:
                    line = f.readline()
                    if not line:
                        break

                    # Si tenemos end_pos, verificar si excedemos
                    if end_pos and f.tell() > end_pos:
                        break

                    lines.append(line.rstrip('\n'))
                    lines_read += 1

            # Actualizar caché
            if len(self.chunk_cache) >= self.max_cache_size:
                oldest = next(iter(self.chunk_cache))
                del self.chunk_cache[oldest]

            self.chunk_cache[chunk_index] = (lines, line_start)
            return lines, line_start

        except Exception as e:
            write_log(f"{Icons.ERROR} Error leyendo chunk {chunk_index}: {str(e)}", level="ERROR")
            return [], 0

    def _start_loader_thread(self):
        """Inicia hilo para carga asincrónica de chunks"""
        def loader():
            while True:
                try:
                    chunk_index = self.load_queue.get(timeout=1)
                    if chunk_index is None:  # Señal de cierre
                        break
                    self.get_chunk(chunk_index)  # Cargar y cachear
                except:
                    continue

        thread = threading.Thread(target=loader, daemon=True)
        thread.start()

    def preload_chunks(self, current_chunk, direction='both'):
        """Pre-carga chunks adyacentes"""
        if direction in ['next', 'both']:
            next_chunk = current_chunk + 1
            if next_chunk < len(self.chunk_boundaries):
                self.load_queue.put(next_chunk)

        if direction in ['prev', 'both']:
            prev_chunk = current_chunk - 1
            if prev_chunk >= 0:
                self.load_queue.put(prev_chunk)

class LazyListManager:
    """Gestor de listas perezosas para Flows/Transactions"""

    def __init__(self, list_widget, chunk_size=100):
        self.list_widget = list_widget
        self.chunk_size = chunk_size
        self.all_items = []  # Todos los elementos
        self.filtered_items = []  # Elementos filtrados
        self.displayed_count = 0
        self.current_filter = None

        # Conectar scroll
        self.list_widget._verticalScrollBar.valueChanged.connect(self._on_scroll)

    def set_items(self, items):
        """Establece todos los items"""
        self.all_items = list(items) if not isinstance(items, list) else items
        self.filtered_items = self.all_items.copy()
        self.current_filter = None
        self._refresh_display()

    def filter_items(self, query):
        """Filtra items por query"""
        if not query:
            self.filtered_items = self.all_items.copy()
            self.current_filter = None
        else:
            # Búsqueda eficiente (puedes mejorar esto con un índice)
            query_lower = query.lower()
            self.filtered_items = [
                item for item in self.all_items
                if query_lower in str(item).lower()
            ]
            self.current_filter = query

        self._refresh_display()

    def _refresh_display(self):
        """Refresca la vista mostrando solo los primeros elementos"""
        # self.list_widget.removeItems()
        for each_item in self.list_widget.items().copy():
            self.list_widget.removeItem(each_item)
        self.displayed_count = 0
        self._load_next_chunk()

    def _load_next_chunk(self):
        """Carga el siguiente chunk de elementos"""
        start = self.displayed_count
        end = min(start + self.chunk_size, len(self.filtered_items))

        for i in range(start, end):
            item = self.filtered_items[i]
            # Convertir a formato adecuado para TTkList
            if isinstance(item, str):
                list_item = item
            else:
                # Asumiendo que tienes un método para convertir objetos a string
                list_item = str(item)

            self.list_widget.addItem(list_item)

        self.displayed_count = end

        # Actualizar estado de carga
        total = len(self.filtered_items)
        write_log(f"Showing {min(end, total)} out of {total} items")
        # if hasattr(self.list_widget.parent(), 'status_label'):
        #
        #     self.list_widget.parent().status_label.setText(
        #         f"Mostrando {min(end, total)} de {total} elementos"
        #     )

    def _on_scroll(self, value):
        """Maneja scroll para cargar más elementos"""
        scroll_bar = self.list_widget._verticalScrollBar
        if value >= scroll_bar.maximum() * 0.8:  # 80% del final
            if self.displayed_count < len(self.filtered_items):
                self._load_next_chunk()