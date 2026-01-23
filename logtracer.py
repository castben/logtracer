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
from configparser import BasicInterpolation
from datetime import datetime

import yaml
from TermTk import TTkUtil, TTkUiLoader, TTk
import TermTk as ttk

from error_log_analysis import ErrorAnalisys
from get_refIds import GetRefIds
from object_class import Configs, FileManagement, BlockExtractor, KnownErrors, LogAnalysis
from object_class import CordaObject
from get_parties import GetParties
from support_icons import Icons
from ui_commands import schedule_ui_update, process_ui_commands, schedule_callback, process_callbacks
from uml import UMLEntityEndPoints, UMLStepSetup, CreateUML
from log_handler import write_log, HighlightCode
from log_handler import log_queue
from TermTk.TTkCore.signal import pyTTkSlot
from shutdown_event import shutdown_event
import lazy_loader


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

class CustomerInfo:
    """
    Customer information related to ticket that is being handled.
    """

    def __init__(self):
        """
        Data structure
        """

        self.attributes = {}

    def set_attribute(self, attribute, value):
        """
        Set attribute to setup
        :param attribute: attribute name
        :param value: value
        :return:
        """

        self.attributes[attribute] = value

    def get_attribute(self, attribute):
        """
        return given attribute name, stored value
        :param attribute: name
        :return: attribute value
        """

        if attribute in self.attributes:
            return self.attributes[attribute]

        write_log(f'Error requested attribute {attribute} do not exist')

        return None

    def set_full_attributes(self, new_attributes):
        """
        Set all attributes at once
        :return:
        """

        self.attributes = new_attributes

    def save_info(self):
        """
        Serialises object to save it into disk
        :return:
        """

        if not self.get_attribute('data_dir_path'):
            return

        with open(f"{self.get_attribute('data_dir_path')}/customer_info.yaml",'w') as cinfo:
            yaml.safe_dump({'customer_data': self.attributes},cinfo)
            write_log(f'Data successfully saved in {self.get_attribute("data_dir_path")}/customer_info.yaml')

    def load_info(self):
        """
        Loading saved data
        :return:
        """
        data_file = f"{self.get_attribute('data_dir_path')}/customer_info.yaml"
        if os.path.exists(data_file):
            write_log(f'Loading information from {data_file}...')
            with open(data_file, 'r') as cinfo:
                customer_info.set_full_attributes(yaml.safe_load(cinfo)['customer_data'])
        else:
            write_log('Not information found for this ticket')


class InteractiveWindow:
    """
    A class that create an interactive experience
    """
    class LogfileViewer:
        """
        A class to generate different logviewer windows
        """

        def __init__(self, filename, starting_line=None):
            """

            """
            self.filename = filename
            self.loader = lazy_loader.LazyTextLoader(filename, lines_per_chunk=500)
            self.current_chunk_index = 0
            self.scroll_threshold = 100  # Cargar nuevo chunk cuando falten 100 líneas

            self.TTkWindow_logviewer = ttk.TTkWindow(pos=(40, 1), size=(120, 32),
                                                     title=ttk.TTkString("Log Viewer", ttk.TTkColor.ITALIC),
                                                     border=True,
                                                     layout=ttk.TTkGridLayout(),
                                                     flags=ttk.TTkK.WindowFlag.WindowMinMaxButtonsHint)

            self.root_logviewer = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
                "eJyFU0tP3DAQznazG7bbh1oor4IU9cSJPq59HKC0iABFZVtOFfImhrFI7FVis2wlpB4XaY7uX+nv69gJ1aoXYkWeGc9Mvm/85Vf4+0878M+13cBQT0bc4qPB4OKbePlR" +
                "pabgUluMLnlZCSUtdt5svt58ZbGtjbCupJPmrKosPqCabSU1E5KXFrsjVrKi8inhISuo6/0DOjsRMlNji3NHqhLatfxhN5IwuccxPBY/uXdHyTrH3oGQ8YnINNgkoGLy" +
                "drk4B+3c3gG7ag73gqDlzinQnNeR6LuoxDDndorRjmRkZc4cKJUPxMhiQLSOWJYJee4/GtSLY3efTZQh1j2i1NgGu3ltESGIYA1610TiM1cF1+WkKSfc2lY4l4LIs5I7" +
                "bj4d56jTp9JNwdVtQB8XbyOnuTo/Ezm/FHxMg4OHDkuLcMBjZxXJGocnSQBP6Z33zGCh3p5NYXEKS7AMK3WNXxyewxp2t1SZUbspdgZC0xBg2cD6DHaIa8gXySpBhhe3" +
                "SPuEa8Cv9E4m9D+wKzPBO/CKZPVOvNjfJ5HEh6YYeogLM258rFmp3Z0kLex95SyLv8h8Ym/ohk2uRexy7dRguyQZkRLaqcrdHpFfjZh0dRHFGtswgxGJ2Gyxkihid6i0" +
                "VkWty5yfaX9Ht0SXfKahDHman12ejmmK45KNrIcduhmQLE6aaEz2NvD0gjUy8w7J7MZUDDulF+Ns+/n/2vMrN2R3g7sY7nhn7wYSV24qeEsTfEfv+6QFHzwTg/1USclT" +
                "9+NU1Nps/gU+ZE//"))

            self.TTkMenuBarButton: ttk.TTkMenuBarButton = self.root_logviewer.getWidgetByName('menuButton_lfv_exit')
            self.TTkFrame_logfileviewer: ttk.TTkFrame = self.root_logviewer.getWidgetByName('TTkFrame_logfileviewer')
            self.TTkTextEdit_logfileviewer: ttk.TTkTextEdit = self.root_logviewer.getWidgetByName('TTkTextEdit_logfileviewer')
            self.TTkWindow_logviewer.addWidget(self.TTkFrame_logfileviewer)
            self.TTkMenuBarButton_lfv_wordwrap: ttk.TTkMenuBarButton = self.root_logviewer.getWidgetByName('menuButton_lfv_wordwrap')
            self._logview_resize()
            self.TTkTextEdit_logfileviewer.setText("")
            self.TTkWindow_logviewer.setTitle(f'Log Viewer -- {self.filename}')

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
            # Cargar primer chunk
            self._load_current_chunk()
                    # Conectar evento de scroll
            self.TTkTextEdit_logfileviewer._verticalScrollBar.valueChanged.connect(self._on_scroll)
            self.TTkMenuBarButton.menuButtonClicked.connect(lambda: self.TTkWindow_logviewer.setVisible(False))
            self.TTkMenuBarButton_lfv_wordwrap.menuButtonClicked.connect(_wordwrap)

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

        def _load_current_chunk(self):
            """Carga el chunk actual en el widget"""
            try:
                # Guardar posición del scroll
                scroll_bar = self.TTkTextEdit_logfileviewer._verticalScrollBar
                current_scroll_value = scroll_bar.value()
                max_scroll_before = scroll_bar.maximum()

                # Obtener chunk
                lines, line_start = self.loader.get_chunk(self.current_chunk_index)

                # Configurar números de línea
                first_line_num = self.current_chunk_index * self.loader.lines_per_chunk + 1
                self.TTkTextEdit_logfileviewer.setLineNumber(first_line_num)

                # Desconectar evento de scroll
                try:
                    scroll_bar.valueChanged.disconnect(self._on_scroll)
                except:
                    pass

                # Limpiar y actualizar contenido
                self.TTkTextEdit_logfileviewer.clear()
                for each_line in lines:
                    ttkstr = ttk.TTkString(each_line.strip('\n'))
                    self.TTkTextEdit_logfileviewer.append(HighlightCode.highlight(ttkstr))

                # Restaurar posición del scroll
                if max_scroll_before > 0 and lines:
                    scroll_ratio = current_scroll_value / max_scroll_before
                    new_max = scroll_bar.maximum()
                    new_value = int(scroll_ratio * new_max)
                    scroll_bar.setValue(max(0, min(new_value, new_max)))

                # Reconectar evento de scroll
                scroll_bar.valueChanged.connect(self._on_scroll)

                # Pre-cargar chunks adyacentes
                self.loader.preload_chunks(self.current_chunk_index)

            except Exception as e:
                write_log(f"{Icons.ERROR} Error en _load_current_chunk: {str(e)}", level="ERROR")

        def _on_scroll(self, value):
            """Maneja el evento de scroll de forma segura"""
            try:
                # Evitar procesamiento si estamos en medio de una carga
                scroll_bar = self.TTkTextEdit_logfileviewer._verticalScrollBar

                # Obtener rango del scroll
                min_val = scroll_bar.minimum()
                max_val = scroll_bar.maximum()

                if max_val <= min_val:
                    return

                # Calcular porcentaje de scroll
                percentage = (value - min_val) / (max_val - min_val)

                # Umbral para carga anticipada (80% del scroll)
                load_threshold = 0.8

                # Cargar siguiente chunk si estamos cerca del final
                if percentage >= load_threshold:
                    if (self.current_chunk_index + 1 < len(self.loader.chunk_boundaries) and
                            self._can_load_next_chunk()):
                        self._load_next_chunk()

                # Cargar chunk anterior si estamos cerca del inicio
                elif percentage <= 0.2 and self.current_chunk_index > 0:
                    if self._can_load_previous_chunk():
                        self._load_previous_chunk()

            except Exception as e:
                write_log(f"{Icons.ERROR} Error en _on_scroll: {str(e)}", level="ERROR")

        def _can_load_next_chunk(self):
            """Verifica si podemos cargar el siguiente chunk"""
            # Evitar carga si ya estamos cargando
            return not hasattr(self, '_loading') or not self._loading

        def _can_load_previous_chunk(self):
            """Verifica si podemos cargar el chunk anterior"""
            return not hasattr(self, '_loading') or not self._loading

        def _load_next_chunk(self):
            """Carga el siguiente chunk"""
            if self.current_chunk_index + 1 < len(self.loader.chunk_boundaries):
                self._loading = True
                self.current_chunk_index += 1
                self._load_current_chunk()
                self._loading = False

        def _load_previous_chunk(self):
            """Carga el chunk anterior"""
            if self.current_chunk_index > 0:
                self._loading = True
                self.current_chunk_index -= 1
                self._load_current_chunk()
                self._loading = False

