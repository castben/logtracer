# logtracer/core.py
import threading
from enum import Enum
from object_class import FileManagement
from object_class import BlockExtractor
from get_parties import GetParties
from get_refIds import GetRefIds
from object_class import CordaObject
from object_class import Configs  # o pásalo como parámetro
from object_class import KnownErrors
from error_log_analysis import ErrorAnalysis
import os

from uml import CreateUML, UMLStepSetup

def analyze_corda_log(log_file_path: str, what_to_collect:CordaObject.Type=None, datainfo=None) -> dict:
    """
    Analiza un archivo de log de Corda y devuelve un diccionario con:
    - parties
    - flows
    - transaction
    - estadísticas (tiempo, conteos, etc.)
    """
    
    # Always convert it into a proper list
    if isinstance(what_to_collect, CordaObject.Type):
        what_to_collect = [what_to_collect]
        
    Configs.load_config()
    payload = {
        "summary":{
            "log_file": log_file_path
        }
    }
    KnownErrors.configs = Configs
    KnownErrors.initialize()
    data_dir = Configs.get_config_for('FILE_SETUP.CONFIG.data_dir')

    app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"

    # 1. Configurar archivo
    file_to_analyse = FileManagement(log_file_path, block_size_in_mb=15)

    if not file_to_analyse.state:
        raise ValueError(f"Unable to to read given file due to: {file_to_analyse.state_message}")

    file_to_analyse.discover_file_format()
    payload["summary"]["file-version-used"] = file_to_analyse.logfile_format
    special_blocks = None
    collect_parties = None
    collect_refIds = None
    collect_errors = None

    if not what_to_collect or CordaObject.Type.SPECIAL_BLOCKS in  what_to_collect:
        # 2. Extraer bloques especiales (opcional, si los necesitas en la API)
        special_blocks = BlockExtractor(file_to_analyse, Configs.config)
        special_blocks.extract()

    if not what_to_collect or CordaObject.Type.PARTY in what_to_collect:
        # 3. Configurar recolectores
        #
        # Party collection
        collect_parties = GetParties(Configs)
        collect_parties.set_file(file_to_analyse)
        collect_parties.set_element_type(CordaObject.Type.PARTY)
        file_to_analyse.add_process_to_execute(collect_parties)

    if not what_to_collect or CordaObject.Type.FLOW_AND_TRANSACTIONS in what_to_collect:
        #
        # Transactions and Flows collection
        collect_refIds = GetRefIds(Configs)
        collect_refIds.set_file(file_to_analyse)
        collect_refIds.set_element_type(CordaObject.Type.FLOW_AND_TRANSACTIONS)
        file_to_analyse.add_process_to_execute(collect_refIds)

    if not what_to_collect or CordaObject.Type.ERROR_ANALYSIS in what_to_collect:
        #
        # Collection of Errors
        collect_errors = ErrorAnalysis(Configs.config)
        collect_errors.set_file(file_to_analyse)
        collect_errors.set_element_type(CordaObject.Type.ERROR_ANALYSIS)
        file_to_analyse.add_process_to_execute(collect_errors)

    # 4. Ejecutar procesamiento
    file_to_analyse.pre_analysis()
    file_to_analyse.parallel_processing()

    # Si quieres soportar múltiples roles por party:
    if collect_parties:
        # 1. Obtener todos los roles detectados en el log
        detected_roles = file_to_analyse.get_party_role()

        x500_to_roles = {}
        for role in detected_roles:
            for x500 in (file_to_analyse.get_party_role(role) or []):
                x500_to_roles.setdefault(x500, []).append(role)


        parties = [
            {"name": p.name, "roles": x500_to_roles.get(p.name, [])}
            for p in file_to_analyse.get_all_unique_results(CordaObject.Type.PARTY, True) or []
        ]
        payload["summary"]["total_parties"] = len(parties)
        payload["summary"]["detected_roles"] = detected_roles
        payload["parties"] = parties

    if collect_refIds:
        flows = []
        transactions = []
        for item in file_to_analyse.get_all_unique_results(CordaObject.Type.FLOW_AND_TRANSACTIONS, True) or []:
            ref_id = item.get_reference_id()
            if item.get_type() == "FLOW":
                flows.append(ref_id)
            elif item.get_type() == "TRANSACTION":
                transactions.append(ref_id)

        payload["summary"]["total_transactions"] = len(transactions)
        payload["summary"]["total_flows"]= len(flows)

        payload["flows"] = flows
        payload["transactions"] = transactions

    if special_blocks and  special_blocks.collected_blocks:
        payload["specialblocks"] = {
            "collected_blocktypes_types": special_blocks.get_collected_block_types(),
            "defined_blocktypes": special_blocks.get_defined_block_types(),
            "collected_blocktypes": special_blocks.get_all_content()
        }

    if collect_errors:
        collect_errors.collected_errors = file_to_analyse.get_all_unique_results(CordaObject.Type.ERROR_ANALYSIS)
        # payload["Error-log"] = collect_errors.get_error_category()
        payload['Error-Log'] = collect_errors.get_all_content()
        payload['summary']['Error-log'] =  collect_errors.get_error_summary()


    # 6. Devolver resultado estructurado
    return payload

def get_analysis_for(log_file_path: str, reference_id: str):
    """
    Get specific results from a reference_id
    :param log_file_path: file to analyse
    :param reference_id: Transaction ID or Flow ID
    :return:
    """
    data_dir = Configs.get_config_for('FILE_SETUP.CONFIG.data_dir')

    app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"

    # 1. Configurar archivo
    file_to_analyse = FileManagement(log_file_path, block_size_in_mb=15)

    if not file_to_analyse.state:
        raise ValueError(f"Unable to to read given file due to: {file_to_analyse.state_message}")

    file_to_analyse.discover_file_format()

    def _run_trace_analysis(ref_id, co):
        """
        Función que ejecuta el análisis en un hilo separado
        """
        try:

            # Proceso de análisis
            uml_trace = UMLStepSetup(Configs, co)
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


        if source == 'txn':
            ref_id = ttk.TTkString.toAscii(TTkList_transaction.selectedLabels()[0])


        if not source:
            return

        sref_id = Icons.remove_unicode_symbols(ref_id)
        co = CordaObject.get_object(sref_id)

        if not ref_id or not co:
            write_log("Reference ID not found unable to trace it, please try another", level='WARN')
            return

        _start_trace(sref_id, file_to_analyse, co)
