#!./system/bin/python
import cProfile
import glob
# Program to test extraction and validation of X500 names.
import os
import argparse
import re
import signal
import sys
import threading
from datetime import datetime
from TermTk import TTkUtil, TTkUiLoader, TTk
import TermTk as ttk
from get_refIds import GetRefIds
from object_class import Configs, FileManagement, BlockExtractor
from object_class import CordaObject
from get_parties import GetParties
from support_icons import Icons
from ui_commands import schedule_ui_update, process_ui_commands
from uml import UMLEntityEndPoints, UMLStepSetup, CreateUML
from log_handler import write_log, HighlightCode
from log_handler import log_queue
from TermTk.TTkCore.signal import pyTTkSlot
from shutdown_event import shutdown_event


def signal_handler(sig, frame):
    """Maneja Ctrl+C y otras señales de terminación"""
    if shutdown_event.is_set():
        # Segundo Ctrl+C: cierre inmediato
        write_log("Forcing closure", level="WARN")
        sys.exit(1)

    write_log("Request to shutdown, finishing all current tasks...", level="INFO")
    shutdown_event.set()

    # Programar cierre forzado en 15 segundos si no termina
    threading.Timer(15.0, lambda: os._exit(1)).start()

# Registrar manejador de señales
signal.signal(signal.SIGINT, signal_handler)

def get_configs():
    return Configs


def remove_unicode_symbols(text):
    """
    Elimina emojis y símbolos Unicode (⚠️, ✅, etc.) pero mantiene texto normal
    """
    # Patrón para eliminar emojis y símbolos comunes
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticonos
        "\U0001F300-\U0001F5FF"  # símbolos y pictogramas
        "\U0001F680-\U0001F6FF"  # transporte y mapas
        "\U0001F700-\U0001F77F"  # símbolos alquímicos
        "\U0001F780-\U0001F7FF"  # formas geométricas extendidas
        "\U0001F800-\U0001F8FF"  # flechas extendidas
        "\U0001F900-\U0001F9FF"  # componentes de símbolos
        "\U0001FA00-\U0001FA6F"  # decoraciones de bandera
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+"
    )
    return emoji_pattern.sub(r'', text).strip()


