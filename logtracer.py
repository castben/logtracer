#!./system/bin/python
import cProfile
import glob
# Program to test extraction and validation of X500 names.
import os
import argparse
import re
import threading
from datetime import datetime
from get_refIds import GetRefIds
from object_class import Configs, FileManagement, BlockExtractor
from object_class import CordaObject
from get_parties import GetParties
from uml import UMLEntityEndPoints, UMLStepSetup, CreateUML
import TermTk as ttk
from log_handler import write_log, HighlightCode
from log_handler import log_queue

def get_configs():
    return Configs

class InteractiveWindow:
    """
    A class that create an interactive experience
    """

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

        HighlightCode('timestamps', r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}', '#00AAAA')
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
        app_path = f'{app_path}/plugins/plantuml_cmd/data/test'
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
        from TermTk import TTkUtil, TTkUiLoader, TTk


        def _filetxtchange():
            """

            :return:
            """
            global tui_logging
            # logfile_name.setWordWrapMode(1)
            # logfile_name.setWrapWidth(6)
            txt = TTkLineEdit_logfile.text().toAscii()
            self.filename = txt
            txt = os.path.basename(txt)
            TTkLineEdit_logfile.setText(txt)
            TTkButton_start_analysis.setEnabled(True)
            tui_logging = TTkTextEdit_logging
            write_log('Checking for existing diagrams...')
            self.check_generated_files()

        def _start_analysis():
            """

            :return:
            """
            global file_to_analyse
            TTkButton_start_analysis.setEnabled(False)

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

                TTkLabel_Parties.setText(f"{len(file_to_analyse.get_all_unique_results('Party'))}")
                results = collect_refIds.classify_results(FileManagement.get_all_unique_results('Flows&Transactions'))
                TTkLabel_Flows.setText(f"{len(results['FLOW'])}")
                TTkLabel_Transactions.setText(f"{len(results['TRANSACTION'])}")

                # Flow list
                for each_flow in results['FLOW']:
                    list_flow.addItem(each_flow)

                # Transaction list
                for each_tx in results['TRANSACTION']:
                    list_transactions.addItem(each_tx)

                # Party List
                party_headers = {
                    'Party X.500 name': 70,
                    'Role': 15
                }

                tree_party.setHeaderLabels(party_headers)
                # Set column width
                for pos,header in enumerate(party_headers.keys()):
                    tree_party.setColumnWidth(pos, party_headers[header])

                for each_party in FileManagement.get_all_unique_results('Party'):
                    if each_party.get_corda_role():
                        role = each_party.get_corda_role()
                    else:
                        role = 'party'
                    tree_element = ttk.TTkTreeWidgetItem([each_party.name, role])
                    tree_party.addTopLevelItem(tree_element)
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
            file_to_analyse.start_stop_watch('Main-search', True)
            analysis_thread = threading.Thread(target=_analysis_process)
            analysis_thread.start()

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

        def _trace(source):
            """
            Trace
            :param source: reference id for the object to trace
            :return:
            """
            global file_to_analyse

            if source == 'flow':
                ref_id = list_flow.selectedLabels()[0]
            if source == 'txn':
                ref_id = list_transactions.selectedLabels()[0]

            if not source:
                return

            sref_id = ref_id.toAscii()
            co = CordaObject.get_object(sref_id)

            if not ref_id:
                write_log("Reference ID not found unable to trace it, please try another")
                return
            write_log('\n\n\n')
            write_log('=============================================================================')
            write_log(f'Starting Trace for {ref_id}')
            uml_trace = UMLStepSetup(get_configs(), co)
            uml_trace.file = file_to_analyse
            uml_trace.parallel_process(co)
            c_uml = CreateUML(co, file_to_analyse)
            script_file = c_uml.generate_uml_pages(client_name='test', output_prefix=ref_id)
            if not script_file:
                write_log('No useful information was related to this reference id', level='WARN')
            else:
                write_log("\n".join(script_file))
                success = CreateUML.render_uml(file=script_file)

                if success:
                    self.add_generated_file(ref_id, script_file)


            write_log('=============================================================================')

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

        # Data generated using ttkDesigner
        customer_info_widget = TTkUiLoader.loadDict(TTkUtil.base64_deflate_2_obj(
            "eJy9Vu1vEzcYT8g1Lw1pCGlHoUw67VMYWlfaIVXJxmhLKezaKVLDmMRQZO7c2urFju58QCYh7WMi+ePt4/6O/XXT9vjOcVPWhgaNJTqdn8f3+Pd73mz/Zv3+ZzmT/N7F" +
            "DWmJQR/HcqHTOXlGv37E3aiHmYhl4TUOQspZLOfWV++trsUyJyIaK5M510dhGMurYLPDmUCU4SCW+T4KUC9MPrF+RD1Ydf4A5p5T5vE3sSy2eUiFWvJl3HAs5wqW1iH9" +
            "FSfinnMLy9IBZfZz6gkSOxkwBukJpsdEKLF0gN7qyR8ymayaB4WeTzWFn2hIX/k4HsrCLkMw8tSww7nfof1YZsCtNvI8yo4T0Ez6xzK/jwY8Aq9L4JIeRzLvpyNwiBTI" +
            "bVJ6B07sYd7DIhhoc+At4lAWXUJ9L8DKt+RzWYSVHgcqCsquQcqTmopCzwIyqarRQ+cGJjUnQ67DU098IYvpa2lIPhuSG2SZ3Extkj8mK+S2zG/zwIPID+VchwpwW1Z2" +
            "olAAv8B+yo54HJHPJ7gTO6X8wFkCyuQLWO+U6j56hf0zVLVGU81qqiU1qjkloJq9iKq0OvitCuaYTROKaIf7HIrEWnmx1oOpLZ8es6TSnGwkcwEUCOQ453JfvQsgh33E" +
            "YFIWQKfHUcq3rNhBze16VBjKixPKrquBNf2yob+Y0s+eoQ/DU+7zT1k/EnZHdQWgl3Zdwu0D7oGUIZtkOSLfweABPN+D3cMxKbIxJjI/jt1X90z0cjNEj2xCFVL3BAvb" +
            "bsakqUNGvgWoC7C3x9jXJ4MgkkVMCHLnhuDgr7/PBoDsgfRkqq+yriqZ+ng7EoKztsIJTCLOn0xILDmWIZFTJKpAIjclEJVD7GNX2Mg+ghVjcncIRUWwe6J6Ox7JQiJA" +
            "l4+k1UawM8jsKvT4Duon+4wsKyL2I4p8fgx6kATsatAnW75vq7nQbnx5B77bcl3cF+M8y1Jip6UPZvzaOONdgEmJJu5ecYoz5n0/tW/al8p7slulYTbRXzaqbihQILqI" +
            "IX8Q0tCkoHw2BdcuSMFIc1o4VMvYW2aZu0Pyy4i8HM3QCBumEWoavJIGpPKBgFQ6AWIhclU2w0s2wzn43xj8+oz4j33YiOz09/H46wa/OiN+G2JPcfhR+KdlqVfRLKqG" +
            "RSFlkZnOAp6mrK682NhsrbfWWuv377cuS2HJUJhMpOFR+794LBgeSUINgfonJrA9uSmajfn9XaKkWbSmHE6jS+7NhE0eiOOdgPA3XbidiYHGvGlKYD7FzF94IEIVWodg" +
            "D40/mt74bNLZSeQjX5lr4PonBL71HrA4LTqDX/sv8fG/VSiKZNnljGFd7MmFUOZDzNRdjfwsiwF2MX2thD9AD/cg5MeyqkoiOS29RigCOJSs0Odwi7oaYqHuU6kW1l/9" +
            "Bxp7k/A="))

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
            "eJyVk01v00AQhu3aiRNCoEAoqaCAEIecwseJD3EgpIAwQZVqaIWoKtceOqs43she0wapEkdH2uPyf5m1nVKQQkUsy7MzO7PPO7P5Yf8c2kbxO1E9aYvZFJS85Hnjj+zB" +
            "kAfZBGKhpPMNkpTxWMna4/6j/kMlLZExpVNqQeSnqZINynmd+BNKr099MtIibH8oXKsjn8U7LA750T5FxYwStnjKhC66p3qu7Zog7W32HYrlgbsBsjli8d0dFgpUriEv" +
            "6NVbYIco9LI58o+r4DvDMHWcHFW89DifWMoOIlC5dDZjn6xQmx7nkcemShokbMsPQxYfFoca5QOy/t6f8Yx0N0nUwq4PeBJCouay5jFBVbGbyXpURkkqOngLmyck7A3w" +
            "CYhkVpUkLUKlshEgi8IECr3l/obe38NW0fCieVVzsK15VtwVwMva+uKuAV5xDbxK77VCHXbKz/Uc13K8gV1c1zvN8gG8STQbOd7WEhPBIFUZ3jmDifdKus9uh+jw/l6p" +
            "gdrjjb0ESF7F1q4cf6CZ1KYSbdftnIsmnW1ODNTmPJNWwo/0AK2AR/rr0Dqd+rFyTemQr7IzP8MnVPIpvc9cE5+TqyTUQxlkQtDNOctYuvZpnqftW68YW66lGWvEaC1l" +
            "tD04pjFbL3WBjVw2XyEEY31raOROsaD7M19ChS8WLKu/WUKIQECF0z3FuVjiNP6FgwNZH1bpNMbhHDf/6+gJD9nXxbTaf3fi3KNHVfryoyHLZCvgcQyB/hOndKuz/i/3" +
            "ymDs"))

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

        root=TTk()

        self.TTkWindow_customer_info = ttk.TTkWindow(parent=self.root,
                                                     pos=(17, 1), size=(68, 27),
                                                     title=ttk.TTkString("Logs reader", ttk.TTkColor.ITALIC),
                                                     border=True,
                                                     layout=ttk.TTkGridLayout())


        self.TTkWindow_flow = ttk.TTkWindow(parent=self.root,
                                                     pos=(85, 1), size=(45, 34),
                                                     title=ttk.TTkString("Flows", ttk.TTkColor.ITALIC),
                                                     border=True,
                                                     layout=ttk.TTkGridLayout(),
                                                     flags=ttk.TTkK.WindowFlag.WindowMinimizeButtonHint)

        self.TTkWindow_party = ttk.TTkWindow(parent=self.root,
                                             pos=(85, 4), size=(98, 32),
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

        TTkLineEdit_logfile: ttk.TTkLineEdit = customer_info_widget.getWidgetByName('TTkLineEdit_logfile')
        TTkFileButtonPicker: ttk.TTkFileButtonPicker = customer_info_widget.getWidgetByName('TTkFileButtonPicker')
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
        TTkTextEdit_quickview: ttk.TTkTextEdit = root_window_quickview.getWidgetByName('TTkTextEdit_quickview_content')
        TTkButton_flow_quickview = root_window_flow.getWidgetByName('TTkButton_flow_quickview')
        frame_transaction = root_window_transaction.getWidgetByName('TTkFrame_transactions')
        TTkButton_tx_quickview = ttk.TTkButton = root_window_transaction.getWidgetByName('TTkButton_tx_quickview')
        list_transactions = root_window_transaction.getWidgetByName('TTkList_transaction')
        frame_flow = root_window_flow.getWidgetByName('TTkFrame_flow')
        TTkLabel_Flows = ttk.TTkLabel = customer_info_widget.getWidgetByName('TTkLabel_Flows')
        TTKButton_show_flow: ttk.TTkButton = customer_info_widget.getWidgetByName('TTkButton_show_flow')
        list_flow: ttk.TTkList = root_window_flow.getWidgetByName('TTkList_flow')
        frame_flow.move(60,4)

        # Party
        frame_party = root_window_party.getWidgetByName('MainWindow_party')
        tree_party: ttk.TTkTree = root_window_party.getWidgetByName('TTkTree_party')
        TTKButton_show_party.clicked.connect(lambda: _show_hide_window('party'))

        #Main window
        TTkFileButtonPicker.pathPicked.connect(_filetxtchange)
        TTkButton_start_analysis.clicked.connect(_start_analysis)

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
        _quickview_resize()


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

        tui_logging = TTkTextEdit_logging
        root.layout().addWidget(self.TTkWindow_customer_info)
        root.layout().addWidget(self.TTkWindow_party)
        root.layout().addWidget(self.TTkWindow_flow)
        root.layout().addWidget(self.TTkWindow_transaction)
        root.layout().addWidget(self.TTkWindow_quickview)
        root.layout().addWidget(TTkWindow_logging)
        InteractiveWindow.update_tui_from_queue()
        root.mainloop()

    @staticmethod
    def update_tui_from_queue():
        while not log_queue.empty():
            message = log_queue.get_nowait()
            tui_logging.append(message)  # Tu widget de logs en PyTermTk

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

    # file = main()

    pass
    # tracer = TracerId(get_configs())
    # #
    # tracer.tracer(file)

    # cProfile.run("main()")#, 'profile-results.prof')
