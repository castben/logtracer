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
        """Encuentra los límites de chunks basados en líneas completas"""
        try:
            with open(self.filepath, 'rb') as f:
                position = 0
                lines_counted = 0

                while True:
                    chunk = f.read(8192)  # Leer en bloques de 8KB
                    if not chunk:
                        break

                    # Contar saltos de línea
                    lines_in_chunk = chunk.count(b'\n')
                    lines_counted += lines_in_chunk

                    # Cada N líneas, guardar posición (al final de la última línea completa)
                    if lines_counted >= self.lines_per_chunk:
                        # Retroceder al último \n
                        last_nl = chunk.rfind(b'\n')
                        if last_nl != -1:
                            position += last_nl + 1
                            self.chunk_boundaries.append(position)
                            lines_counted = 0
                        else:
                            position += len(chunk)
                    else:
                        position += len(chunk)

                # Contar líneas totales
                self.total_lines = sum(1 for _ in open(self.filepath, 'r'))

        except Exception as e:
            write_log(f"Error reading file: {e}", level="ERROR")
            self.total_lines = 0

    def get_chunk(self, chunk_index):
        """Obtiene un chunk específico del archivo"""
        if chunk_index >= len(self.chunk_boundaries):
            return [], 0

        if chunk_index in self.chunk_cache:
            return self.chunk_cache[chunk_index]

        start_pos = self.chunk_boundaries[chunk_index] if chunk_index > 0 else 0
        end_pos = self.chunk_boundaries[chunk_index + 1] if chunk_index + 1 < len(self.chunk_boundaries) else None

        lines = []
        line_start = 0

        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(start_pos)
                line_start = start_pos

                while True:
                    line = f.readline()
                    if not line:
                        break
                    if end_pos and f.tell() >= end_pos:
                        break
                    lines.append(line.rstrip('\n'))

                    if len(lines) >= self.lines_per_chunk:
                        # Asegurarse de no cortar a mitad de chunk
                        next_char = f.read(1)
                        if next_char == '\n':
                            break
                        elif next_char:
                            # 🔧 CORRECCIÓN: Usar seek absoluto en lugar de relativo
                            current_pos = f.tell()
                            f.seek(current_pos - 1)
                            break

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