class InteractiveWindow:
    """
    A class that create an interactive experience
    """
    class LogfileViewer:
        """
        A class to generate different logviewer windows
        """

        def __init__(self, starting_line=None):
            """

            """

            self.TTkWindow_logviewer = ttk.TTkWindow(pos=(40, 1), size=(120, 32),
                                                     title=ttk.TTkString("Log Viewer", ttk.TTkColor.ITALIC),
                                                     border=True,
                                                     layout=ttk.TTkGridLayout(),
                                                     flags=ttk.TTkK.WindowFlag.WindowMinMaxButtonsHint)

            self.root_logviewer = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
                "eJyFU0tP3DAQznbDhmXbohbKqyBFPXGij2sfBygtIixFZVtOFTKJYSwSe5XYLFsJqcdFmqP7W/r3OnZCteqFWJbnne8bj3+Fv/+0A//d2E0M9XjILT4eDC6/iZcfVWoK" +
                "LrXF6IqXlVDS4sybrddbryy2tRHWpcykOasqiw8pZ0dJzYTkpcXOkJWsqHxIeMgKqjrXJ9+JkJkaWZw9UpXQruQPu5mEyQOO4bH4yb06TDY4dvtCxici02CTgJJJ2+Pi" +
                "ArRTu3123Tj3g6Dl/GRo/LUl+i4qcZZzO8FoVzKSMicOlMoHYmgxIFpHLMuEvPA/DerFsXPAxsoQ6y5RamSDnbyWiBBEsA7dGyLxmauC63LcpBNubSucTUHkWckdNx+O" +
                "s1TpU+m64PI2oYdLd5bTXF2ci5xfCT6ixsEjh6VFOGDeSUWyzuFJEsBT2gueGSzWx7MJLE1gGVZgtc7xi8NzWMfOtiozKjfBmYHQ1ARYMbAxhR3iGvJlskaQ4cUd0h7h" +
                "GvBrvZsJ/Q/s6pTxHrwiWbsXL/YOaEjiQ1OceYiLU2p8rFmp3Z0kLex+5SyLv8h8TFFzfZNrEbtYOzHYLmmMaBLaqcrdGZFeDZl0eRHZGtkwgxENsdlmJVHEzpnSWhX1" +
                "XOb8XPs7uiO67CMNRcjT/PzqdERdHJVsaD3s0PWAxuKkscYk7wBPL1kzZl6hMbs1FcNOSk+H+E3XX/ivPr92XXZXuIfhrlf2byFx+aaCt9TCd7TfJy344KkY7KVKSp66" +
                "l1NRabP1F5LoUGM="))

            self.TTkMenuBarButton: ttk.TTkMenuBarButton = self.root_logviewer.getWidgetByName('menuButton_lfv_exit')
            self.TTkFrame_logfileviewer: ttk.TTkFrame = self.root_logviewer.getWidgetByName('TTkFrame_logfileviewer')
            self.TTkTextEdit_logfileviewer: ttk.TTkTextEdit = self.root_logviewer.getWidgetByName('TTkTextEdit_logfileviewer')
            self.TTkWindow_logviewer.addWidget(self.TTkFrame_logfileviewer)
            self.TTkMenuBarButton_lfv_wordwrap: ttk.TTkMenuBarButton = self.root_logviewer.getWidgetByName('menuButton_lfv_wordwrap')
            self._logview_resize()

            if starting_line:
                self.starting_line = starting_line
                self.TTkTextEdit_logfileviewer.setLineNumber(starting_line)

            def _wordwrap():
                """

                :return:
                """
                if self.TTkMenuBarButton_lfv_wordwrap.isChecked():
                    self.TTkTextEdit_logfileviewer.setLineWrapMode(ttk.TTkK.WidgetWidth)
                    self.TTkMenuBarButton_lfv_wordwrap.clearFocus()
                else:
                    self.TTkTextEdit_logfileviewer.setLineWrapMode(ttk.TTkK.NoWrap)

            self.TTkWindow_logviewer.sizeChanged.connect(self._logview_resize)

            self.TTkMenuBarButton.menuButtonClicked.connect(lambda: self.TTkWindow_logviewer.setVisible(False))
            self.TTkMenuBarButton_lfv_wordwrap.menuButtonClicked.connect(_wordwrap)

        def loadfile(self, filename, starting_line=0, maxlines=0):
            """
            Load full logfile
            :param filename: file name to read
            :param starting_line: Starting line to read from
            :param maxlines: maximum lines to read.
            :return:
            """

            self.TTkTextEdit_logfileviewer.setText("")
            self.TTkWindow_logviewer.setTitle(f'Log Viewer - {filename}')
            if starting_line == 0:
                self.TTkTextEdit_logfileviewer.setLineNumberStarting(1)
            else:
                self.TTkTextEdit_logfileviewer.setLineNumberStarting(starting_line)
            buffer = []
            try:
                with open(filename, 'r') as hlogfile:
                    for line_number, each_line in enumerate(hlogfile, start=2):
                        ttkline = ttk.TTkString(each_line.rstrip())
                        if starting_line>0:
                            if maxlines > 0:
                                if starting_line <= line_number <= starting_line+maxlines:
                                    # self.TTkTextEdit_logfileviewer.append(each_line.rstrip())
                                    buffer.append(HighlightCode.highlight(ttkline))
                            else:
                                # self.TTkTextEdit_logfileviewer.append(each_line.rstrip())
                                buffer.append(HighlightCode.highlight(ttkline))
                        else:
                            # self.TTkTextEdit_logfileviewer.append(each_line.rstrip())
                            buffer.append(HighlightCode.highlight(ttkline))

                self.TTkTextEdit_logfileviewer.setText(ttk.TTkString("\n").join(buffer))

            except IOError as io:
                write_log(f'Unable to open {filename} due to {io}', level="ERROR")
            except BaseException as be:
                write_log(f'An error was found trying to read {filename} due to {be}', level='ERROR')

        def add_line(self, line):
            """
            Add a new line
            :param line:
            :return:
            """

            self.TTkTextEdit_logfileviewer.append(line)

        def _logview_resize(self):
            """
            Will resize logging text edit to adapt it to its container window...
            :return:
            """
            window_size = self.TTkWindow_logviewer.size()
            new_size = (window_size[0]+5, window_size[1]+4)
            self.TTkTextEdit_logfileviewer.resize(window_size[0]-5,window_size[1]-7)

    def __init__(self):
        """

        """
        self.root = None
        self.TTkWindow_logging = None
        self.TTkWindow_customer_info = None
        self.filename = None
        self.customer = None
        self.ticket = None
        self.generated_files = {}
        self.filesize = 0


        HighlightCode('timestamps', r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}', '#00AAAA')
        HighlightCode('timestamps', r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2},\d+Z','#00AAAA')
        HighlightCode('level', 'WARN', '#AAAA00')
        HighlightCode('level', 'WARNING', '#AAAA00')
        HighlightCode('level', r'\bINFO ', '#44AA00')
        HighlightCode('level', 'ERROR ', '#FF8800')

        #

    def check_generated_files(self):
        """
        This will check Actual folder where UML diagrams should exist, and will load references that exist
        :return:
        """
        app_path = os.path.dirname(os.path.abspath(__file__))
        app_path = f'{app_path}/plugins/plantuml_cmd/data/{self.customer}/{self.ticket}'
        pattern = re.compile(r'([A-Za-z0-9-]*)_page_[0-9]*.puml')
        for each_file in glob.glob(f"{app_path}/*.puml"):
            match = pattern.search(each_file)

            if match:
                ref_id = match.group(1)
                self.add_generated_file(ref_id, each_file)

    def add_generated_file(self,ref_id, script_files):
        """
        Add file that has been generated
        :return:
        """

        write_log(f'Generated diagram for {ref_id}... found')

        if isinstance(ref_id, ttk.TTkString):
            ref_id = ref_id.toAscii()

        if ref_id not in self.generated_files:
            self.generated_files[ref_id] = []

        if isinstance(script_files, list):
            # if given script_files is a list, process each entry to make sure it has proper extension...

            # Modify file extension to only "see utxt" files
            files = []
            for each_file in script_files:
                file_path, file_ext  = os.path.splitext(each_file)
                files.append(f"{file_path}.utxt")

            self.generated_files[ref_id] = files

        else:
            # if it is just a string then append it to current list...
            if script_files not in self.generated_files[ref_id]:
                self.generated_files[ref_id].append(script_files)

    def exist(self, ref_id):
        """
        Check if given reference was already traced

        :param ref_id:
        :return:
        """

        return ref_id in self.generated_files

    def tk_window(self):
        """

        :return:
        """
        global tui_logging

        def _filetxtchange(filepath):
            """

            :return:
            """
            global tui_logging
            # logfile_name.setWordWrapMode(1)
            # logfile_name.setWrapWidth(6)

            self.filename = filepath
            filepath = os.path.basename(filepath)
            self.filesize = os.path.getsize(self.filename)

            TTkLabel_file_size.setText(ttk.TTkString(_filesize_str(self.filesize)))
            TTkButton_start_analysis.setEnabled(True)
            TTkLabel_analysis_status.setText("")
            TTkLabel_Flows.setText("")
            TTkLabel_Parties.setText("")
            TTkLabel_Transactions.setText("")
            TTkButton_viewfile.setEnabled(True)

            self.TTkWindow_customer_info.setTitle(f'Logs tracer - {filepath}')
            write_log('Checking for existing diagrams...')
            self.check_generated_files()

        def _fill_tickets(customer):
            """
            Will fill tickets list if there're on given folder path
            :param app_path:
            :return:
            """
            self.customer = customer
            TTkButton_new_ticket.setEnabled(True)
            app_path =f"{os.path.dirname(os.path.abspath(__file__))}/plugins/plantuml_cmd/data/{customer}"

            ticket_list = _check_folders(app_path)

            if ticket_list:
                TTkComboBox_ticket.clear()
                TTkComboBox_ticket.addItems(ticket_list)

        def _check_folders(app_path=None):
            """

            :return:
            """
            if not app_path:
                app_path =f"{os.path.dirname(os.path.abspath(__file__))}/plugins/plantuml_cmd/data"

            subdirs = [
                item for item in os.listdir(app_path)
                if os.path.isdir(os.path.join(app_path, item))
            ]

            return subdirs

        def _enable_file_select(ticket):
            """

            :return:
            """
            if ticket:
                self.ticket = ticket
                TTkFileButtonPicker.setEnabled(True)

        def _filesize_str(size_in_bytes):
            """
            Return a human-readable file size string (e.g., 1.23 KB, 4.56 MB).
            :param size_in_bytes: Size in bytes (int or float)
            :return: Formatted string
            """
            for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
                if size_in_bytes < 1024.0:
                    return f"{size_in_bytes:.2f} {unit}"
                size_in_bytes /= 1024.0
            return f"{size_in_bytes:.2f} EB"

        def _clear_components():
            """
            Clear all components lists/trees
            :return:
            """
            # Clear all components
            for each_item in list_flow.items().copy():
                list_flow.removeItem(each_item)

            for each_item in list_transactions.items().copy():
                list_transactions.removeItem(each_item)

            self.clear_tree_party()

        def _start_analysis():
            """

            :return:
            """
            global file_to_analyse
            TTkButton_start_analysis.setEnabled(False)
            schedule_ui_update('TTkLabel_analysis_stat','setVisible',True)
            schedule_ui_update('TTkLabel_analysis_stat', "setText", "Working...")

            _clear_components()

            def _analysis_process(special_blocks:BlockExtractor):
                """
                Thread for analysis
                :return:
                """

                file_to_analyse.parallel_processing()
                # Prepare new execution
                # Clean up old processes:
                file_to_analyse.remove_process_to_execute(CordaObject.Type.PARTY)
                file_to_analyse.remove_process_to_execute(CordaObject.Type.FLOW_AND_TRANSACTIONS)

                # Stopping timewatch process and get time spent
                time_msg = file_to_analyse.start_stop_watch('Main-search', False)

                # Set roles if it is possible
                if file_to_analyse.result_has_element(CordaObject.Type.PARTY):
                    write_log('Setting up roles automatically...')
                    file_to_analyse.assign_roles()

                write_log(f"Elapsed time:{time_msg}")
                schedule_ui_update('TTkLabel_analysis_stat', "setText", '\u2705 Done...')

                ##
                ## Start filling components with data
                if not file_to_analyse.get_all_unique_results():
                    write_log('I was not able to process this file, it was not recognized as Corda log file', level='WARN')
                    return

                if not file_to_analyse.get_all_unique_results('Party'):
                    write_log('I was not able to process this file, it was not recognized as Corda log file', level='WARN')
                    return

                TTkLabel_Parties.setText(f"{len(file_to_analyse.get_all_unique_results('Party'))}")
                results = collect_refIds.classify_results(FileManagement.get_all_unique_results('Flows&Transactions'))
                if not results:
                    write_log('...')
                    return
                TTkLabel_Flows.setText(f"{len(results['FLOW'])}")
                TTkLabel_Transactions.setText(f"{len(results['TRANSACTION'])}")

                # Flow list
                for each_flow in results['FLOW']:
                    sp_blk = special_blocks.get_reference(each_flow)
                    if sp_blk:
                        icn=""
                        for each_blk in sp_blk:
                            icn += f" {Icons.get(Configs.get_config_for(f'BLOCK_COLLECTION.COLLECT.{each_blk}.ICON'))}"
                        each_flow = ttk.TTkString(f"{each_flow}{icn.lstrip()}")
                    list_flow.addItem(each_flow)

                # Transaction list
                for each_tx in results['TRANSACTION']:
                    sp_blk = special_blocks.get_reference(each_tx)
                    if sp_blk:
                        icn=""
                        for each_blk in sp_blk:
                            icn += f" {Icons.get(Configs.get_config_for(f'BLOCK_COLLECTION.COLLECT.{each_blk}.ICON'))}"
                        each_tx = ttk.TTkString(f"{each_tx}{icn.lstrip()}")
                    list_transactions.addItem(each_tx)

                # Party List
                party_headers = {
                    'Party X.500 name': 70,
                    'Role': 15
                }

                self.tree_party.setHeaderLabels(party_headers)
                # Set column width
                for pos,header in enumerate(party_headers.keys()):
                    self.tree_party.setColumnWidth(pos, party_headers[header])

                for each_party in FileManagement.get_all_unique_results('Party'):
                    if each_party.get_corda_role():
                        role = each_party.get_corda_role()
                    else:
                        role = 'party'
                    tree_element = ttk.TTkTreeWidgetItem([each_party.name, role])
                    self.tree_party.addTopLevelItem(tree_element)
                    if each_party.has_alternate_names():
                        for each_alternate in each_party.get_alternate_names():
                            child = ttk.TTkTreeWidgetItem([each_alternate, role])
                            tree_element.addChild(child)

            # print("Starting analysis...")

            Configs.load_config()

            # Define default entity object endpoints...
            UMLEntityEndPoints.load_default_endpoints()

            # in this case I'm removing initial branch 'UML_SETUP' because final config is a collection of configuration settings
            # that removes this.
            file_to_analyse = FileManagement(self.filename, block_size_in_mb=15, debug=True)
            # Analyse first 50 (by default) lines from given file_to_analyse to determine which Corda log format is
            # This is done to be able to separate key components from lines like Time stamp, severity level, and log
            # message
            file_to_analyse.discover_file_format()
            #
            # Analyse file for specific block lines that lack of key fields (like stack traces, and flow transitions):

            special_blocks = BlockExtractor(file_to_analyse, Configs.config)
            special_blocks.extract()
            special_blocks.summary()
            #
            #
            # Setup party collection
            #
            # Set actual configuration to use, and create object that will manage "Parties"
            collect_parties = GetParties(Configs)
            # Set file_to_analyse that will be used to extract information from
            collect_parties.set_file(file_to_analyse)
            # Set specific type we are going to collect
            collect_parties.set_element_type(CordaObject.Type.PARTY)
            #
            # Setting up collection of other data like Flows and Transactions
            #
            # Setup corresponding Config to use, and create object that will manage "RefIds" (Flows and transactions)
            collect_refIds = GetRefIds(Configs)
            # Set actual file_to_analyse that will be used to pull data from
            collect_refIds.set_file(file_to_analyse)
            # Set specific type of element we are going to extract
            collect_refIds.set_element_type(CordaObject.Type.FLOW_AND_TRANSACTIONS)

            # Pre-analyse the file_to_analyse to figure out how to read it, if file_to_analyse is bigger than blocksize then file_to_analyse will be
            # Divided by chunks and will be created a thread for each one of them to read it
            file_to_analyse.pre_analysis() # Calculate on fly proper chunk sizes to accommodate lines correctly
            #
            # Add proper methods to handle each collection
            #
            file_to_analyse.add_process_to_execute(collect_parties)
            file_to_analyse.add_process_to_execute(collect_refIds)

            # Start all threads required
            # start a time watch
            # Diagnóstico de hilos
            # current_threads = threading.enumerate()
            # write_log(f"{Icons.INFO} Hilos activos antes del análisis: {len(current_threads)}")
            # for t in current_threads:
            #     write_log(f"  - {t.name} (daemon: {t.daemon})")


            file_to_analyse.start_stop_watch('Main-search', True)
            analysis_thread = threading.Thread(
                target=_analysis_process,
                args=(special_blocks,),
                name="File Analysis",
                daemon=True
            )
            analysis_thread.start()
            write_log(f'Started analysis for: {file_to_analyse.filename}')
            # Verifica que el hilo se inició
            # write_log(f"{Icons.SUCCESS} Hilo de análisis iniciado: {analysis_thread.name}")
            # write_log(f"{Icons.INFO} Hilos activos después: {len(threading.enumerate())}")

        def _logging_resize():
            """
            Will resize logging text edit to adapt it to its container window...
            :return:
            """
            window_size = TTkWindow_logging.size()
            new_size = (window_size[0]+5, window_size[1]+4)
            TTkTextEdit_logging.resize(window_size[0]-5,window_size[1]-4)

        def _quickview_resize():
            """
            Will resize logging text edit to adapt it to its container window...
            :return:
            """
            window_size = self.TTkWindow_quickview.size()
            new_size = (window_size[0]+5, window_size[1]+4)
            TTkTextEdit_quickview.resize(window_size[0]-5,window_size[1]-7)

        def _run_analysis(ref_id, file_to_analyse, co):
            """
            Función que ejecuta el análisis en un hilo separado
            """
            try:

                write_log('=')
                write_log('=')
                write_log('=')
                write_log('=============================================================================')
                write_log(f'Starting Trace for {ref_id}')

                # Proceso de análisis
                uml_trace = UMLStepSetup(get_configs(), co)
                uml_trace.file = file_to_analyse
                uml_trace.parallel_process(co)

                c_uml = CreateUML(co, file_to_analyse)
                script_file = c_uml.generate_uml_pages(
                    client_name=self.customer,
                    ticket=self.ticket,
                    output_prefix=ref_id
                )

                if not script_file:
                    write_log('No useful information was related to this reference id', level='WARN')
                else:
                    write_log("\n".join(script_file))
                    success = CreateUML.render_uml(file=script_file)
                    if success:
                        self.add_generated_file(ref_id, script_file)

                write_log('=============================================================================')

            except Exception as e:
                write_log(f"Error during analysis: {str(e)}", level='ERROR')

        def _start_trace(ref_id, file_to_analyse, co):
            """
             Método que lanza el análisis en un hilo separado
            """
            # Mostrar mensaje de inicio en UI
            write_log(f"Starting analysis for {ref_id}...")

            # Crear y lanzar el hilo
            analysis_thread = threading.Thread(
                target=_run_analysis,
                args=(ref_id, file_to_analyse, co),
                name=f"AnalysisThread-{ref_id}",
                daemon=True  # El hilo se cerrará cuando termine la aplicación
            )
            analysis_thread.start()

            # Opcional: guardar referencia al hilo para poder monitorearlo
            # self.active_threads.append(analysis_thread)

        def _trace(source):
            """
            Trace
            :param source: reference id for the object to trace
            :return:
            """
            global file_to_analyse

            if source == 'flow':
                ref_id = ttk.TTkString.toAscii(list_flow.selectedLabels()[0])
                TTkButton_flow_trace.setEnabled(False)

            if source == 'txn':
                ref_id = ttk.TTkString.toAscii(list_transactions.selectedLabels()[0])
                TTkButton_tx_trace.setEnabled(False)

            if not source:
                return

            sref_id = remove_unicode_symbols(ref_id)
            co = CordaObject.get_object(sref_id)

            if not ref_id or not co:
                write_log("Reference ID not found unable to trace it, please try another", level='WARN')
                return

            _start_trace(ref_id, file_to_analyse, co)

        def _show_hide_window(window_name):
            """
            Show/hide window
            :param window_name:
            :return:
            """

            if window_name == 'party':
                if TTKButton_show_party.text() == 'Show':
                    self.TTkWindow_party.setVisible(True)
                    TTKButton_show_party.setText(ttk.TTkString('Hide'))
                else:
                    self.TTkWindow_party.setVisible(False)
                    TTKButton_show_party.setText(ttk.TTkString('Show'))

            if window_name == 'flow':
                if TTKButton_show_flow.text() == 'Show':
                    self.TTkWindow_flow.setVisible(True)
                    TTKButton_show_flow.setText(ttk.TTkString('Hide'))
                else:
                    self.TTkWindow_flow.setVisible(False)
                    TTKButton_show_flow.setText(ttk.TTkString('Show'))

            if window_name == 'txn':
                if TTKButton_show_txn.text() == 'Show':
                    self.TTkWindow_transaction.setVisible(True)
                    TTKButton_show_txn.setText(ttk.TTkString('Hide'))
                else:
                    self.TTkWindow_transaction.setVisible(False)
                    TTKButton_show_txn.setText(ttk.TTkString('Show'))

        ttk.pyTTkSlot([])
        def _quick_view_check(type, selected_item):
            """

            :param selected_item: a list of selected ttkstrings...
            :return:
            """

            label=selected_item[0].toAscii()

            if type == 'flows':
                if self.exist(label):
                    TTkButton_flow_trace.setEnabled(False)
                    TTkButton_flow_quickview.setEnabled(True)
                else:
                    TTkButton_flow_trace.setEnabled(True)
                    TTkButton_flow_quickview.setEnabled(False)
            else:
                if self.exist(label):
                    TTkButton_tx_trace.setEnabled(False)
                    TTkButton_tx_quickview.setEnabled(True)
                else:
                    TTkButton_tx_trace.setEnabled(True)
                    TTkButton_tx_quickview.setEnabled(False)

        def _quick_view(ref_id):
            """
            Show Ascii version of Sequence Diagram
            :return:
            """

            ref_id = ref_id[0].toAscii()

            if ref_id in self.generated_files:
                filename = self.generated_files[ref_id][0]
            else: return

            TTkTextEdit_quickview.setText("")

            self.TTkWindow_quickview.setVisible(True)
            basename, ext = os.path.splitext(filename)
            filename = f"{basename}.utxt"
            try:
                with open(filename,'r') as huml:
                    for each_line in huml:
                        TTkTextEdit_quickview.append(each_line.rstrip())
            except IOError as io:
                write_log(f"Unable to open file {filename} due to : {io}")

        def _viewlogfile():
            """

            :return:
            """

            logfile_viewer = InteractiveWindow.LogfileViewer()

            logfile_viewer.loadfile(self.filename)

            logfile_viewer.TTkWindow_logviewer.setParent(self.root)

            root.layout().addWidget(logfile_viewer.TTkWindow_logviewer)

        @pyTTkSlot()
        def _add_new_data(type=None):
            """
            Add new customer
            :param type: Customer or ticket
            :return:
            """
            global TTkWindow_popup_new_data

            TTkWindow_popup_new_data = root_window_popup_add_customer_ticket.getWidgetByName('TTkWindow_popup_new_data')

            ttk.TTkHelper.overlay(TTkButton_new_customer, TTkWindow_popup_new_data, -2, -1)
            if type and type == 'ticket':
                TTkLineEdit_popup_newcustomer_customer.setText(self.customer)
                TTkLineEdit_popup_newcustomer_customer.setEnabled(False)

            # TTkButton_new_customer.setEnabled(False)
            # TTkButton_new_ticket.setEnabled(False)

        def _process_new_data():
            """
            Adding new data
            :return:
            """

            app_path =f"{os.path.dirname(os.path.abspath(__file__))}/plugins/plantuml_cmd/data"

            self.customer = TTkLineEdit_popup_newcustomer_customer.text().toAscii()
            self.ticket = TTkLineEdit_popup_newcustomer_ticket.text().toAscii()
            if not self.customer:
                write_log('Please supply a valid customer name...')
                return

            if not self.ticket:
                write_log('Please supply a valid customer ticket...')
                return

            os.makedirs(f'{app_path}/{self.customer}/{self.ticket}')

            TTkComboBox_customer.addItem(self.customer)
            TTkComboBox_ticket.addItem(self.ticket)
            TTkComboBox_customer.setCurrentText(self.customer)
            TTkComboBox_ticket.setCurrentText(self.ticket)
            TTkButton_new_customer.setEnabled(True)
            TTkButton_new_ticket.setEnabled(True)
            TTkWindow_popup_new_data.close()


        def _close_popup_new_data():
            """

            :return:
            """
            global TTkWindow_popup_new_data

            TTkWindow_popup_new_data.close()
            TTkButton_new_customer.setEnabled(True)
            TTkButton_new_ticket.setEnabled(True)


        def _exit_application():
            """
            Close all operations and exit
            :return:
            """




        # Data generated using ttkDesigner
        customer_info_widget = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJy9l+9PGzcYx0NzSQjpJYQCK6WTTntRsVXLKAypgnUdUNp1V7pIZK3UaorMxWCLyzm68xUyqdJeJpJf3t7v1bY/bn/EHt85JqFJIEgs0Sn+cfb34+d5bD/53fjjXzMV" +
            "fz5GK8Lg7RaORLFWO/mFfvOMOWETezwSuQ/YDyjzIpFZqzyqrEYizUMaySEZx0VBEInbMGaXeRxRD/uRyLaQj5pB/IrxGjVh1pl96HtLvQY7jcR0lQWUyyl/jVZsw76F" +
            "hXFAf8Nx9YV9D4v8PvWst7TBSWSnYDDUfsT0mHBZze+jM9X5Uyo1JfuhQfUnLbk3NKCHLo46IrfnISg1ZLHGmFujrUikYFlV1GhQ7zgWTSVfLLKvUJuFsOo8LEmVQ5F1" +
            "kxIsiOTIfZL/CIt4gVkTc7+thgM3jwIx7RDqNnws1xa/LqZhpue+tIIct0IK/S2mVL8FyqQkS0/tRUzKdorMwXMnXguZT34WOmSxQz4jd8mSfHMq+WKyTO6L7A7zG2D5" +
            "jsjUKIdlC3M3DDjw+dZL74hFIfm8j51YCfITex6QyRcw3znqK3SI3QFU1WIqWYWal6WynQfUqVGowqjhM2nMHs0mBNEucxkEibH8frUJXdsuPfbiSLOnQpH2IUDAx2mH" +
            "ufI3B/WghTzoFDloU+UwWc16D3Omh/n1Iw2angCUPAaHU+cEc8vajMimoiPfgRR5Ar74Hp6nMP6Hnra4I51IXbwTcs68qhzsa7MN7zSTUMsosHmJWLZLAJYeA2YeYBc7" +
            "3ELWEcwYkYcdsCfBzokM66grcnEFArwrjCqCTSGmKhDeu6gVbzFRkCDWM4pcdgztUOOwoSFEtl3Xkn2BtfLVl/DetuPgFrf2WQPH2ywep2qjrCC3SbJIvfa7uqkecOTz" +
            "OvKQ2w5ooA0wPWiA2REG6CoDFA/kNNa2nuZhh/zcJdXuCKhhYbGuw6KoxM0kLMxLwsKs+cgLkCNtGVwtNIbpf6v1ZyfUf+7CDrCSz/X117T+7Qn1q2B7ioNr6c/29Otq" +
            "FkVR0hS5hCI1ngKeTVFafr/+eGtta3VrbWNj66oICxqh35Gao/h/cRQ1R+xQDTB7wwDvegDzfduSsNM63NG8rTCWtD9mEozsAAYU+0PCOIDxsAu743fhu/7DsF/5yJXD" +
            "lfDsDQrfuyDMzyNA6xdvUH/uXP8DxafJ8R3rPrCz+gyMdQvjdPNvYHTv9B8vLgpxKtY8ZDvsLOr3fa+x7qi7WKEU9I2uUDKjUZb6c6U485jea1CuLqKCvOyt+D6vRLYh" +
            "zJdegOHgrjKXOm15aw/NQkBCZSETnGcbin5BGzIzjP7T8ywjE81Jz7E5vXmlE+qBzFUT/WWtn03005fopyuVilQvD2xieK64jRfPY8rDpxed+eCiM8vj4qr0GsKql5rF" +
            "XFcO7flBDB7nThoiPQhRGgdhSogk97oSwp/9TtFBPQBQuAgwSUiTv7rkb9sg/9jp68brsJOvCf9/6viM9hhX7PJgFpS9JA009uLBo3Mf/GkTCkNRcJjnYXXtAXPlPyXB" +
            "MhE="))

        root_window_logging = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyFkltv0zAUgFPSNu0KjLFxG0OKeOpTubxzETBAZB0VK0wITZOXWDkWiV3FNqxIk3gs0nk0/5fjJEyTeCBW5HP3+Xz8s/t7Owzq78yNsWuWC+7w6nz+9aN48EqltuTS" +
            "OIy+8UoLJR32Hk8eTR46DI0Vzqf00oJp7fAy5bxU0jAheeWwv2AVK3Ud0t1nJVVdm5LvUMhMfXc4mCktjC955MbJpSTk2D0QP3itHifbHIdTIeNDkRlwSUDJpL3lIgfj" +
            "1eGUnbbOd0HQ8X4ytP7GEn0SWpwU3K0w2pWMpMyLc6WKuVg4DAhrxrJMyLw+NGgWx/4eWypL1ENCamWL/aKRCAgi2IHhGUG84arkplq26dS3cRoHKYgiq7hnq8PrSi25" +
            "TxzDCDfOTceFynPfBVzxfXSSdQ7rXjpKRhw2kgCu079ZU8FWs91Ywc0V3ILbcMdHhpRFi8Nd2MH+C1VlNIMV9ubC0AXgtVmlchpHXHKtWc79uJqz49cFy7W/sWBg4d4F" +
            "OIgbpi9JRExw/y/KiPqe81OzmwlzDrN5wfgPTtDifE76/8XB0R69n3jflidE8Au3LqjxgWGV8ZX9A/jAWRa/l8WSotamtjAi9rFuZTGs6J4pJkxV4feIdL1g0iUdjMjW" +
            "ypZZeEKtPKX/WdKB57XJ4ihVUvLUP05NE7STP/YXD1c="))

        root_window_flow = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyNk1lv00AQgB3lcJIeKVdJRYEICdEqqBw/oU1bwKRqVdM+ocjYS2dVxxvsdQ+kSn1MpHlBWp554A/yE5j1OqEIQolleY6dmW9mJ5elrwtlK/tdqBUsyfMBUzjvusfv" +
            "+LOO8NM+i6RC+4TFCReRwvLLtRdrzxUWZcqVDin7oZckCmcpZkNE0uMRixVWBl7s9ZPsSGnH61PWhS75DnkUiNPex1CcUlB1VyRc6sTv1YpTcgoMS/v8M8vUrvOQYa3L" +
            "o9YhDyQox8K61l4xfgRSq7Wud5Y731hWQfvJkPuNxT7gCf8QMjVEezPySAq06AoRunyg0KLmdr0g4NFRVtQyD8PKW+9cpNR7jRrL5RQroZGoLbBhGWoX1MQ2E30m4/M8" +
            "nLilSrDqAw+DmOnesuNYpUxbsZ6FjluBGZwbW7KBKJjTCAUqDw0ttZ0HDG44Ftyk91bWENw2nztDWBzCXWjCkonJHgb3YBkr6yIO6BKGWHa5pN6xvJXNO4X7V8ChZXhX" +
            "nWXihUeUx3gfj/Fmr+LldNaEbtVZ+k+68VA1HbRH8BSa01CWchQzMVvPnidSXSXSht/nVciJnjiL1xLh/D4Lma+XrtUVAVNOAaudqJMrVorFmFLTdhV9EeqvTXoy8CJ9" +
            "0iZbLqdeCh2qs0nvllOAbTIZar0x66mUtNZj7sbE1PNDkbAcfU6PMEOvO0WNbhN6cSp6yWVntJHlDZOiPcTaBjD/WK+1GqGdKbTgoylk8PovPDL2fDa53DHPrOGp/4sH" +
            "drD+49uX7y3XpGgPYXcEe9dXb/6qru+x9ynl/vEJZ+MbbU4wGgajcQ1GgzAuW3s6TesgyzOdhf1p8tIUZ3wRRWYvEvrHpms/AbsJn7E="))

        root_window_party = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyVk8tv00AQhx3sxElDgVLSljdCPeQUHice4kBIAWGCKtW0CFEVYw+dVRxvZK9pg1SJYyLtcfl/mV07gRxawJbleeyOv9/M+ofzc9exzHWi2tIR4xEoecH3B+/ZvR4P" +
            "8yEkQkn3G6QZ44mS1YedB537StoiZ0pvqYZxkGVK1mnPyzQY0vbaKCAjM2nnnQld6gcs2WNJxI8OKCvGtGGbZ0zoovuq7Z3zKiCdHfYdjPvZuway0WfJnT0WCVSeJZe0" +
            "9xrYIQrtNvrBcZl8Y1kVnadAmS8i7i7L2JcY1ES6W0lAVqRNn/PYZyMlLRK2HUQRSw7NR63iBll7G4x5TrobJGpm17o8jSBVU1n1maCquJHLWlxkSSq6eAMbJyTsFfAh" +
            "iHRcliQtQmWyHiKLoxSM3mJ9Xa9vY9M03DSvbA4uFz2xAC9q65O3DrjiWXiZnlWjDq8Ur9YE1ya4jht4Va+sFDfgdaK5OcFbWmIqGGQqx9t/YOLdgu6j1yI63NwvNFB7" +
            "/IGfAskr2ZbLwAJaZY72wWv9FU26O5wYqM2TXNopP9IDtEMe67dLfjYKEuVVpEux0s6DHB9Rycf0PPEq+JRCBaEeSjcXgk7OjHF1HjqgeS6QOrp1hrTp2Zq0SqT2qaSO" +
            "D8c0bPt5FCnqn2y8QAgH+uzQ4F3j0CmansKGz2ZEa7+JhjxiX8cLUCtzqKUCqn4WFHZlrW+KaCTsTXHrvwAiiEEszm9zDnD+HwF6pshZAJDnshnyJIFQ/9YZnfO88wuZ" +
            "OGi9"))


        root_window_transaction = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyNk91PE0EQwK/241pAikL5iDU2JiYkEPz4E2gB9SyBcMoTIevdymy47ta7PQomJDyWZF9M1mcf/Af9E5y9vTZNLGIvl5uPnZnfzE5vSj82y072u9brqiSv+lSred8/" +
            "/8hedkSQ9iiXWrkXNE6Y4FqV32y93nqlVVGmTJuQchCRJNFqDmPagkvCOI21qvRJTHpJdqS0T3qYdaGLvmPGQzE4/RKJAQZVD0TCpEl8ote9kveAqtIR+0Yztes9o6rW" +
            "Zbx1zEIJ2nPUjNHeUnYG0qi1LrnMne8dp2D8aMj91uJ+Ygn7HFE9VO4OJyiFRvSFiHzW18rB5g5IGDJ+lhV17ENV5QO5Ein2XsPGcjlVlchK2Ba40ITaNTaxR0WPyvgq" +
            "D0duqRNVDYBFYUxNb9lxVcVMu7GZhYlbh1nVGFlOZUx4QgIzi0TDQ4NSQAyoG2nHa1J45DnwGN/FrDFYsp/GEJaHsAKrsDaJD0+gqSrbIg7xMm5V2WcSZwCrKTydQIeW" +
            "jcD8SAzPMYP1vhgBLk0DzPkcrzDmW/lPvoJ9Mj7YGMIm7s1k59P52l4j57ODdM2VsESO57iYG6ZSjqa47TXupVTzRzSiWXyrK0KqvYKqdngnV5xUFWMxMLtXDERkvi7q" +
            "SZ9wc9JFWy6nJIUO1tnBd9crwB6aLLzZp+1USkOY49fHJtNAQMfoazn6nFc06DOIXrwTveTTS9zXmd8/v/9q+TbPxlDV2kCDc7P5uAhupuB/4PYOPHg3BSqIRDKCqo+h" +
            "Zi2U+y8o2Fflto3G2z64hcP7Cy9PTOPy9GvKgvMLRgd5/ea4/oKtX7+nfh3ncdM6NGlaNs/dJPRvE0lTNRsIzmm+oic63foDVDusZQ=="))

        root_window_quickview = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyFU0tv00AQdogTJw1QUQq00EoWp5zC48xDagkg3JRCDb1Qoo296q5i7wZ7t02QKvXAIZXmgrSc+Yv8BGZtByIueGXtzOw8vm929sL98a3uFN+56YKrZhNq4HoYjj/w" +
            "By9kpFMqlAHvlGY5l8JA43HvUe+hgbrS3NiQRpSQPDdwFWN2pVCEC5oZaE5IRtK8cHH3SYpZVwZ4dsRFLM8MtA5kzpVNeWy6wZWgTsE95F9poQ6DuxTaAy78Ix4rZgIH" +
            "g1F7TfkJU1ZtD8i0OnzjODV7jobqvLR4H3nORwk1c/D6gqAUWzGUMgn5xICDtA5IHHNxUhR1ykWhuUdmUiPrNlKqZA3NpJSQEPPYFmufI4lXVKZUZbMqHHErk0MrYjyJ" +
            "M2q5Fe7QwkwvM9sFG9dlHVhbWIZfNI/Gp5yeGXatwkHZqpU+YxvYjcBha/jfLFix9XK7NWe35+wO22Cb1rNWLsrusS1o7sgsxjuYQyPkChsAq79+fr/w39lCflFJs+0l" +
            "Hswv4X8KNhA+u79A3UGMIZ2qfszVH+DbS8a/2IcRXr0dlX85YM7/coDOHg6Nv6/TEcK+hPUl1T9UJFP2juytv6ck9t+KZIbkVgY6Udy3vmauoZ7hWKFPPZKJ3T3U8wkR" +
            "JqiBh7ZK1kSDh0Otd0iGNKE5kkrJ1IqNrJgey35BdrPw1OghlrjSqe2HBe7aThhw+9YC7V1Go7GdNCThFQrO3KXO8YGwJ8j/Kf7Pghp7XuDQ0MGuCRrZZ5BjXd37DUw+" +
            "PWo="))

        root_window_popup_add_customer_ticket = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyVlN9PE0EQx69py7VFICAKCpoLMYaEWIHoAxh/QMUfnBUSqzwYJMfdhtlw3W3u9gRMSHykyfpgsr74wot/nU/8Cc7eL0At0TaXm5m92f18Z3b3c+nbz7IR/w7VtCyJ" +
            "gw5RcrDV2n1L7z7lbtQmTChpfiRBSDlTsjxfn6vPKlkUEVU6pez6ThgqeQlzGpwJhzISKNnXcQKnHcaflF47bZy11sSxDco8vqdkZZ2HVOgpN9W0PWQXiSy9oZ9I7N63" +
            "B4isNimzNqgnQNkGJqP3gtAdENqtNp39dHDVMAp6HAPpeBIx39GQbvtEHUlzhTloedpsce63aEdJA2WtO55H2U68qJH8iex75RzwCFVXUVJqR7LPTywUBCZMQvUQRTwn" +
            "vE1EcJCmI7dQoay4QH0vIFpb/Hk8U6pcJ05DvxzPQ1sd3ok6W4zsbXmOcBQMaJyCXSAwpK15u5/AsG3ACD6XY3EwmryuHMHVIxiDcbiW5iR5EzAp+5Z54GErjmS5RQXW" +
            "QY4txWotXMlyo1AgexDW63VsXkJiPfOdnVDXz6hEcOOMVLAShbN2FRXCFK6WKKvENdomfi7sTCQWUsTeJkIGNdqwPYhCCr2EyFKL7GPtBxspoMVw8yzixmtwn+PGKk28" +
            "n21jb5Z8usPi3WkXIlkMsLS4L4ou9/XbRD/sOAwHpYmx1I4SSfcy1lrGemcupy3/By0s4Fmh7i4RFova2yRYVPAgRYSHuB48wp49xucJTrKUAch+vS4elBWPirxwt88E" +
            "T/dE1qitzEhBR/KyjiaghXOgaJ7WtPaSdSJhtfThxoJUV1zgVpN76BmwAOM9MGE1Q7t1MZqIS5CDlf8VDNbQW7+QIT46y5EQeFNkNDfz0F9Y+G7eSfM8h9mbY0GaJ8df" +
            "v1hrtoKZrqw2gLi7+spQXWnGDl4e3V5l2sjApi4Ccx3m5ofi+u9wtYvgaifHP7430vyZLmx24cNfaMifISeKZL/LGSOuvmxDvJGi+i97/O4V"))


        root=TTk()

        self.TTkWindow_customer_info = ttk.TTkWindow(parent=self.root,
                                                     pos=(17, 1), size=(67, 26),
                                                     title=ttk.TTkString("Logs Tracer", ttk.TTkColor.ITALIC),
                                                     border=True,
                                                     layout=ttk.TTkGridLayout())


        self.TTkWindow_flow = ttk.TTkWindow(parent=self.root,
                                                     pos=(85, 1), size=(45, 34),
                                                     title=ttk.TTkString("Flows", ttk.TTkColor.ITALIC),
                                                     border=True,
                                                     layout=ttk.TTkGridLayout(),
                                                     flags=ttk.TTkK.WindowFlag.WindowMinimizeButtonHint)

        self.TTkWindow_party = ttk.TTkWindow(parent=self.root,
                                             pos=(85, 4), size=(98, 30),
                                             title=ttk.TTkString("Party", ttk.TTkColor.ITALIC),
                                             border=True,
                                             layout=ttk.TTkGridLayout(),
                                             flags=ttk.TTkK.WindowFlag.WindowMinimizeButtonHint)

        self.TTkWindow_transaction = ttk.TTkWindow(parent=self.root,
                                             pos=(130, 1), size=(71, 32),
                                             title=ttk.TTkString("Transaction", ttk.TTkColor.ITALIC),
                                             border=True,
                                             layout=ttk.TTkGridLayout(),
                                             flags=ttk.TTkK.WindowFlag.WindowMinimizeButtonHint)

        self.TTkWindow_quickview = ttk.TTkWindow(parent=self.root,
                                                 pos=(40, 1), size=(120, 32),
                                                 title=ttk.TTkString("Quick View", ttk.TTkColor.ITALIC),
                                                 border=True,
                                                 layout=ttk.TTkGridLayout(),
                                                 flags=ttk.TTkK.WindowFlag.WindowMinMaxButtonsHint)


        # TUI-Window.py:
        # "Name": "MainWindow",
        # "Name": "TTkFrame",
        # "Name": "TTkLabel",
        # "Name": "TTkLineEdit_customer",
        # "Name": "TTkLabel-1",
        # "Name": "TTkLineEdit_ticket",
        # "Name": "TTkFileButtonPicker",
        # "Name": "TTkLabel_logfile",
        # "Name": "TTkButton_start_analysis",
        # "Name": "TTkLabel-3",
        # "Name": "TTkLabel-4",
        # "Name": "TTkLabel-2",
        # "Name": "TTkLabel_Parties",
        # "Name": "TTkLabel_Transactions",
        # "Name": "TTkLabel_Flows",
        # "Name": "TTkLineEdit_logfile",

        # forms/window_logging.tui.json
        # "Name": "MainWindow",
        # "Name": "TTkWindow_logging",
        # "Name": "TTkTextEdit",

        # Pull all required components
        TTkFileButtonPicker: ttk.TTkFileButtonPicker = customer_info_widget.getWidgetByName('TTkFileButtonPicker')
        TTkComboBox_customer: ttk.TTkComboBox = customer_info_widget.getWidgetByName('TTkComboBox_customer')
        TTkComboBox_ticket: ttk.TTkComboBox = customer_info_widget.getWidgetByName('TTkComboBox_ticket')
        TTkLabel_file_size: ttk.TTkLabel = customer_info_widget.getWidgetByName("TTkLabel_file_size")
        TTkButton_new_customer: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_new_customer')
        TTkButton_new_ticket: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_new_ticket')
        TTkButton_main_exit: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_main_exit')

        TTkButton_start_analysis: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_start_analysis')
        TTkWindow_logging: ttk.TTkWindow = root_window_logging.getWidgetByName("TTkWindow_logging")
        TTkTextEdit_logging: ttk.TTkTextEdit = root_window_logging.getWidgetByName('TTkTextEdit_logging')
        TTkLabel_Parties = ttk.TTkLabel = customer_info_widget.getWidgetByName('TTkLabel_Parties')
        TTkLabel_Transactions = ttk.TTkLabel = customer_info_widget.getWidgetByName('TTkLabel_Transactions')
        TTkButton_tx_trace: ttk.TTkButton = root_window_transaction.getWidgetByName('TTkButton_trace')

        TTkButton_flow_trace: ttk.TTkButton = root_window_flow.getWidgetByName('TTkButton_trace')
        TTKButton_show_party: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_show_party')

        TTKButton_show_txn: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_show_transaction')
        frame_quickview:  ttk.TTkFrame = root_window_quickview.getWidgetByName('TTkFrame_quickview')
        TTkmenuButton_quickview_exit = root_window_quickview.getWidgetByName('menuButton_quickview_exit')
        TTkTextEdit_quickview: ttk.TTkTextEdit = root_window_quickview.getWidgetByName('TTkTextEdit_quickview_content')
        TTkButton_flow_quickview = root_window_flow.getWidgetByName('TTkButton_flow_quickview')
        frame_transaction = root_window_transaction.getWidgetByName('TTkFrame_transactions')
        TTkButton_tx_quickview = ttk.TTkButton = root_window_transaction.getWidgetByName('TTkButton_tx_quickview')
        list_transactions = root_window_transaction.getWidgetByName('TTkList_transaction')
        frame_flow = root_window_flow.getWidgetByName('TTkFrame_flow')
        TTkLabel_Flows = ttk.TTkLabel = customer_info_widget.getWidgetByName('TTkLabel_Flows')
        TTKButton_show_flow: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_show_flow')
        list_flow: ttk.TTkList = root_window_flow.getWidgetByName('TTkList_flow')
        TTkButton_viewfile: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_viewfile')

        TTkWindow_popup_new_data = None
        # TTkWindow_popup_new_data: ttk.TTkWindow = root_window_popup_add_customer_ticket.getWidgetByName('TTkWindow_popup_new_data')
        # TTkWindow_popup_new_data_org = ttk.TTkWindow = root_window_popup_add_customer_ticket.getWidgetByName('TTkWindow_popup_new_data')
        TTkButton_popup_newcustomer_ok: ttk.TTkButton = root_window_popup_add_customer_ticket.getWidgetByName('TTkButton_popup_newcustomer_ok')
        TTkButton_popup_newcustomer_cancel: ttk.TTkButton = root_window_popup_add_customer_ticket.getWidgetByName('TTkButton_popup_newcustomer_cancel')
        TTkLineEdit_popup_newcustomer_customer: ttk.TTkLineEdit = root_window_popup_add_customer_ticket.getWidgetByName('TTkLineEdit_popup_newcustomer_customer')
        TTkLineEdit_popup_newcustomer_ticket: ttk.TTkLineEdit = root_window_popup_add_customer_ticket.getWidgetByName('TTkLineEdit_popup_newcustomer_ticket')

        frame_flow.move(60,4)

        # pop window new customer/ticket
        TTkButton_popup_newcustomer_ok.clicked.connect(_process_new_data)
        TTkButton_popup_newcustomer_cancel.clicked.connect(_close_popup_new_data)

        # TTkWindow_popup_new_data.setVisible(False)

        # FilePicker
        TTkButton_viewfile.setEnabled(False)
        TTkFileButtonPicker.pathPicked.connect(_filetxtchange)
        TTkButton_viewfile.clicked.connect(_viewlogfile)

        # Party
        frame_party = root_window_party.getWidgetByName('MainWindow_party')

        tree_party: ttk.TTkTree = root_window_party.getWidgetByName('TTkTree_party')
        TTKButton_show_party.clicked.connect(lambda: _show_hide_window('party'))

        #Main window
        TTkFileButtonPicker.setEnabled(False)
        TTkFileButtonPicker.pathPicked.connect(_filetxtchange)
        TTkButton_start_analysis.clicked.connect(_start_analysis)
        TTkComboBox_customer.currentTextChanged.connect(_fill_tickets)
        TTkComboBox_ticket.currentTextChanged.connect(_enable_file_select)
        TTkButton_new_customer.clicked.connect(_add_new_data)
        TTkButton_new_ticket.clicked.connect(lambda: _add_new_data('ticket'))
        TTkButton_new_ticket.setEnabled(False)
        TTkButton_main_exit.clicked.connect(_exit_aplication)


        # Flow
        TTkButton_flow_trace.setEnabled(False)
        TTkButton_flow_trace.clicked.connect(lambda: _trace('flow'))
        TTKButton_show_flow.clicked.connect(lambda: _show_hide_window('flow'))
        list_flow.textClicked.connect(lambda: _quick_view_check('flows', list_flow.selectedLabels()))
        TTkButton_flow_quickview.clicked.connect(lambda: _quick_view( list_flow.selectedLabels()))

        # Transaction
        TTkButton_tx_trace.clicked.connect(lambda: _trace('txn'))
        TTKButton_show_txn.clicked.connect(lambda: _show_hide_window('txn'))
        TTkButton_tx_quickview.setEnabled(False)
        list_transactions.textClicked.connect(lambda: _quick_view_check('transactions',
                                                                        list_transactions.selectedLabels()))
        TTkButton_tx_quickview.clicked.connect(lambda: _quick_view( list_transactions.selectedLabels()))

        # Quick View
        self.TTkWindow_quickview.addWidget(frame_quickview)
        TTkButton_flow_quickview.setEnabled(False)
        TTkmenuButton_quickview_exit.menuButtonClicked.connect(lambda: self.TTkWindow_quickview.setVisible(False))
        _quickview_resize()

        # LogViewer

        TTkWindow_logging.move(4,28)
        TTkWindow_logging.sizeChanged.connect(_logging_resize)
        self.TTkWindow_quickview.sizeChanged.connect(_quickview_resize)
        TTkWindow_logging.setWindowFlag(ttk.TTkK.WindowFlag.WindowReduceButtonHint|ttk.TTkK.WindowFlag.WindowMinimizeButtonHint)

        self.TTkWindow_flow.setVisible(False)
        self.TTkWindow_transaction.setVisible(False)
        self.TTkWindow_party.setVisible(False)
        self.TTkWindow_quickview.setVisible(False)

        self.TTkWindow_transaction.addWidget(frame_transaction)
        self.TTkWindow_flow.addWidget(frame_flow)
        self.TTkWindow_customer_info.addWidget(customer_info_widget)
        self.TTkWindow_party.addWidget(frame_party)

        customers = _check_folders()
        if customers:
            TTkComboBox_customer.addItems(customers)

        tui_logging = TTkTextEdit_logging

        root.layout().addWidget(self.TTkWindow_customer_info)
        root.layout().addWidget(self.TTkWindow_party)
        root.layout().addWidget(self.TTkWindow_flow)
        root.layout().addWidget(self.TTkWindow_transaction)
        root.layout().addWidget(self.TTkWindow_quickview)
        root.layout().addWidget(TTkWindow_logging)
        # root.layout().addWidget(TTkWindow_popup_new_data)
        InteractiveWindow.update_tui_from_queue()

        root.mainloop()

    @staticmethod
    def update_tui_from_queue():
        while not log_queue.empty():
            message = log_queue.get_nowait()
            tui_logging.append(message)  # Tu widget de logs en PyTermTk
            # tui_logging._verticalScrollBar.setValue(tui_logging._verticalScrollBar.maximum())



        # Volver a revisar en 500 ms
        threading.Timer(0.5, InteractiveWindow.update_tui_from_queue).start()