#=======================

    def __init__(self):
        """

        """
        self.root = None
        self.filepath = None
        self.TTkWindow_logging = None
        self.TTkWindow_customer_info = None
        self.filename = None
        self.customer = None
        self.ticket = None
        self.generated_files = {}
        self.current_qv_page = 0
        self.filesize = 0
        self.flow_list_manager = None
        self.tx_list_manager = None

    def check_generated_files(self):
        """
        This will check Actual folder where UML diagrams should exist, and will load references that exist
        :return:
        """

        app_path = os.path.dirname(os.path.abspath(__file__))
        app_path = f'{app_path}/{data_dir}/{self.customer}/{self.ticket}'
        pattern = re.compile(r'([A-Za-z0-9-]*)_page_[0-9]*.puml')

        customer_info.set_attribute('ticket', self.ticket)
        customer_info.set_attribute('customer', self.customer)
        customer_info.set_attribute('data_dir_path', app_path)

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
            _clear_components()
            self.filename = filepath
            self.selected_id_for_special_blocks = None
            try:
                self.filepath = os.path.dirname(filepath)
                filepath = os.path.basename(filepath)
                self.filesize = os.path.getsize(self.filename)
                #write_log(f'Setting up last path visited to file picker...{self.filepath}')
                TTkFileButtonPicker.setPath(self.filepath)
                TTkLabel_file_size.setText(ttk.TTkString(_filesize_str(self.filesize)))
                TTkButton_start_analysis.setEnabled(True)
                TTkLabel_analysis_status.setText("")
                TTkLabel_Flows.setText("")
                TTkLabel_Parties.setText("")
                TTkLabel_Transactions.setText("")
                TTkButton_viewfile.setEnabled(True)

                self.TTkWindow_customer_info.setTitle(f'Logs tracer - {filepath}')
                customer_info.set_attribute('filename', filepath)
                customer_info.set_attribute('log_path_dir', self.filepath)

                write_log('Checking for existing diagrams...')
                self.check_generated_files()
            except:
                write_log(f"Unable to open file {self.filename}")
                self.filesize = 0
                self.filepath=""
                filepath=""
                TTkLabel_file_size.setText("")
                TTkButton_start_analysis.setEnabled(False)
                TTkLabel_analysis_status.setText("")
                TTkLabel_Flows.setText("")
                TTkLabel_Parties.setText("")
                TTkLabel_Transactions.setText("")
                TTkButton_viewfile.setEnabled(False)



        def _remember_last_path():
            # if not self.filepath:
            #     self.filepath = TTkFileButtonPicker.path()
            #     TTkFileButtonPicker.setPath(self.filepath)
            #     write_log(f'Saving last path...({self.filepath})')
            # else:
            #     # if self.filepath and self.filepath != TTkFileButtonPicker.path():
            #     #     self.filepath = os.path.dirname(TTkFileButtonPicker.path())
            #     # else:

            if self.filepath:
                write_log(f'Setting up last path visited to file picker...{self.filepath}')
                TTkFileButtonPicker.setPath(self.filepath)
                customer_info.set_attribute('last_path_used', self.filepath)

        def _fill_tickets(customer):
            """
            Will fill tickets list if there're on given folder path
            :param app_path:
            :return:
            """
            self.customer = customer
            TTkButton_new_ticket.setEnabled(True)
            app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}/{customer}"

            customer_info.set_attribute('customer', self.customer)


            ticket_list = _check_folders(app_path)

            if ticket_list:
                TTkComboBox_ticket.clear()
                TTkComboBox_ticket.addItems(ticket_list)

        def _check_folders(app_path=None):
            """

            :return:
            """
            if not app_path:
                app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"

            if not os.path.exists(app_path):
                write_log(f"Creating data directory {app_path}")
                os.makedirs(app_path)

            subdirs = [
                item for item in os.listdir(app_path)
                if os.path.isdir(os.path.join(app_path, item))
            ]

            return subdirs

        def _enable_file_select(ticket):
            """
            Enable button for file selection. This is done Only if a ticket has been selected...
            :return:
            """
            if ticket:
                self.ticket = ticket
                TTkFileButtonPicker.setEnabled(True)

            customer_info.set_attribute('ticket', self.ticket)
            customer_info.set_attribute('customer', self.customer)
            customer_info.set_attribute('data_dir_path', f"{app_path}/{self.customer}/{self.ticket}")

            customer_info.load_info()

            if customer_info.get_attribute('log_path_dir'):
                self.filepath = customer_info.get_attribute('log_path_dir')
                _remember_last_path()

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
            for each_item in TTkList_flow.items().copy():
                TTkList_flow.removeItem(each_item)

            for each_item in TTkList_transaction.items().copy():
                TTkList_transaction.removeItem(each_item)

            self.clear_tree_party()
            self.clear_spb_tree()
            _clear_spb_details_pane()
            _clear_quickview_pane()

        def _clear_quickview_pane():
            """
            Clear quick view pane
            :return:
            """
            schedule_ui_update('TTkTextEdit_quickview','setText','')


        def _clear_labels():
            """
            Clear all label counts
            :return:
            """
            schedule_ui_update('TTkLabel_Transactions', 'setText','')
            schedule_ui_update('TTkLabel_Flows','setText','')
            schedule_ui_update('TTkLabel_Parties','setText','')

        def _clear_spb_details_pane():
            """
            Clears Special Blocks pane details
            :return:
            """
            schedule_ui_update('TTkTextEdit_specialblocks','setText','')
            schedule_ui_update('TTkTextEdit_specialblocks','setLineNumberStarting',0)

        def _start_analysis():
            """

            :return:
            """
            global file_to_analyse
            TTkButton_start_analysis.setEnabled(False)
            schedule_ui_update('TTkLabel_analysis_stat','setVisible',True)
            schedule_ui_update('TTkLabel_analysis_stat', "setText", "Working...")

            schedule_ui_update('TTkLabel_Transactions', 'setText',f"{Icons.CLOCK}...")
            schedule_ui_update('TTkLabel_Flows','setText',f"{Icons.CLOCK}...")
            schedule_ui_update('TTkLabel_Parties','setText',f"{Icons.CLOCK}...")

            def _party_role_apply():
                """

                :return:
                """
                write_log("Check roles!!")
                pass

            def _load_party_tree():
                """Carga el árbol de parties (mantener como está)"""
                party_headers = {
                    'Party X.500 name': 70,
                    'Role': 15
                }
                party_roles = ['party', 'notary', 'log_owner', 'notary/log_owner']
                try:
                    schedule_ui_update('TTkTree_party', 'setHeaderLabels', list(party_headers.keys()))
                    write_log('Setting up parties...','INFO')
                    # Set column width
                    for pos, header in enumerate(party_headers.keys()):
                        schedule_ui_update('TTkTree_party', 'setColumnWidth', pos, party_headers[header])

                    for each_party in FileManagement.get_all_unique_results('Party'):
                        if each_party.get_corda_role():
                            role = each_party.get_corda_role()
                            idx = party_roles.index(role)
                            role = ttk.TTkComboBox(size=(17,1), list=party_roles, index=idx)
                        else:
                            role = ttk.TTkComboBox(size=(17,1), list=party_roles, index=0)

                        tree_element = ttk.TTkTreeWidgetItem([each_party.name, role])
                        schedule_ui_update('TTkTree_party', 'addTopLevelItem', tree_element)

                        if each_party.has_alternate_names():
                            for each_alternate in each_party.get_alternate_names():
                                child = ttk.TTkTreeWidgetItem([each_alternate, role])
                                tree_element.addChild(child)

                    # Party List
                    if file_to_analyse.get_all_unique_results('Party'):
                        schedule_ui_update('TTkLabel_Parties', 'setText', f"{len(file_to_analyse.get_all_unique_results('Party'))}")
                    else:
                        schedule_ui_update('TTkLabel_Parties', 'setText', '0')

                    apply_button:ttk.TTkButton = root_window_party.getWidgetByName('TTkButton_apply')
                    if apply_button:
                        apply_button.clicked.connect(lambda: _party_role_apply)
                    else:
                        write_log(f"NO CONNECTED! {apply_button}")

                except BaseException as be:
                    write_log(f'Unable to process parties due to {be}', level='ERROR')


            def _analysis_process():
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


                ##
                ## Start filling components with data
                if not file_to_analyse.get_all_unique_results():
                    write_log('I was not able to process this file, it was not recognized as Corda log file', level='WARN')
                    _clear_labels()
                    return

                if not file_to_analyse.get_all_unique_results('Party'):
                    write_log('I was not able to process this file, it was not recognized as Corda log file', level='WARN')
                    _clear_labels()
                    return


                results = collect_refIds.classify_results(FileManagement.get_all_unique_results('Flows&Transactions'))
                if not results:
                    write_log('...')
                    _clear_labels()
                    return

                # Preparar datos para carga perezosa (sin cargar inmediatamente)
                flow_data = []
                tx_data = []

                # Flow list - solo recolectar datos
                if 'FLOW' in results:
                    write_log('Flows: Preparing data...')
                    for index, each_flow in enumerate(results['FLOW']):
                        sp_blk = file_to_analyse.special_blocks.get_reference(each_flow)
                        if sp_blk:
                            icn = ""
                            for each_blk in sp_blk:
                                icon_config = Configs.get_config_for(f'BLOCK_COLLECTION.COLLECT.{each_blk}.ICON')
                                if icon_config:
                                    icn += f" {Icons.get(icon_config)}"
                            each_flow = f"{each_flow}{icn.lstrip()}"

                        flow_data.append(each_flow)

                        # Actualizar progreso
                        if index % 50 == 0:  # Cada 50 elementos
                            progress = f'{Icons.CLOCK} Flows: {(index * 100)/len(results["FLOW"]):.1f}%'
                            schedule_ui_update('TTkLabel_Flows', 'setText', progress)

                # Transaction list - solo recolectar datos
                if 'TRANSACTION' in results:
                    write_log('Transactions: Preparing data...')
                    for index, each_tx in enumerate(results['TRANSACTION']):
                        sp_blk = file_to_analyse.special_blocks.get_reference(each_tx)
                        if sp_blk:
                            icn = ""
                            for each_blk in sp_blk:
                                icon_config = Configs.get_config_for(f'BLOCK_COLLECTION.COLLECT.{each_blk}.ICON')
                                if icon_config:
                                    icn += f" {Icons.get(icon_config)}"
                            each_tx = f"{each_tx}{icn.lstrip()}"

                        tx_data.append(each_tx)

                        # Actualizar progreso
                        if index % 50 == 0:
                            progress = f'{Icons.CLOCK} Transactions: {(index * 100)/len(results["TRANSACTION"]):.1f}%'
                            schedule_ui_update('TTkLabel_Transactions', 'setText', progress)

                # Actualizar UI con datos preparados
                schedule_ui_update('TTkLabel_Flows', 'setText', str(len(flow_data)))
                schedule_ui_update('TTkLabel_Transactions', 'setText', str(len(tx_data)))

                # Cargar datos en listas perezosas (en el hilo principal)
                def load_lazy_lists():
                    # Cargar árbol de parties (menos crítico para carga perezosa)
                    _load_party_tree()
                    # Cargar datos en gestores perezosos
                    self.flow_list_manager.set_items(flow_data)
                    self.tx_list_manager.set_items(tx_data)

                # Programar carga en hilo principal
                schedule_callback(load_lazy_lists)

                process_callbacks()

                # # Flow list
                # if 'FLOW' in results:
                #     #TTkLabel_Flows.setText(f"{len(results['FLOW'])}")
                #     write_log('Flows: Checking for Special blocks related...')
                #     for index, each_flow in enumerate(results['FLOW']):
                #         sp_blk = file_to_analyse.special_blocks.get_reference(each_flow)
                #         fcompleted = f'{Icons.CLOCK}...{(index * 100)/ len(results["FLOW"]):.2f}%'
                #         if sp_blk:
                #             icn=""
                #             for each_blk in sp_blk:
                #                 icn += f" {Icons.get(Configs.get_config_for(f'BLOCK_COLLECTION.COLLECT.{each_blk}.ICON'))}"
                #             each_flow = ttk.TTkString(f"{each_flow}{icn.lstrip()}")
                #
                #         schedule_ui_update('TTkList_flow', 'addItem', each_flow)
                #         schedule_ui_update('TTkLabel_Flows', 'setText', fcompleted)
                #
                #     schedule_ui_update('TTkLabel_Flows','setText',f"{len(results['FLOW'])}")
                #     # list_flow.addItem(each_flow)
                # else:
                #     schedule_ui_update('TTkLabel_Flows','setText','0')
                #
                #
                # # Transaction list
                # if 'TRANSACTION' in results:
                #     # TTkLabel_Transactions.setText(f"{len(results['TRANSACTION'])}")
                #     write_log('Transactions: Checking for Special blocks related...')
                #     for index, each_tx in enumerate(results['TRANSACTION']):
                #         fcompleted = f'{Icons.CLOCK}...{(index * 100)/ len(results["TRANSACTION"]):.2f}%'
                #         sp_blk = file_to_analyse.special_blocks.get_reference(each_tx)
                #         if sp_blk:
                #             icn=""
                #             for each_blk in sp_blk:
                #                 icn += f"{Icons.get(Configs.get_config_for(f'BLOCK_COLLECTION.COLLECT.{each_blk}.ICON'))}"
                #             each_tx = ttk.TTkString(f"{each_tx}{icn.lstrip()}")
                #         schedule_ui_update('TTkList_transaction', 'addItem', each_tx)
                #         schedule_ui_update('TTkLabel_Transactions', 'setText', fcompleted)
                #         # list_transactions.addItem(each_tx)
                #     schedule_ui_update('TTkLabel_Transactions', 'setText',f"{len(results['TRANSACTION'])}")
                # else:
                #     schedule_ui_update('TTkLabel_Transactions', 'setText','0')
                #
                # party_headers = {
                #     'Party X.500 name': 70,
                #     'Role': 15
                # }
                # try:
                #     schedule_ui_update('TTkTree_party', 'setHeaderLabels', party_headers)
                #     # self.tree_party.setHeaderLabels(party_headers)
                #     # Set column width
                #     for pos,header in enumerate(party_headers.keys()):
                #         schedule_ui_update('TTkTree_party', 'setColumnWidth',pos, party_headers[header] )
                #         # self.tree_party.setColumnWidth(pos, party_headers[header])
                #
                #     for each_party in FileManagement.get_all_unique_results('Party'):
                #         if each_party.get_corda_role():
                #             role = each_party.get_corda_role()
                #         else:
                #             role = 'party'
                #         tree_element = ttk.TTkTreeWidgetItem([each_party.name, role])
                #         schedule_ui_update('TTkTree_party', 'addTopLevelItem',tree_element )
                #         # self.tree_party.addTopLevelItem(tree_element)
                #         if each_party.has_alternate_names():
                #             for each_alternate in each_party.get_alternate_names():
                #                 child = ttk.TTkTreeWidgetItem([each_alternate, role])
                #                 tree_element.addChild(child)
                #
                #     # Party List
                #     if file_to_analyse.get_all_unique_results('Party'):
                #         schedule_ui_update('TTkLabel_Parties','setText',f"{len(file_to_analyse.get_all_unique_results('Party'))}")
                #     else:
                #         schedule_ui_update('TTkLabel_Parties','setText','0')
                #
                # except BaseException as be:
                #     write_log(f'Unable to process parties due to {be}', level='ERROR')

            # Configs.load_config()

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

            file_to_analyse.special_blocks = BlockExtractor(file_to_analyse, Configs.config)
            file_to_analyse.special_blocks.extract()
            file_to_analyse.special_blocks.summary()
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

            # Set Error Log analysis -- TODO: need to review for optimizations
            # collect_errors = ErrorAnalisys(file_to_analyse, Configs)
            # collect_errors.set_file(file_to_analyse)
            # collect_errors.set_element_type(CordaObject.Type.ERROR_ANALYSIS)

            # Pre-analyse the file_to_analyse to figure out how to read it, if file_to_analyse is bigger than
            # blocksize then file_to_analyse will be
            # Divided by chunks and will be created a thread for each one of them to read it
            file_to_analyse.pre_analysis() # Calculate on fly proper chunk sizes to accommodate lines correctly
            #
            # Add proper methods to handle each collection
            #
            file_to_analyse.add_process_to_execute(collect_parties)
            file_to_analyse.add_process_to_execute(collect_refIds)
            # file_to_analyse.add_process_to_execute(collect_errors)

            file_to_analyse.start_stop_watch('Main-search', True)
            analysis_thread = threading.Thread(
                target=_analysis_process,
                name="File Analysis",
                daemon=True
            )
            analysis_thread.start()
            write_log(f'Started analysis for: {file_to_analyse.filename}')

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

        def _run_trace_analysis(ref_id, file_to_analyse, co):
            """
            Función que ejecuta el análisis en un hilo separado
            """
            try:

                ref_id = Icons.remove_unicode_symbols(ref_id)
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
             Método que lanza el trace en un hilo separado
            """
            # Mostrar mensaje de inicio en UI



            write_log(f"Starting trace analysis for {ref_id}...")

            # Crear y lanzar el hilo
            analysis_thread = threading.Thread(
                target=_run_trace_analysis,
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

            if not file_to_analyse.get_party_role('log_owner'):
                write_log("Unable to perform a tracing, 'log_owner' role is not being assigned...", level="WARN")
                write_log("You will need to manually setup it up, otherwise will not be possible to trace any item...", level="WARN")
                self.tk_popup_window(origen=TTkButton_flow_trace, message="Unable to continue role:\n 'log_owner' hasn't been assigned.")
                return

            if source == 'flow':
                ref_id = ttk.TTkString.toAscii(TTkList_flow.selectedLabels()[0])
                TTkButton_flow_trace.setEnabled(False)

            if source == 'txn':
                ref_id = ttk.TTkString.toAscii(TTkList_transaction.selectedLabels()[0])
                TTkButton_tx_trace.setEnabled(False)

            if not source:
                return

            sref_id = Icons.remove_unicode_symbols(ref_id)
            co = CordaObject.get_object(sref_id)

            if not ref_id or not co:
                write_log("Reference ID not found unable to trace it, please try another", level='WARN')
                return

            _start_trace(sref_id, file_to_analyse, co)

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


        def _quick_view_check(type, selected_item):
            """

            :param selected_item: a list of selected ttkstrings...
            :return:
            """

            label=Icons.remove_unicode_symbols(selected_item[0].toAscii())

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

        def _quick_view_check_pages(ref_id):
            """
            This method will prepare quick view paginated if it is required
            :param ref_id:
            :return:
            """
            sref_id = ref_id[0].toAscii()

            if sref_id in self.generated_files:
                if  len(self.generated_files[sref_id]) > 1:
                    np =f'Page: 1/{len(self.generated_files[sref_id])}'
                    TTkmenuButton_qv_npage.setEnabled(True)
                    TTkmenuButton_qv_ppage.setEnabled(False)
                    TTkmenuButton_qv_pages.setText(np)
                else:
                    np = 'Page: 1/1'
                    TTkmenuButton_qv_npage.setEnabled(False)
                    TTkmenuButton_qv_ppage.setEnabled(False)
                    TTkmenuButton_qv_pages.setText(np)

            _quick_view(ref_id)

        def _quick_view_browse(ref_id, direction):
            """
            Will move pages
            :param ref_id: reference Id to view
            :param direction: forward or backward
            :return:
            """

        def _quick_view(ref_id, page=0):
            """
            Show Ascii version of Sequence Diagram
            :return:
            """

            ref_id = Icons.remove_unicode_symbols(ref_id[0].toAscii())

            if ref_id in self.generated_files:
                filename = self.generated_files[ref_id][page]
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

            logfile_viewer = InteractiveWindow.LogfileViewer(self.filename)

            # logfile_viewer.loadfile(self.filename)

            logfile_viewer.TTkWindow_logviewer.setParent(self.root)

            root.layout().addWidget(logfile_viewer.TTkWindow_logviewer)

        def _sb_view_details_for(specialblocks_list, reference_id):
            """
            Show content of selected block
            :param selected_index: selected index from
            :return:
            """

            selected_index = specialblocks_list.selectedItems()

            if not selected_index:
                return

            selected_item = selected_index[0].data(0).toAscii()
            block_type = selected_index[0]._parent.data(0) # Dirty and not good way to get this, but there're no methods that can help me...
            if ':' in selected_item:
                idx, block_name = selected_item.split(':')
                idx = int(idx)
                _special_block_fill_details(idx,reference_id,block_type)

        def _special_block_fill_details(idx, reference_id, block_type):
            """
            Fill content of block
            :param idx: index of content at the blocks
            :param type:
            :return:
            """
            global file_to_analyse

            self.TTkTextEdit_specialblocks.setText("")
            block_type = block_type.toAscii()
            content = file_to_analyse.special_blocks.get_reference(reference_id=reference_id, block_type=block_type)

            if not content:
                write_log(f"Unable to find any {block_type} for id {reference_id}...", level="WARN")
                return

            if content and idx < len(content) :
                self.TTkTextEdit_specialblocks.setLineNumberStarting(content[idx].line_number-1)

                for each_line in content[idx].get_content():
                    self.TTkTextEdit_specialblocks.append(HighlightCode.highlight(ttk.TTkString(each_line.rstrip())))
            else:
                write_log(f"Invalid index for the content!, reference id being used: {reference_id}", level="ERROR")
                pass

        def _special_block_resize():
            """

            :return:
            """
            tree_parent_size = self.TTkTree_specialblocks.parentWidget().size()
            details_parent_size = self.TTkTextEdit_specialblocks.parentWidget().size()

            self.TTkTree_specialblocks.resize(tree_parent_size[0]-2, tree_parent_size[1]-3)
            self.TTkTextEdit_specialblocks.resize(details_parent_size[0]-2, details_parent_size[1]-3)

        def _special_block_details_wordwrap():
            """

            :return:
            """
            if self.TTkmenuButton_sp_wordwrap.isChecked():
                self.TTkTextEdit_specialblocks.setLineWrapMode(ttk.TTkK.WidgetWidth)
                self.TTkmenuButton_sp_wordwrap.clearFocus()
            else:
                self.TTkTextEdit_specialblocks.setLineWrapMode(ttk.TTkK.NoWrap)
                self.TTkTextEdit_specialblocks.clearFocus()

        def _special_block_details_exit():
            """

            :return:
            """
            self.TTkWindow_specialblocks.setVisible(False)
            self.TTkTextEdit_specialblocks.setText("")
            self.clear_spb_tree()

        @pyTTkSlot(ttk.TTkList)
        def _special_block_details(reference_list):
            """
            Special block details
            :return:
            """
            global file_to_analyse

            reference_id = reference_list.selectedLabels()

            if not reference_id:
                return

            self.clear_spb_tree()
            _clear_spb_details_pane()
            reference_id = reference_id[0].toAscii()
            reference_id = Icons.remove_unicode_symbols(reference_id)
            results = file_to_analyse.special_blocks.get_reference(reference_id)
            self.TTkWindow_specialblocks.setTitle(f'Details for {reference_id}')
            self.specialblocks_selected_reference_id = reference_id
            self.specialblocks_selected_item = self.TTkTree_specialblocks.selectedItems()
            if results:
                self.TTkTree_specialblocks.setHeaderLabels(labels=['Type'])
                self.TTkTree_specialblocks.setColumnWidth(0, 47)
                for each_type in results:
                    tree_element = ttk.TTkTreeWidgetItem([each_type])
                    self.TTkTree_specialblocks.addTopLevelItem(tree_element)
                    for idx,each_item in enumerate(results[each_type]):
                        child = ttk.TTkTreeWidgetItem([f'{idx:0>3}:{each_item.__str__()}'])
                        tree_element.addChild(child)

                # ✅ GUARDAR EL HANDLER ANTERIOR PARA DESCONECTARLO
                if hasattr(self, '_previous_tree_handler'):
                    # Desconectar el handler anterior
                    try:
                        self.TTkTree_specialblocks.itemClicked.disconnect(self._previous_tree_handler)
                        # write_log(f"DEBUG: Desconectado handler anterior")
                    except (TypeError, RuntimeError):
                        # write_log(f"DEBUG: No se pudo desconectar handler anterior")
                        pass

                # ✅ CREAR NUEVO HANDLER
                def create_handler(ref_id):
                    def handler():
                        # write_log(f"DEBUG: Handler ejecutado con ref_id: {ref_id}")
                        _sb_view_details_for(self.TTkTree_specialblocks, ref_id)
                    return handler

                new_handler = create_handler(reference_id)

                # ✅ CONECTAR NUEVO HANDLER
                self.TTkTree_specialblocks.itemClicked.connect(new_handler)

                # ✅ GUARDAR PARA DESCONEXIÓN POSTERIOR
                self._previous_tree_handler = new_handler

                # write_log(f"DEBUG: Conectado nuevo handler. Total conexiones: {len(self.TTkTree_specialblocks.itemClicked._connected_slots)}")

            self.TTkWindow_specialblocks.setVisible(True)

        @pyTTkSlot()
        def _add_new_data(type=None):
            """
            Add new customer
            :param type: Customer or ticket
            :return:
            """
            self.TTkWindow_customer_info.setEnabled(False)
            TTkWindow_popup_new_data.setVisible(True)
            TTkLineEdit_popup_newcustomer_customer.setEnabled(True)
            TTkLineEdit_popup_newcustomer_customer.setText('')
            TTkLineEdit_popup_newcustomer_ticket.setText('')
            TTkWindow_popup_new_data.move(30,10)
            TTkWindow_popup_new_data.raiseWidget()
            # ttk.TTkHelper.overlay(TTkButton_new_customer, TTkWindow_popup_new_data, -2, -1)
            if type and type == 'ticket':
                if self.customer:
                    TTkLineEdit_popup_newcustomer_customer.setText(self.customer)
                else:
                    write_log('Please set proper customer name before adding a new ticket...', level="WARN")
                    TTkButton_new_customer.setEnabled(True)
                    TTkButton_new_ticket.setEnabled(True)
                    self.TTkWindow_customer_info.setEnabled(True)
                    TTkWindow_popup_new_data.setVisible(False)
                    return


                TTkLineEdit_popup_newcustomer_customer.setEnabled(False)

            TTkButton_new_customer.setEnabled(False)
            TTkButton_new_ticket.setEnabled(False)

        def _process_new_data():
            """
            Adding new data
            :return:
            """

            app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"

            self.customer = TTkLineEdit_popup_newcustomer_customer.text().toAscii()
            self.ticket = TTkLineEdit_popup_newcustomer_ticket.text().toAscii()
            if not self.customer:
                write_log('Please supply a valid customer name...')
                return

            if not self.ticket:
                write_log('Please supply a valid customer ticket...')
                return

            new_full_path = f'{app_path}/{self.customer}/{self.ticket}'

            if not os.path.exists(new_full_path):
                ticketPath = f'{app_path}/{self.customer}/{self.ticket}'
                customerPath = f'{app_path}/{self.customer}'
                if not os.path.exists(customerPath):
                    os.makedirs(customerPath)
                    TTkComboBox_customer.addItem(self.customer)
                    write_log(f'Adding new customer {self.customer}')
                if not os.path.exists(ticketPath):
                    os.makedirs(ticketPath)
                    TTkComboBox_ticket.addItem(self.ticket)
                    write_log(f'Adding new ticket {self.ticket} to {self.customer}')


            TTkComboBox_customer.setCurrentText(self.customer)
            TTkComboBox_ticket.setCurrentText(self.ticket)
            TTkButton_new_customer.setEnabled(True)
            TTkButton_new_ticket.setEnabled(True)
            TTkWindow_popup_new_data.setVisible(False)
            self.TTkWindow_customer_info.setEnabled(True)

        def _close_popup_new_data():
            """

            :return:
            """
            TTkWindow_popup_new_data.setVisible(False)
            TTkButton_new_customer.setEnabled(True)
            TTkButton_new_ticket.setEnabled(True)
            TTkButton_new_customer.clearFocus()
            self.TTkWindow_customer_info.setEnabled(True)

        def _exit_application():
            """
            Close all operations and exit
            :return:
            """

            """Inicia el cierre ordenado desde la UI"""
            if shutdown_event.is_set():
                return

                # return  # Ya se solicitó cierre

            customer_info.save_info()
            write_log("Exiting...", level="INFO")
            shutdown_event.set()
            root.quit()

        # Form definition; all these forms where created using ttkDesigner
        #
        #


        customer_info_widget = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJy9l+9vGjcYx0k5IIRAIKVp2rTSaXuTJRpL6aKtzX4oSdOuuyZDCmtVVRNyDje2ctyhO18TJlXaS5D88vZ6r7b9m3vsMw6khECkDHTCP87+fvz4eeyHP4w/aSEhPx+j" +
            "VW6wThtHvFCvn/xKv3rm2WELuyzimQ/YD6jnRjxVrTyqbEQ8yUIaiSEp20FBEPF5GLPruQxRF/sRT7eRj1qBfMU4QC2YdW4f+t5Qt+mdRny25gWUiSl/i1Ytw7qFuXFI" +
            "f8ey+sK6j3l2n7rmG9pkJLISMBhqP2F6TJioZvfRmer8OZGYEf3QoPrjlsxrGtAjB0ddntlzEZSaolj3PKdO2xFPwLJqqNmk7rEUTcRfzNOvUMcLYdVZWJIqhzztxCVY" +
            "EMmQByT7ERbxAnstzPyOGg7cLAr4rE2o0/SxWJt8nc/CTM99YQUxbpXkBlvySh2TBVHatZYwKVkJsgjPbbkWUo5/7nTJUpfcJcvknnhzJv5iskIe8PSO5zfB8l2eqlMG" +
            "yybLIXk4QEvMGHLbKgMk+QxmOId7hY6wMwSnWiTcLSEi4bKiVLKyADdzGRw36vhMmG83DBjYx38KbrPrOR64hbHybqMFXdsOPXalb1kzIU/64BKwq0nbc8RvBupBG7nQ" +
            "yTPQpsphvJpqH3Ouj/nlIw2anAKUfANbTO0TzEzzaUSeKDqyBVLkO7D+9/D8AON/7Gvz22LbqIN3QsY8tyYG+9psozsVWEqBlQViyVoAsOQYsPwhdrDNTGS+p2Iz17tg" +
            "T4LtE+HIUY9nZAVcuseNGoIw4DMVcOhd1JZBxXMCxHxGkeMdQzvUGIRwxPPbjmOKvsBcXfsC3tu2bdxm5r7XxDKw5DhVu8wKIjDiReq1L+umRsCQzxrIRU4noIE2wOyw" +
            "AYqXGKCnDFA4FNOY23qa9S456JFfepdAjXKLx0o8aRWUeD52i/wVbpGv+8gNkC1sGUzmGqP0v9b6xSn1nzsQAWb8ub5+VevPT6lfA9tTHFxLv9jXb6hZFEVJU2RiisR4" +
            "Cnie8IWVd4+/3apubWxVNze3JkW4oxEGN1JzFP4vjoLmkBuqAYo3DPC2D1AeCEvinTbgVmYdhbGi92MuxkgPYUBx0CWMQxgPUdgbH4VvBw/DQeX3jhiuhIs3KHz/gjA7" +
            "9wCtX7hB/cVz/Q8Un8bHt9Rds9L6DJS6uXG62dcwun/6jxfnOZl8tY68He8sGtz7fmPDVnexQpnXN7pCSV2Ocm8wO5K5xuxekzJ1EeXEZW/K+7wSWQbPv3QDDAd3zXOo" +
            "3RG39sgsBCRUFjLFebap6O9qQ6ZG0X96nqVEajntObaog1dsQiMQ2Wms/1Drp2P95BX6yUqlItRLQ0EMz4RhvHTuUy4+vbiZaxc3szTOrxYOwK36qZnkmti1y8MYTOZO" +
            "GiI5DLEwDiIvIOLcayKEvwY3RTv1EMD8RYBpXJr83SP/WAb510pe119HnXwt+MfTwGe0z7hulYazoPQVaaCxJwdPnPssaZ/t518iHWM6brJK/vPJL56JfRZ/2oTCkOds" +
            "z3WxuoHBfJX/AEJeUbw="))

        root_window_logging = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyFkltv0zAUgFPSNu0KjLFxG0OKeOpTubxzETBAZB0VK0wITZOXWDkWiV3FNqxIk3gs0nk0/5fjJEyTeCBW5HP3+Xz8s/t7Owzq78yNsWuWC+7w6nz+9aN48EqltuTS" +
            "OIy+8UoLJR32Hk8eTR46DI0Vzqf00oJp7fAy5bxU0jAheeWwv2AVK3Ud0t1nJVVdm5LvUMhMfXc4mCktjC955MbJpSTk2D0QP3itHifbHIdTIeNDkRlwSUDJpL3lIgfj" +
            "1eGUnbbOd0HQ8X4ytP7GEn0SWpwU3K0w2pWMpMyLc6WKuVg4DAhrxrJMyLw+NGgWx/4eWypL1ENCamWL/aKRCAgi2IHhGUG84arkplq26dS3cRoHKYgiq7hnq8PrSi25" +
            "TxzDCDfOTceFynPfBVzxfXSSdQ7rXjpKRhw2kgCu079ZU8FWs91Ywc0V3ILbcMdHhpRFi8Nd2MH+C1VlNIMV9ubC0AXgtVmlchpHXHKtWc79uJqz49cFy7W/sWBg4d4F" +
            "OIgbpi9JRExw/y/KiPqe81OzmwlzDrN5wfgPTtDifE76/8XB0R69n3jflidE8Au3LqjxgWGV8ZX9A/jAWRa/l8WSotamtjAi9rFuZTGs6J4pJkxV4feIdL1g0iUdjMjW" +
            "ypZZeEKtPKX/WdKB57XJ4ihVUvLUP05NE7STP/YXD1c="))

        root_window_flow = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyNk1tv0zAUx1P1kra7lNvYhSEqJKRKm8rGR9i6DQidNi1sT2gyidmxlsYlcXZBmrTHTvILknnmgS/IR+DYTkbRGCNRlONjn+Pf//j4svJtoeqY50J1ZEWcD6mS075/" +
            "/J697PEgG9BYKOme0CRlPFay+qq72l1RsiwypnRINYhImio5iTHrPBaExTRRsjYkCRmkZkllmwww670+zh2wOOSnh58ifopB9R2eMqETf1Adr+KVqKzssS/UDPveMyob" +
            "fRa3D1goQHmObOrRa8qOQOhho0/O8sm3jlPS8+jI563H3Wcp+xhRNZLuRkzQCrXpcx75bKikg+J2SBiy+Mhs6tiXyto7cs4z1N5AYbmdyVpkLZQFLixC4wJFbFE+oCI5" +
            "z8ORW6hU1gNgUZhQrc0sl3XMtJnoWui4DkzIqcJjCqJgKkeg0NLWqrdI4b7nwAP8HhpB8Mj+ZkbweASzMAfz49jwBBZlbY0nIR7Claz6TKB2mMvg6RgytG0E5kdSeI4Z" +
            "7OyLAmxyHOwG14o3/59cJfsaLlgawbKsbpqj/ztQ15vNgWzFXF17lgo1zqUd4/Uy+Q3XsjdzJ5ec3qMRDXTTtfs8pMoryXov7uUDJ5PlBFNjd5UDHum/i+N0SGK90kVf" +
            "bmckgx7us4HfpleCLXRZat0xa5kQ2NYF9+y1y7b+YUjxpkRpLmFaF9RIaHplLaGBEsq3Sqj49Ezfyl6RZGkkG+tAg2Pd4Hjurhlgq1/dwghvCrLWbzKRkIBeH3ZBNGmJ" +
            "mv8igm3Z/Pn964+2b1PgSe9cwe7du8/9WZfDzxkLjk8YLc524RqjZTFad2C0EOOyvavTtPdNnttZ6E0XyTI5EfA4th2S4t3Nur8Av1CkDQ=="))

        root_window_party = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyVlEtv00AQxx3sxElDCKVNW94V6iGn8DjxEIemKUWYoEo1LUJUxdhLZhXHG9lr2iBV4phIe1w+G1+H2bUTmkNbasvy7Mzu7O8/s/Yv6/cfy9DXqWwKi4+GRIobrtv/" +
            "SB93mJ8OSMSlsH+QOKEskqL4rPW09UQKk6dUqiVFP/SSRIoyrnkTewNcXhp6aCQ6bH3Qrptdj0YHNArY8RFG+QgX7LKEcpX0UDada06BCGuP/iR6+NW5Q0SlS6P1Axpw" +
            "kI4hFtToLaE94GpY6XonefCdYRRUHB15PPPY+zSh30Iix8Lejjy0AmW6jIUuHUphoLBdLwho1NObGtlNROm9N2Ip6q6gqKldarM4ILGciKJLOWaFtVSUwiyKUsGGe1A5" +
            "RWE7hA0Ij0d5StTCZSLKPtAwiInWm80vq/lNqOqC6+LlxYFaVhODQF1ZX5xVAouOAbfwWdLqYDl7NcawMoZVWIPbamYhuwncRZr7Y3igJMackkSm8PAMJjzK6D47DaSD" +
            "jcNMA5bH7bsxQXk5Wy13zKEVZmifnMalaMLeY8iAZR6nwozZsWqg6bNQvW0cJ0Mvkk5B2OjL7dRL4TmmfIHPS6cAr9CVEaqmtFPO8eRMGZdmriPs5xyppUqnSauOqUiL" +
            "SGqeS2q55ASbbW4GgcT6icoWEL+vzg423tYDPEWTc9jg9ZRo5R/RgAX0+2gOanEGtZBBlS+CgrYodXUShQSdCWxfCSAgIeHz/duYAVz/T4COTnIFgPqZngyH4XTnndnO" +
            "y9nO9Ut2rm2q1etb4EU9PMUXAJA0FVWfRRHx1X8lwQ8tbf0FhH2Pcg=="))

        root_window_transaction = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyNk91PE0EQwK/241pAikL5iDU2JiYkEPz4E2gB9SyBcMoTIevdymy47ta7PQomJDyWZF9M1mcf/Af9E5y9vTZNLGIvl5uPnZnfzE5vSj82y072u9brqiSv+lSred8/" +
            "/8hedkSQ9iiXWrkXNE6Y4FqV32y93nqlVVGmTJuQchCRJNFqDmPagkvCOI21qvRJTHpJdqS0T3qYdaGLvmPGQzE4/RKJAQZVD0TCpEl8ote9kveAqtIR+0Yztes9o6rW" +
            "Zbx1zEIJ2nPUjNHeUnYG0qi1LrnMne8dp2D8aMj91uJ+Ygn7HFE9VO4OJyiFRvSFiHzW18rB5g5IGDJ+lhV17ENV5QO5Ein2XsPGcjlVlchK2Ba40ITaNTaxR0WPyvgq" +
            "D0duqRNVDYBFYUxNb9lxVcVMu7GZhYlbh1nVGFlOZUx4QgIzi0TDQ4NSQAyoG2nHa1J45DnwGN/FrDFYsp/GEJaHsAKrsDaJD0+gqSrbIg7xMm5V2WcSZwCrKTydQIeW" +
            "jcD8SAzPMYP1vhgBLk0DzPkcrzDmW/lPvoJ9Mj7YGMIm7s1k59P52l4j57ODdM2VsESO57iYG6ZSjqa47TXupVTzRzSiWXyrK0KqvYKqdngnV5xUFWMxMLtXDERkvi7q" +
            "SZ9wc9JFWy6nJIUO1tnBd9crwB6aLLzZp+1USkOY49fHJtNAQMfoazn6nFc06DOIXrwTveTTS9zXmd8/v/9q+TbPxlDV2kCDc7P5uAhupuB/4PYOPHg3BSqIRDKCqo+h" +
            "Zi2U+y8o2Fflto3G2z64hcP7Cy9PTOPy9GvKgvMLRgd5/ea4/oKtX7+nfh3ncdM6NGlaNs/dJPRvE0lTNRsIzmm+oic63foDVDusZQ=="))

        root_window_quickview = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyFU91PE0EQv9prj1KRCKigkFx84gnEZz8SPvw6ClWqvKjNcrdhN1xvy+1uoSYkPJZkXkzWZ/9F/wRn965YTYi9XG5mdmfm95v59dL/se977ndhVsFXwz41cKfTOfnI" +
            "17dFrHs0UwaCAc0lF5mB2tO1jbUnBqpKc2NTanFKpDRwG3O2RKYIz2huoN4nOelJd8XfIz2sOt3Cs0OeJeLMwFRbSK5syS9mNboVVSn4B/wbdW43ekih0eJZeMgTxUzk" +
            "YTJ6byg/Zsq6jRY5Lw/feV7FnmOgPC8iwScu+VFKzQiCnYyglVizI0Ta4X0DHtJqkyTh2bFr6hUPhfouGQqNrBtIqbQ11NPCQkIsYMuscYEkXlPRoyoflumIWxkJUzHj" +
            "aZJTy81dhyms9Cq3U7B5q6wJc+NI91Tz+GTA6ZlhMyUOymat9RXHwO5GHpvDd96xYgvF596I3R+xB2yRLdmbleKh7BFbhvqmyBPcwQhqHa5wADD76+f3y/C9bRS6Tpqt" +
            "TPBgYQH/c7SI8NnjMeomYuzQc7WTcHUNfGUi+Ad7N8bVW6n8ywFr/pcDNHdRNOGe7h0h7CtYmHDDA0VyZXdkt/6BkiTcz9Ihkptu6VTx0N41Iw3VHGWFd6qxSO03QF/2" +
            "SWaiCgQYK21NNAQoar1JcifOqhJ9NKCWO+1Y7mOq8+6eVkpk3dNBt0+OqTQOsG8nYEWMoXBjfQO1ssVofGJVhgQC56DerrQkEupHAmv0XLt6jFNCljibmxvZTq4Rewsz" +
            "7ZwOuNAybLtodMV2seyNydlkcmMPcf6dSNn2JMelyezrbdJzu/Gihr/jnDKdaM2e4Sqf4/siqrCXbqQamiiAjMb2Hy2RnF77DRwciok="))

        root_window_popup_add_customer_ticket = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyVlN9PE0EQx69py7VFICAKCpoLMYaEWIHoAxh/QMUfnBUSqzwYJMfdhtlw3W3u9gRMSHykyfpgsr74wot/nU/8Cc7eL0At0TaXm5m92f18Z3b3c+nbz7IR/w7VtCyJ" +
            "gw5RcrDV2n1L7z7lbtQmTChpfiRBSDlTsjxfn6vPKlkUEVU6pez6ThgqeQlzGpwJhzISKNnXcQKnHcaflF47bZy11sSxDco8vqdkZZ2HVOgpN9W0PWQXiSy9oZ9I7N63" +
            "B4isNimzNqgnQNkGJqP3gtAdENqtNp39dHDVMAp6HAPpeBIx39GQbvtEHUlzhTloedpsce63aEdJA2WtO55H2U68qJH8iex75RzwCFVXUVJqR7LPTywUBCZMQvUQRTwn" +
            "vE1EcJCmI7dQoay4QH0vIFpb/Hk8U6pcJ05DvxzPQ1sd3ok6W4zsbXmOcBQMaJyCXSAwpK15u5/AsG3ACD6XY3EwmryuHMHVIxiDcbiW5iR5EzAp+5Z54GErjmS5RQXW" +
            "QY4txWotXMlyo1AgexDW63VsXkJiPfOdnVDXz6hEcOOMVLAShbN2FRXCFK6WKKvENdomfi7sTCQWUsTeJkIGNdqwPYhCCr2EyFKL7GPtBxspoMVw8yzixmtwn+PGKk28" +
            "n21jb5Z8usPi3WkXIlkMsLS4L4ou9/XbRD/sOAwHpYmx1I4SSfcy1lrGemcupy3/By0s4Fmh7i4RFova2yRYVPAgRYSHuB48wp49xucJTrKUAch+vS4elBWPirxwt88E" +
            "T/dE1qitzEhBR/KyjiaghXOgaJ7WtPaSdSJhtfThxoJUV1zgVpN76BmwAOM9MGE1Q7t1MZqIS5CDlf8VDNbQW7+QIT46y5EQeFNkNDfz0F9Y+G7eSfM8h9mbY0GaJ8df" +
            "v1hrtoKZrqw2gLi7+spQXWnGDl4e3V5l2sjApi4Ccx3m5ofi+u9wtYvgaifHP7430vyZLmx24cNfaMifISeKZL/LGSOuvmxDvJGi+i97/O4V"))

        root_special_blocks = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJyNVG1P2zAQTte0oS0w1vEyNiZF+9SJwWDS/gCvE6EMjY5ukybkJgZbpHGV2INOQuJjkfzR+x/7iTvbadcJJkgUxXe+uzzP3eNcu79+lxxzXamGdHm/h5WcbrXOP9O3" +
            "WywUXZxwJb0fOM0oS5QsvVtdX11TssgFVTqlFMYoy5SchJxNlnBEE5wqWe6hFHUzE+IeoC5UrTZhr02TiF0oOXHIMsp1ye+qEbjBIyzdI/oTG/MkeI5lpUkTv00jTlTg" +
            "QDJYHzA9I1yblSa6zDf3HKeg98GR71uPd0wz2omxGkhvO0GwivSyxVjcoj0lHaB1iKKIJmfmo469sSzvoz4TwLoClPK1kOXYroAQ8cgSqVwBiV3Mupin/TwdcHOVyYmQ" +
            "0DhKseZmwk2lnLlObJCaXBi5TrIeDimKOzELzzNFpmxHipg81qsvwTwmTwKH1OF5ariRWfuaG5D5AVkgz8iijiwGBX1j8kJOQfXdlEZDKuUNlkYwl4EstSiHpsjaFoZZ" +
            "xZl/ymBckxaKvxOjs0w1nWtBXlqmyxow8S3B46AOBMkr+JolNgHf2Un1eIe8xjyGyDK01BJZDuoPJFIYEYFGvxmQFenlaNUI19I4rtfBTI7LwqoBiBa+5NsR5SNki2PO" +
            "O3vujKA2gpl7ocraPkjdPxDdjmns7JjpH3GUcq2soCArnzCK/I9J3IeoalPEnPo6Vg2ELKYgCdBzMWSxfntgZz2U6DwPfPlaICE9OIpiA6VAUZY7jHPWtacrxqfcKG1I" +
            "dN5ECohIgOfJBYz+IkU9ZVC7ugVwGNvgbYPX90HomwSH5yg/LMaAw3IjMiRLqTlS4+Xr/5bHl7rHenZt6W4b4+sN+aazRUb2oIFBUCD78DSBiB3e+2Gt6lAtK+u3hpDr" +
            "ZdYOIVh7sFiqG3qqvvmXPUwvnpZGiv+qeC53/EcnhZFOpu/XiXfErBYGIm+HM2oHuu3Cd0UJWQtZkuBQ/zIzGIdY/QONReYz"))

        root_error_analysis = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJydU99r1EAQzvXSS6/XU9TanlrhEIQDtVpfa/3RWhXXSqHRPklZk7WzNLd7bDbaEwo+XmEe1//X2STXClYEE0JmZmcm3/fN5Ef4sxsG5XXiBhja8Ug4vBTHRx/kw5c6" +
            "KYZCWYfRV2FyqZXD2cera6uPHDZtIZ0vmU0ynucOF6hmSyvLpRLGYWvEDR/mZUr4ng+p6/wOne1LlepvDud2dS6tb/nJDVjIZgSGe/K7KN0DdlNge0eq/r5MLTgWUDF5" +
            "b4Q8BOvd9g4/rg/fBkHDn1OgPq8i0UeZy8+ZcBOMthUnK/VmrHUWy5HDgGjt8jSV6rD8aFDdAlvv+FgXxLpNlGq7wFZWWUQIIliB9gmReC30UFgzrssJt3U5ziUgs9QI" +
            "z61Mxznq9Mp4FXzdADq4PI0cCGO0OeCKZ+Nc5g66lSCBgMve2mRLAq6wAK7Sc62kBovV6/oEliawDD244TMb1S3gFqxga1OblAYxwdlYWlIBegXc/g089CvMz9kiYYY7" +
            "1KHC6llvFtbSaKZge2ehi9HO+K+WaHus6dEuEdrm39BiGItjkndxz3Jj+9u+Y//FWcd7E2xvgUiO/MjcKUalQ8M7LbBpaHdo/M1EZ/4dkZ+PuHKsgRHFaruoeN6d4p+f" +
            "iv1grUbcYFGN+Bnr/oe+hBLu40KJPe9/0YVK3cX6brBOrW8lb0RYYiPON+E80K3XsEa2zjr/RIbRnjbWr/CkgHXKe0LPBmvAU1KB/xkSF2UV2Em0UiLx/2NOS1us/gJ9" +
            "B1HW"))

        root_window_popup_message = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJy1U1tr1EAUTrrJXuzFWy+r24e+CItgrEVFtIpabzhWSo32QZZluhn2DE0yIZnUrlDwQaEP8yIdn/2L/gRPMhu7WvTNDCHnzMk5+b5vvnxyvu07Vnkd6q5y5ChhWs35" +
            "/t5bfv2JGOQRi6VWjX2WZlzEWrlr3g1vVauazLkuWtxBSLNMqxb27PA4EB+0qic0pVFW1p3XNMKR7U3KY1PvJyLJk37EsowOsdTcEhmXxfSe7pI2aTLlvOEfWZmukzmm" +
            "Wps8XtnhgQRN1tWZInvB+BCkJnNYpAeTRcxOio13POO7IdNHqvE0phgFRegLEfo80cpCbls0CHg8LD9nm8VU/RUdiVwaXlVcfyzSgKU4wfW5xKnQVjOG1MqzkA5RhiWf" +
            "pZG/52HXhkiZNxBxJmmh4WK5ZTLPNBU9+li/RPWbX/S2zlU9NJ9C5aABy9A6RH2eMxExmY4Qn4XrLpmROlPNAfAwSFkpW/m+apZYd1moi8YuTKvZaqfPEYmG2YLkFJli" +
            "cNZENoPzZAouEBsuIg7bgnnzWDiCxSNYQoaOzw4Qv/Pj+9fPaIANEYoU08771QjleRTyYVy6BFbUwiTHk8qxJmN+tRT9QSxVG4iweDYwzxIaa2KrBu6N49zwmTHjJFoH" +
            "Va84XZ7c7e/mUoq4DyIsTsYQdEhrTHCN1AqCFhK0/kYQLvXGyuJi0IHlHK5MHAB0TRVnoe5wtadzuIfj1vG+j7o9qPDCwwpi5zeIY6f/idH9rxhN8VqF6NwvI1T/nYFR" +
            "jithzBsvuP/yAqwpd2ywm3ALbsMdYpcHe0oQenqL5bmaRhfGbFD87Rn6Nvd+As5ufMY="))


        root=TTk()

        self.TTkWindow_customer_info = ttk.TTkWindow(parent=self.root,
                                                     pos=(4, 1), size=(71, 30),
                                                     maxSize=(71, 30),minSize=(71, 30),
                                                     title=ttk.TTkString("Log Analyser", ttk.TTkColor.ITALIC),
                                                     border=True,
                                                     layout=ttk.TTkGridLayout())

        self.TTkWindow_flow = ttk.TTkWindow(parent=self.root,
                                                     pos=(85, 1), size=(50, 32),
                                                     maxSize=(50, 32),minSize=(50, 32),
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
                                             maxSize=(71, 32), minSize=(71, 32),
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


        # Pull all required components
        #
        #

        TTkFileButtonPicker: ttk.TTkFileButtonPicker = customer_info_widget.getWidgetByName('TTkFileButtonPicker')
        TTkComboBox_customer: ttk.TTkComboBox = customer_info_widget.getWidgetByName('TTkComboBox_customer')
        TTkComboBox_ticket: ttk.TTkComboBox = customer_info_widget.getWidgetByName('TTkComboBox_ticket')
        TTkLabel_file_size: ttk.TTkLabel = customer_info_widget.getWidgetByName("TTkLabel_file_size")
        TTkButton_new_customer: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_new_customer')
        TTkButton_new_ticket: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_new_ticket')
        TTkButton_main_exit: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_main_exit')
        TTkLabel_analysis_status: ttk.TTkLabel = customer_info_widget.getWidgetByName('TTkLabel_analysis_stat')

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
        TTkmenuButton_qv_ppage = root_window_quickview.getWidgetByName('menuButton_qv_ppage')
        TTkmenuButton_qv_npage = root_window_quickview.getWidgetByName('menuButton_qv_npage')
        TTkmenuButton_qv_pages = root_window_quickview.getWidgetByName('menuButton_qv_pages')
        TTkTextEdit_quickview: ttk.TTkTextEdit = root_window_quickview.getWidgetByName('TTkTextEdit_quickview_content')

        TTkButton_flow_quickview = root_window_flow.getWidgetByName('TTkButton_flow_quickview')
        frame_transaction = root_window_transaction.getWidgetByName('TTkFrame_transactions')
        TTkButton_tx_quickview = ttk.TTkButton = root_window_transaction.getWidgetByName('TTkButton_tx_quickview')
        TTkList_transaction = root_window_transaction.getWidgetByName('TTkList_transaction')
        frame_flow = root_window_flow.getWidgetByName('TTkFrame_flow')
        TTkButton_flow_details: ttk.TTkButton = root_window_flow.getWidgetByName('TTkButton_flows_details')
        TTkLabel_Flows = ttk.TTkLabel = customer_info_widget.getWidgetByName('TTkLabel_Flows')
        TTKButton_show_flow: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_show_flow')
        TTkList_flow: ttk.TTkList = root_window_flow.getWidgetByName('TTkList_flow')
        TTkButton_viewfile: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_viewfile')

        TTkWindow_popup_new_data: ttk.TTkWindow = root_window_popup_add_customer_ticket.getWidgetByName('TTkWindow_popup_new_data')
        TTkButton_popup_newcustomer_ok: ttk.TTkButton = root_window_popup_add_customer_ticket.getWidgetByName('TTkButton_popup_newcustomer_ok')
        TTkButton_popup_newcustomer_cancel: ttk.TTkButton = root_window_popup_add_customer_ticket.getWidgetByName('TTkButton_popup_newcustomer_cancel')
        TTkLineEdit_popup_newcustomer_customer: ttk.TTkLineEdit = root_window_popup_add_customer_ticket.getWidgetByName('TTkLineEdit_popup_newcustomer_customer')
        TTkLineEdit_popup_newcustomer_ticket: ttk.TTkLineEdit = root_window_popup_add_customer_ticket.getWidgetByName('TTkLineEdit_popup_newcustomer_ticket')
        TTkFrame_error_analysis: ttk.TTkFrame = root_error_analysis.getWidgetByName('TTkFrame_error_analysis')

        self.TTkWindow_popup_message: ttk.TTkWindow = root_window_popup_message.getWidgetByName("MainWindow_popup_message")
        self.TTkWindow_popup_message.setVisible(False)
        # Create tab container and add 2 tabs on it:
        #Tab Container
        self.TTkTabContainer = ttk.TTkTabWidget()
        self.TTkTabContainer.addTab(customer_info_widget,label='Trace analysis')
        self.TTkTabContainer.addTab(TTkFrame_error_analysis, label='Log error analysis')

        # special blocks details
        self.TTkTree_specialblocks: ttk.TTkTree = root_special_blocks.getWidgetByName('TTkTree_specialblocks')
        self.TTkTextEdit_specialblocks: ttk.TTkTextEdit = root_special_blocks.getWidgetByName('TTkTextEdit_specialblocks')
        self.TTkWindow_specialblocks: ttk.TTkWindow = root_special_blocks.getWidgetByName('TTkWindow_specialblocks')
        self.TTkWindow_specialblocks.setVisible(False)
        self.TTkTextEdit_specialblocks.setReadOnly(False)
        self.TTkWindow_specialblocks.sizeChanged.connect(_special_block_resize)
        self.TTkmenuButton_sp_wordwrap:  ttk.TTkMenuBarButton = root_special_blocks.getWidgetByName('menuButton_sp_wordwrap')
        self.TTkmenuButton_sp_exit:  ttk.TTkMenuBarButton = root_special_blocks.getWidgetByName('menuButton_sp_exit')
        self.TTkmenuButton_sp_wordwrap.menuButtonClicked.connect(_special_block_details_wordwrap)
        self.TTkmenuButton_sp_exit.menuButtonClicked.connect(_special_block_details_exit)

        frame_flow.move(60,4)

        # pop window new customer/ticket
        TTkButton_popup_newcustomer_ok.clicked.connect(_process_new_data)
        TTkButton_popup_newcustomer_cancel.clicked.connect(_close_popup_new_data)

        # TTkWindow_popup_new_data.setVisible(False)

        # FilePicker
        TTkButton_viewfile.setEnabled(False)
        TTkFileButtonPicker.pathPicked.connect(_filetxtchange)
        TTkFileButtonPicker.clicked.connect(_remember_last_path)
        TTkButton_viewfile.clicked.connect(_viewlogfile)

        # Party
        frame_party = root_window_party.getWidgetByName('MainWindow_party')
        TTkFrame_party = root_window_party.getWidgetByName('TTkTree_frame')
        self.tree_party: ttk.TTkTree = root_window_party.getWidgetByName('TTkTree_party')
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
        TTkButton_main_exit.clicked.connect(_exit_application)
        TTkLabel_analysis_status.setVisible(False)
        TTkWindow_popup_new_data.setVisible(False)


        # Flow
        TTkButton_flow_trace.setEnabled(False)
        TTkButton_flow_trace.clicked.connect(lambda: _trace('flow'))
        TTKButton_show_flow.clicked.connect(lambda: _show_hide_window('flow'))
        TTkList_flow.textClicked.connect(lambda: _quick_view_check('flows', TTkList_flow.selectedLabels()))
        TTkButton_flow_quickview.clicked.connect(lambda: _quick_view_check_pages(TTkList_flow.selectedLabels()))
        TTkButton_flow_details.clicked.connect(lambda: _special_block_details(TTkList_flow))

        # Gestores de listas perezosas
        self.flow_list_manager = lazy_loader.LazyListManager(
            list_widget=TTkList_flow,
            chunk_size=100
        )
        self.tx_list_manager = lazy_loader.LazyListManager(
            list_widget=TTkList_transaction,
            chunk_size=100
        )
        #

        # Transaction
        TTkButton_tx_trace.setEnabled(False)
        TTkButton_tx_trace.clicked.connect(lambda: _trace('txn'))
        TTKButton_show_txn.clicked.connect(lambda: _show_hide_window('txn'))
        TTkButton_tx_quickview.setEnabled(False)
        TTkList_transaction.textClicked.connect(lambda: _quick_view_check('transactions',
                                                                        TTkList_transaction.selectedLabels()))
        TTkButton_tx_quickview.clicked.connect(lambda: _quick_view( TTkList_transaction.selectedLabels()))

        # Quick View
        self.TTkWindow_quickview.addWidget(frame_quickview)
        TTkButton_flow_quickview.setEnabled(False)
        TTkmenuButton_qv_pages.setEnabled(False)
        TTkmenuButton_quickview_exit.menuButtonClicked.connect(lambda: self.TTkWindow_quickview.setVisible(False))
        _quickview_resize()

        # LogViewer
        TTkWindow_logging.move(4,31)
        TTkWindow_logging.sizeChanged.connect(_logging_resize)
        TTkWindow_logging.resize(120,9)
        TTkWindow_logging.setWindowFlag(ttk.TTkK.WindowFlag.WindowReduceButtonHint|ttk.TTkK.WindowFlag.WindowMinimizeButtonHint)

        # Quick View
        self.TTkWindow_quickview.sizeChanged.connect(_quickview_resize)


        self.TTkWindow_flow.setVisible(False)
        self.TTkWindow_transaction.setVisible(False)
        self.TTkWindow_party.setVisible(False)
        self.TTkWindow_quickview.setVisible(False)

        self.TTkWindow_transaction.addWidget(frame_transaction)
        self.TTkWindow_flow.addWidget(frame_flow)
        # self.TTkWindow_customer_info.addWidget(customer_info_widget.getWidgetByName('TTkFrame'))
        self.TTkWindow_customer_info.addWidget(self.TTkTabContainer)
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
        root.layout().addWidget(self.TTkWindow_specialblocks)
        root.layout().addWidget(TTkWindow_popup_new_data)
        root.layout().addWidget(TTkWindow_logging)
        root.layout().addWidget(self.TTkWindow_popup_message)
        # root.layout().addWidget(TTkWindow_popup_new_data)
        InteractiveWindow.update_tui_from_queue()


        process_ui_commands(root)

        root.mainloop()

    def tk_popup_window(self, origen,  message, title="Information", button="Ok", icon="Information"):
        """
        An emergent window to communicate a message to user.
        :return:
        """

        buttonName = {
            'Ok':              ttk.TTkMessageBox.StandardButton.Ok,
            'Open':            ttk.TTkMessageBox.StandardButton.Open,
            'Save':            ttk.TTkMessageBox.StandardButton.Save,
            'Cancel':          ttk.TTkMessageBox.StandardButton.Cancel,
            'Close':           ttk.TTkMessageBox.StandardButton.Close,
            'Discard':         ttk.TTkMessageBox.StandardButton.Discard,
            'Apply':           ttk.TTkMessageBox.StandardButton.Apply,
            'Reset':           ttk.TTkMessageBox.StandardButton.Reset,
            'RestoreDefaults': ttk.TTkMessageBox.StandardButton.RestoreDefaults,
            'Help':            ttk.TTkMessageBox.StandardButton.Help,
            'SaveAll':         ttk.TTkMessageBox.StandardButton.SaveAll,
            'Yes':             ttk.TTkMessageBox.StandardButton.Yes,
            'YesToAll':        ttk.TTkMessageBox.StandardButton.YesToAll,
            'No':              ttk.TTkMessageBox.StandardButton.No,
            'NoToAll':         ttk.TTkMessageBox.StandardButton.NoToAll,
            'Abort':           ttk.TTkMessageBox.StandardButton.Abort,
            'Retry':           ttk.TTkMessageBox.StandardButton.Retry,
            'Ignore':          ttk.TTkMessageBox.StandardButton.Ignore,
            'NoButton':        ttk.TTkMessageBox.StandardButton.NoButton
        }

        iconVal = {
            'NoIcon':ttk.TTkMessageBox.Icon.NoIcon,
            'Question':ttk.TTkMessageBox.Icon.Question,
            'Information':ttk.TTkMessageBox.Icon.Information,
            'Warning':ttk.TTkMessageBox.Icon.Warning,
            'Critical':ttk.TTkMessageBox.Icon.Critical} # .get(icon.currentText(),ttk.TTkMessageBox.Icon.NoIcon)

        messageBox = ttk.TTkMessageBox(
                title=title,
                text=message,
                icon=iconVal[icon],
                standardButtons=buttonName[button])

        ttk.TTkHelper.overlay(origen, messageBox, 2, 1, True)

    def clear_tree_party(self):
        """

        :return:
        """
        # get all original settings to add them into new widget that will replace old one...
        # pos=self.tree_party.pos()
        # size=self.tree_party.size()
        # parent=self.tree_party.parentWidget()
        # self.tree_party = ttk.TTkTree(pos=pos,size=size,parent=parent)
        self.tree_party.clear()

    def clear_spb_tree(self):
        self.TTkTree_specialblocks.clear()
        # pos=self.TTkTree_specialblocks.pos()
        # size=self.TTkTree_specialblocks.size()
        # parent=self.TTkTree_specialblocks.parentWidget()
        # name = self.TTkTree_specialblocks.name()
        # self.TTkTree_specialblocks = ttk.TTkTree(parent=parent, size=size, pos=pos, name=name).clear()


    @staticmethod
    def update_tui_from_queue():

        # Si se está cerrando, procesar solo mensajes pendientes
        if shutdown_event.is_set() and log_queue.empty():
            return  # No programar más actualizaciones

        while not log_queue.empty():
            message = log_queue.get_nowait()
            if w:
                msg = HighlightCode.highlight(ttk.TTkString(message))
                tui_logging.append(msg)
            else:
                print(message)

            # tui_logging._verticalScrollBar.setValue(tui_logging._verticalScrollBar.maximum())

        # Programar próxima revisión solo si no se está cerrando
        if not shutdown_event.is_set():
            threading.Timer(0.5, InteractiveWindow.update_tui_from_queue).start()

def mainX():
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
            print(f"Sorry but there's not information about {ref_id}...")
            print("Exiting...")
            return None

        test = UMLStepSetup(get_configs(), co)
        test.file = file_to_analyse
        test.parallel_process(co)
        c_uml = CreateUML(co, file_to_analyse)
        ref_id = Icons.remove_unicode_symbols(ref_id)
        script = c_uml.generate_uml_pages(client_name='test', output_prefix=ref_id)
        print("\n".join(script))
        ##########################
        return file_to_analyse
    return None

def load_highlights():
    """

    :return:
    """

    highlights = Configs.get_config_for('FILE_SETUP.CODE_HIGHLIGHTS')

    for each_env in highlights:
        for each_item in highlights[each_env]:
            for each_color in highlights[each_env][each_item]:
                desc = f'{each_env}:{each_item}'
                for each_rgx in highlights[each_env][each_item][each_color]:
                    HighlightCode(desc, each_rgx, each_color)

    pass

    # HighlightCode('timestamps', r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}', '#00AAAA')
    # HighlightCode('timestamps', r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[,.]\d+Z','#00AAAA')
    # HighlightCode('level', 'WARN', '#AAAA00')
    # HighlightCode('level', 'WARNING', '#AAAA00')
    # HighlightCode('level', r'\bINFO ', '#44AA00')
    # HighlightCode('level', 'ERROR ', '#FF8800')
    # HighlightCode("specialBlocks", "Timestamp:",'#44AA00')
    # HighlightCode("specialBlocks", "Event:",'#44AA00')
    # HighlightCode("specialBlocks", "Actions:",'#44AA00')
    # HighlightCode("specialBlocks", "Continuation:",'#44AA00')
    # HighlightCode("specialBlocks", "isFlowResumed:",'#44AA00')
    # HighlightCode("specialBlocks", "Diff between previous and next state:",'#44AA00')
    # HighlightCode("specialBlocks", "checkpoint\\..*:",'#44AA00')

def main():

    log_file = args.log_file

    # Create file_to_analyse object containing file_to_analyse that will be analysed, starting with a block-size of 15 Mbytes
    file_to_analyse = FileManagement(log_file, block_size_in_mb=15, debug=True)
    if not file_to_analyse.state:
        return

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
    threading.Timer(0.5, InteractiveWindow.update_tui_from_queue).start()

    if not file_to_analyse:
        write_log(f"Sorry unable to analyse given file",level="Error")
        return

    if args.list_transactions:
        tc = 0
        tl = file_to_analyse.get_all_unique_results(CordaObject.Type.FLOW_AND_TRANSACTIONS,True)
        if not tl:
            write_log("Sorry no transactions found")
            return
        print(f"Transactions found:")
        for each_tx in tl:
            if each_tx.get_type() == 'TRANSACTION':
                tc = tc +1
                print(f'{tc: >3} - {each_tx.get_reference_id()}')

        print(f'Transactions found... {tc}\n\n')

    if args.list_flows:
        fc = 0
        fl = file_to_analyse.get_all_unique_results(CordaObject.Type.FLOW_AND_TRANSACTIONS,True)
        if not fl:
            write_log("Sorry no flows found", level="WARN")
            return

        print('Flows found:')
        for each_tx in fl:
            if each_tx.get_type() == 'FLOW':
                fc = fc + 1
                print(f'{fc:>3} - {each_tx.get_reference_id()}')
        print(f'Flows found... {fc}\n\n')

    if args.list_parties:

        pc = 0
        pl = file_to_analyse.get_all_unique_results(CordaObject.Type.PARTY,True)
        if not pl:
            write_log("Sorry no parties found")
            return

        print('Parties found:')
        for each_tx in pl:
            pc = pc + 1
            print(f'{pc:>3} - {each_tx.name}')

        print(f'Parties found... {pc}')


if __name__ == "__main__":

    max_number_items_fNtx = 15
    tui_logging = None
    Configs.load_config()
    load_highlights()
    KnownErrors.configs = Configs
    KnownErrors.initialize()
    data_dir = Configs.get_config_for('FILE_SETUP.CONFIG.data_dir')
    customer_info = CustomerInfo()
    app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"
    w = None
    # test()

    # file_to_analyse = None

    ## TESTS
    # Configs.load_config()
    #
    # file_to_analyse = FileManagement('/home/larry/IdeaProjects/logtracer/checks/log-test.log',
    #                                  block_size_in_mb=15, debug=True)
    # # Analyse first 50 (by default) lines from given file_to_analyse to determine which Corda log format is
    # # This is done to be able to separate key components from lines like Time stamp, severity level, and log
    # # message
    # file_to_analyse.discover_file_format()
    # #
    # # Analyse file for specific block lines that lack of key fields (like stack traces, and flow transitions):
    #
    # special_blocks = BlockExtractor(file_to_analyse, Configs.config)
    # special_blocks.extract()
    # special_blocks.summary()
    # test = special_blocks.get_reference('33deaf04-1a1c-4f79-8a33-83c5c27a2979')
    # test1 = special_blocks.get_reference(block_type='ERRORS')
    # test3 = special_blocks.get_reference()
    # pass

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


    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                            help='Give actual log file to analyse')
    parserargs.add_argument('-r', '--reference',
                            help='Reference ID to trace flow-id or tx-id')
    parserargs.add_argument('-t', '--list-transactions',
                            help='list all transactions found', action="store_true")
    parserargs.add_argument('-f', '--list-flows',
                            help='list all flows found', action="store_true")
    parserargs.add_argument('-p', '--list-parties',
                            help='list all parties found', action="store_true")

    args = parserargs.parse_args()

    if args.log_file and args.list_transactions or args.list_flows or args.list_parties:
        main()
        shutdown_event.set()


    if not args.log_file:
        w = InteractiveWindow()
        #
        if not shutdown_event.is_set():
            w.tk_window()

    pass