def main():
    log_file = None
    Configs.load_config()

    # Define default entity object endpoints...
    UMLEntityEndPoints.load_default_endpoints()

    # in this case I'm removing initial branch 'UML_SETUP' because final config is a collection of configuration settings
    # that removes this.

    if not args.log_file:
        print('You must provide a log file to scan')
        exit(0)
    else:
        log_file = args.log_file

    if log_file:
        # Create file_to_analyse object containing file_to_analyse that will be analysed, starting with a block-size of 15 Mbytes
        file_to_analyse = FileManagement(log_file, block_size_in_mb=15, debug=True)
        # Analyse first 50 (by default) lines from given file_to_analyse to determine which Corda log format is
        # This is done to be able to separate key components from lines like Time stamp, severity level, and log
        # message
        file_to_analyse.discover_file_format()
        #
        # Analyse file for specific block lines that lack of key fields (like stack traces, and flow transitions):

        special_blocks = BlockExtractor(file_to_analyse, Configs.config)
        special_blocks.extract()
        special_blocks.summary()
        #
        #
        # Setup party collection
        #
        # Set actual configuration to use, and create object that will manage "Parties"
        collect_parties = GetParties(Configs)
        # Set file_to_analyse that will be used to extract information from
        collect_parties.set_file(file_to_analyse)
        # Set specific type we are going to collect
        collect_parties.set_element_type(CordaObject.Type.PARTY)
        #
        # Setting up collection of other data like Flows and Transactions
        #
        # Setup corresponding Config to use, and create object that will manage "RefIds" (Flows and transactions)
        collect_refIds = GetRefIds(Configs)
        # Set actual file_to_analyse that will be used to pull data from
        collect_refIds.set_file(file_to_analyse)
        # Set specific type of element we are going to extract
        collect_refIds.set_element_type(CordaObject.Type.FLOW_AND_TRANSACTIONS)

        # Pre-analyse the file_to_analyse to figure out how to read it, if file_to_analyse is bigger than blocksize then file_to_analyse will be
        # Divided by chunks and will be created a thread for each one of them to read it
        file_to_analyse.pre_analysis() # Calculate on fly proper chunk sizes to accommodate lines correctly
        #
        # Add proper methods to handle each collection
        #
        file_to_analyse.add_process_to_execute(collect_parties)
        file_to_analyse.add_process_to_execute(collect_refIds)

        # start a time watch
        file_to_analyse.start_stop_watch('Main-search', True)
        # Start all threads required
        file_to_analyse.parallel_processing()
        # Prepare new execution
        # Clean up old processes:
        file_to_analyse.remove_process_to_execute(CordaObject.Type.PARTY)
        file_to_analyse.remove_process_to_execute(CordaObject.Type.FLOW_AND_TRANSACTIONS)

        # Stopping timewatch process and get time spent
        time_msg = file_to_analyse.start_stop_watch('Main-search', False)

        if file_to_analyse.result_has_element(CordaObject.Type.PARTY):
            print('Setting up roles automatically...')
            file_to_analyse.assign_roles()
            print("\n X500 names found: ")
            print_parties()

            party = list(file_to_analyse.get_all_unique_results('Party'))[0]
            pending_roles = party.get_pending_roles()
            pselection = None
            if pending_roles:
                print('\nI was not able to find all roles, following roles were not assigned, please assign them manually:')
                print('   [0] -- Exit')
                while True:
                    if len(pending_roles) == 0:
                        break
                    for index, each_pending in enumerate(pending_roles):
                        print(f'   [{index+1}] -- {each_pending} which is {pending_roles[each_pending]} to assign...')
                    role_to_assign = input(f'Please choose role to assign [0-{len(pending_roles)}]:')
                    if not role_to_assign:
                        break
                    if role_to_assign.isdigit():
                        selection = int(role_to_assign)
                        if selection > len(pending_roles):
                            continue
                        if selection == -1:
                            break

                        role_list = list(pending_roles)
                        print(f'Please select party for {role_list[selection-1]}:')
                        if selection > len(pending_roles):
                            continue
                        selected_role = list(pending_roles)[selection - 1]
                        party_list = list(FileManagement.get_all_unique_results('Party'))
                        print('[ -1] [    None   ]')
                        print('[  0] [           ] Define a party not listed here')

                        print_parties()
                        while True:
                            party_selection = input(f'Select party [0-{len(party_list)}]:')
                            if party_selection.isdigit():
                                pselection = int(party_selection)

                                if pselection == 0:
                                    new_party=party.define_custom_party(rules_set=file_to_analyse.rules, assigned_role=selected_role)
                                    validation_list = file_to_analyse.parser.parse_line(new_party.name, [])
                                    if validation_list:
                                        validation = validation_list[0]
                                    else:
                                        validation = None
                                    if not validation or not validation.is_same_name(new_party.name):
                                        print('Invalid party name')
                                        continue

                                    if new_party:
                                        FileManagement.add_element('Party', new_party)
                                        break

                                if pselection > len(party_list):
                                    print('Invalid selection')
                                    continue

                                selected_party = party_list[pselection - 1]
                                selected_party.set_corda_role(selected_role)
                                break


                    if party.get_pending_roles():
                        continue
            if pselection:
                print('\n Party final assignation:')
                print_parties()

            response = input('Do you want to use this list for final analysis ([Y]es/[N]o/[M]odify) [Yes]: ')
            if response:
                if response == 'M':
                    response1 = input('What do you want to do? [D]elete / [M]odify a party:')
                    if response1:
                        if response1 == 'D':
                            while True:
                                print_parties()
                                party_list = list(FileManagement.get_all_unique_results('Party'))
                                select_party = input(f'Which party do you want to delete [1-{len(party_list)}] or just enter to exit:')
                                if select_party.isdigit():
                                    iselect_party = int(select_party)
                                    if iselect_party>len(party_list):
                                        print('Invalid selection')
                                        continue
                                    FileManagement.delete_element('Party', party_list[iselect_party-1])
                                if not select_party:
                                    break


        if file_to_analyse.result_has_element('Flows&Transactions'):
            print("\nThese total of other objects found:")
            results = collect_refIds.classify_results(FileManagement.get_all_unique_results('Flows&Transactions'))
            for each_result_type in results:
                item_count = 0
                print(f'  * {each_result_type}: {len(results[each_result_type])}')

                if len(results[each_result_type])> max_number_items_fNtx:
                    item_limit = max_number_items_fNtx
                else:
                    item_limit = len(results[each_result_type])

                for each_item in results[each_result_type]:
                    print(f"    `---> ({item_count+1:>4}) {each_item}")
                    item_count = item_count + 1
                    if item_count >= item_limit and (len(results[each_result_type])-item_limit > 0):
                        print(f"    ... there are {len(results[each_result_type])-item_limit} more...")
                        break

        print(f'Elapsed time {time_msg}.')
        ##
        # Testing
        ## -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
        # 1231B1D70E2CF011021F6379E3A802DF04E32D89784F61940A83A596EF99D1CF
        # a26f97bb-3ad3-40ac-8b6b-257bdd9bcba4
        # -l /home/larry/IdeaProjects/logtracer/client-logs/DLT-Service/CS-4010/DLT_suspendMembership.txt
        # 9888363EC1AAF0AAD8B64911D4202EA9ACE288D530B509020ADE326443B305E4
        # 49cea758-40d9-48d2-a4eb-9ce770c307fd

        ref_id = args.reference

        if not ref_id:
            while True:
                ref_id = input('Reference to trace: ')
                if ref_id or not ref_id:
                    break

        if not ref_id:
            return file_to_analyse


        co = CordaObject.get_object(ref_id) # change here for parameter
        if not co:
            print("Sorry but there's not information about {ref_id}...")
            print("Exiting...")
            return None

        test = UMLStepSetup(get_configs(), co)
        test.file = file_to_analyse
        test.parallel_process(co)
        c_uml = CreateUML(co, file_to_analyse)
        script = c_uml.generate_uml_pages(client_name='test', output_prefix=ref_id)
        print("\n".join(script))
        ##########################
        return file_to_analyse
    return None


if __name__ == "__main__":
    max_number_items_fNtx = 15
    tui_logging = None
    file_to_analyse = None

    # Small file with all roles
    # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
    # -l/home/larry/IdeaProjects/logtracer/client-logs/Grow-super/CS-3873/logsinsurance/corda-node-cordaprimary-prod-growadmin-i-0bb90aaa48c7b6b88.dlta.internal.2024-12-02-7.log
    # Very small one to test UML
    # -l /home/larry/IdeaProjects/logtracer/checks/log-test.log
    # Office
    # -l
    # /Users/larry.castro/IdeaProjects/logtracer/client-logs/Grow-super/logsinsurance/corda-node-cordaprimary-prod-growadmin-i-0bb90aaa48c7b6b88.dlta.internal.2024-12-02-23.log
    # Small size and have all roles:
    # -l
    # /Users/larry.castro/IdeaProjects/logtracer/client-logs/Finteum/CS-3462/notary-issue/node-bull-759dc59895-j7rmw.log
    # ===
    # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
    # -l "/home/r3support/www/uploads/customers/Grow Super/CS-3992/20250225103248_pack"/corda-node-dev0-ri-hes-admin-node.2025-02-19-1.log
    #
    # Huge files:
    # -l /home/larry/IdeaProjects/logtracer/client-logs/ChainThat/CS-4002/Success-Transaction-logs.log
    # -l /home/larry/IdeaProjects/investigations/lab-constructor/investigation/ChainThat/CS-4002/client-logs/mnp-dev-party005-cordanode.log
    w = InteractiveWindow()
    w.tk_window()

    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                            help='Give actual log file to analyse')
    parserargs.add_argument('-r', '--reference',
                            help='Reference ID to trace flow-id or tx-id')

    args = parserargs.parse_args()

    pass

