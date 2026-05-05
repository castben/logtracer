# logtracer/core.py
import hashlib
import threading
from enum import Enum

from drivers.yaml_driver import YamlDataDriver
from object_class import FileManagement, Party
from object_class import BlockExtractor
from get_parties import GetParties
from get_refIds import GetRefIds
from object_class import CordaObject
from object_class import Configs
from object_class import KnownErrors
from error_log_analysis import ErrorAnalysis
import os

from uml import CreateUML, UMLStepSetup, UMLEntityEndPoints


class CoreApi:

    def __init__(self, datainfo):
        self.result = None
        self.datainfo = datainfo
        self.log_file_path = None
        self.log_files = []
        self.what_to_collect = None
        self.references_id = None
        self.file_to_analyse = None
        self.base_data_storage = None

    def object_to_dict(self, obj):
        """
        This method converts an instanced class object into a dictionary to be serialised
        :param obj: any object that need to be serialised
        :return: a dictionary representing given instanced object class
        """
        # 1. Manejo de Enums (¡Nuevo!)
        if isinstance(obj, Enum):
            return obj.value  # O obj.name, según prefieras para el valor

        # 2. Tipos básicos
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj

        # 3. Diccionarios (Mejorado para claves Enum)
        if isinstance(obj, dict):
            return {
                (k.name if isinstance(k, Enum) else str(k)): self.object_to_dict(v)
                for k, v in obj.items()
            }

        # 4. Listas y Tuplas
        if isinstance(obj, (list, tuple)):
            return [self.object_to_dict(x) for x in obj]

        # 5. Objetos personalizados (clases)
        if hasattr(obj, "__dict__"):
            return {
                (k.name if isinstance(k, Enum) else str(k)): self.object_to_dict(v)
                for k, v in vars(obj).items()
                if not callable(v) and not k.startswith('_')
            }

        return str(obj)

    def object_to_dictx(self, obj):
        """
        This method converts an instanced class object into a dictionary to be serialised
        :param obj: any object that need to be serialised
        :return: a dictionary representing given instanced object class
        """
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        if isinstance(obj, dict):
            return {k: self.object_to_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.object_to_dict(x) for x in obj]

        # Aquí aplicamos tu filtro para objetos personalizados
        if hasattr(obj, "__dict__"):
            return {
                k: self.object_to_dict(v)
                for k, v in vars(obj).items()
                if not callable(v) and not k.startswith('_')
            }
        return str(obj) # Último recurso

    def add_log_file(self, logfile):
        """

        :param logfile:
        :return:
        """

        self.log_files.append(logfile)

        self.log_file_path = logfile

    def what_to_collect(self, what_to_collect:CordaObject.Type=None):
        """
        Set what objects to collect from analysis
        :param what_to_collect:
        :return:
        """
        self.what_to_collect = what_to_collect

    def set_references_to_trace(self, references_id):
        """
        A list or a single string for a reference to trace
        :param references_id: a reference to trace, transaction or flow id
        :return:
        """
        self.references_id = references_id

    def get_results(self):
        """
        Return actual payload of all results found
        :return: a dictionary
        """

        return self.result

    def analyze_corda_log(self) -> dict:
        """
        Analiza un archivo de log de Corda y devuelve un diccionario con:
        - parties
        - flows
        - transaction
        - estadísticas (tiempo, conteos, etc.)
        """

        # Always convert it into a proper list
        if isinstance(self.what_to_collect, CordaObject.Type):
            what_to_collect = [self.what_to_collect]

        Configs.load_config()
        _payload = Payload()
        _master_payload = Payload()

        # master_payload = {'log_files': {}}
        file_index = {}
        # payload = {
        #     "summary":{},
        #     "results": {}
        # }

        file_status = {}

        # if self.datainfo:
        #     payload["summary"]["file_info"] = self.datainfo.get_all()

        KnownErrors.configs = Configs
        KnownErrors.initialize()
        data_dir = Configs.get_config_for('FILE_SETUP.CONFIG.data_dir')

        customer_name = self.datainfo.get(DataInfo.Attribute.CUSTOMER) or "unknown"
        customer_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"

        # 1. Configurar archivo
        # need to loop in all assigned files
        for each_file in self.log_files:
            self.file_to_analyse = FileManagement(each_file, block_size_in_mb=15)
            if not self.file_to_analyse.state:
                raise ValueError(f"Unable to to read given file due to: {self.file_to_analyse.state_message}")
            self.log_file_path = each_file
            # payload['summary']['log_file'] = each_file
            # payload["summary"]["file_version_used"] = self.file_to_analyse.logfile_format
            _payload.add('summary.log_file', each_file)
            self.file_to_analyse.discover_file_format()
            _payload.add('summary.file_version_used', self.file_to_analyse.logfile_format)
            special_blocks = None
            collect_parties = None
            collect_refIds = None
            collect_errors = None

            if not self.what_to_collect or CordaObject.Type.SPECIAL_BLOCKS in  self.what_to_collect:
                # 2. Extraer bloques especiales (opcional, si los necesitas en la API)
                special_blocks = BlockExtractor(self.file_to_analyse, Configs.config)
                special_blocks.extract()

            if not self.what_to_collect or CordaObject.Type.PARTY in self.what_to_collect:
                # 3. Configurar recolectores
                #
                # Party collection
                collect_parties = GetParties(Configs)
                collect_parties.set_file(self.file_to_analyse)
                collect_parties.set_element_type(CordaObject.Type.PARTY)
                self.file_to_analyse.add_process_to_execute(collect_parties)

            if not self.what_to_collect or CordaObject.Type.FLOW_AND_TRANSACTIONS in self.what_to_collect:
                #
                # Transactions and Flows collection
                collect_refIds = GetRefIds(Configs)
                collect_refIds.set_file(self.file_to_analyse)
                collect_refIds.set_element_type(CordaObject.Type.FLOW_AND_TRANSACTIONS)
                self.file_to_analyse.add_process_to_execute(collect_refIds)

            if not self.what_to_collect or CordaObject.Type.ERROR_ANALYSIS in self.what_to_collect:
                #
                # Collection of Errors
                collect_errors = ErrorAnalysis(Configs.config)
                collect_errors.set_file(self.file_to_analyse)
                collect_errors.set_element_type(CordaObject.Type.ERROR_ANALYSIS)
                self.file_to_analyse.add_process_to_execute(collect_errors)

            # 4. Ejecutar procesamiento
            self.file_to_analyse.pre_analysis()
            self.file_to_analyse.parallel_processing()

            # Si quieres soportar múltiples roles por party:
            if collect_parties:
                # 1. Obtener todos los roles detectados en el log
                detected_roles = self.file_to_analyse.get_party_role()

                x500_to_roles = {}
                for role in detected_roles:
                    for x500 in (self.file_to_analyse.get_party_role(role) or []):
                        x500_to_roles.setdefault(x500, []).append(role)

                parties = [
                    {"name": p.name, "roles": x500_to_roles.get(p.name, [])}
                    for p in self.file_to_analyse.get_all_unique_results(CordaObject.Type.PARTY, True) or []
                ]
                # payload["summary"]["total_parties"] = len(parties)
                # payload["summary"]["detected_roles"] = detected_roles
                # payload["results"][CordaObject.Type.PARTY.value] = parties

                _payload.add('summary.total_parties', len(parties))
                _payload.add('summary.detected_roles', detected_roles)
                _payload.add(f'results.{CordaObject.Type.PARTY.value}', parties)

            if collect_refIds:
                flows = {}
                transactions = {}
                # Transform CordaObject into a dictionary for serialization
                for item in self.file_to_analyse.get_all_unique_results(CordaObject.Type.FLOW_AND_TRANSACTIONS, True) or []:
                    ref_id = item.get_reference_id()
                    item_dict = self.object_to_dict(item)
                    if item.get_type() == "FLOW":
                        flows[f'{ref_id}']=item_dict
                    elif item.get_type() == "TRANSACTION":
                        transactions[f'{ref_id}'] =item_dict
                # Put all content of flows and transactions into same bucket; each corda object has its type and can be
                # easily identified.
                fnt = {**flows, **transactions}
                # payload["summary"]["total_transactions"] = len(transactions)
                # payload["summary"]["total_flows"]= len(flows)
                # payload["results"][CordaObject.Type.FLOW_AND_TRANSACTIONS.value] = fnt
                _payload.add('summary.total_transactions', len(transactions))
                _payload.add('summary.total_flows', len(flows))
                _payload.add(f'results.{CordaObject.Type.FLOW_AND_TRANSACTIONS.value}', fnt)

            if special_blocks and  special_blocks.collected_blocks:
                # payload["results"][CordaObject.Type.SPECIAL_BLOCKS.value] = {
                #     "collected_blocktypes_types": special_blocks.get_collected_block_types(),
                #     "defined_blocktypes": special_blocks.get_defined_block_types(),
                #     "collected_blocktypes": special_blocks.get_all_content()
                # }
                # payload['summary'][CordaObject.Type.SPECIAL_BLOCKS.value] = special_blocks.get_collected_block_types()
                _payload.add(f'results.{CordaObject.Type.SPECIAL_BLOCKS.value}.collected_blocktypes_types', special_blocks.get_collected_block_types())
                _payload.add(f'results.{CordaObject.Type.SPECIAL_BLOCKS.value}.defined_blocktypes', special_blocks.get_defined_block_types())
                _payload.add(f'results.{CordaObject.Type.SPECIAL_BLOCKS.value}.collected_blocktypes',special_blocks.get_all_content())
                _payload.add(f'summary.{CordaObject.Type.SPECIAL_BLOCKS.value}', special_blocks.get_collected_block_types())

            if collect_errors:
                collect_errors.collected_errors = self.file_to_analyse.get_all_unique_results(CordaObject.Type.ERROR_ANALYSIS)
                # payload["Error-log"] = collect_errors.get_error_category()
                # payload["results"][CordaObject.Type.ERROR_ANALYSIS.value] = collect_errors.get_all_content()
                # payload['summary'][CordaObject.Type.ERROR_ANALYSIS.value] = collect_errors.get_error_summary()
                _payload.add(f'results.{CordaObject.Type.ERROR_ANALYSIS.value}', collect_errors.get_all_content())
                _payload.add(f'summary.{CordaObject.Type.ERROR_ANALYSIS.value}', collect_errors.get_error_summary())
                file_status['error_analysis'] = 'complete'
            else:
                file_status['error_analysis'] = 'pending'

            file_index[self.file_to_analyse.file_id] = self.log_file_path
            # payload['summary']['file_info'] = {
            #     'processed_timestamp': self.file_to_analyse.load_timestamp,
            #     'file_size': self.file_to_analyse.file_size,
            #     'file_status': file_status,
            #     'time_spent': self.file_to_analyse.time_spent
            # }
            _payload.add('summary.file_info.processed_timestamp', self.file_to_analyse.load_timestamp)
            _payload.add('summary.file_info.file_size', self.file_to_analyse.file_size)
            _payload.add('summary.file_info.file_status', file_status)
            _payload.add('summary.file_info.time_spent', self.file_to_analyse.time_spent)

            # master_payload['log_files'][self.file_to_analyse.file_id] = payload
            _master_payload.add(f'log_files.{self.file_to_analyse.file_id}', _payload.to_dict())
            # 6. Devolver resultado estructurado
        self.datainfo.set('log_files', file_index)
        # master_payload['ticket_details'] = self.datainfo.get_all()
        _master_payload.add('ticket_details', self.datainfo.get_all())


        self.result = _master_payload.to_dict()


        return self.result

    def save_analysis(self, object_type=None, driver=None):
        """
        Store analysis.
        :param object_type: What to persist from API response, if NONE will save all data collected otherwise
        will persist only object given
        :param driver: driver to use to persist data by default will be YAML
        :return:
        """

        if not object_type:
            object_type = [
                CordaObject.Type.FLOW_AND_TRANSACTIONS,
                CordaObject.Type.PARTY,
                CordaObject.Type.ERROR_ANALYSIS,
                CordaObject.Type.SPECIAL_BLOCKS,
                CordaObject.Type.UML_STEPS
            ]

        if not isinstance(object_type, list):
            object_type = [object_type]

        if not driver or driver=="YAML":
            customer = self.datainfo.get(DataInfo.Attribute.CUSTOMER) or "unknown"
            ticket = self.datainfo.get(DataInfo.Attribute.TICKET) or "unknown"

            storage = YamlDataDriver()

            if 'log_files' in self.result:
                for file_id in  self.result['log_files']:
                    summary = {
                        "analysis": self.result['log_files'][file_id]["summary"]
                    }
                    storage.connect(data_dir= f"./data/storage/{customer}/{ticket}/{file_id}",
                                    summary=summary,
                                    ticket_details=self.result['ticket_details'])

                    for each_object in object_type:
                        # Serialise Error analysis
                        if each_object == CordaObject.Type.ERROR_ANALYSIS and each_object.value in self.result['log_files'][file_id]["results"]:
                            category = self.result['log_files'][file_id]["results"][each_object.value]
                            for each_item_category in category:
                                for each_error in category[each_item_category]:
                                    error_list = category[each_item_category][each_error]
                                    for each_item in error_list:
                                        if 'category' not in each_item:
                                            each_item['category'] = each_item_category
                                        if 'reference_id' not in each_item:
                                            each_item['reference_id'] = each_item['line_number']

                                        storage.save_error(each_item)

                        # Serialise Party data
                        if each_object == CordaObject.Type.PARTY and each_object.value in self.result['log_files'][file_id]["results"]:
                            for each_party in self.result['log_files'][file_id]['results'][each_object.value]:
                                party = Party(each_party['name'])
                                party.set_corda_role('/'.join(each_party['roles']))
                                # storage.save_party(each_party)
                                storage.save_party(party)

                        # Serialise Flow and Transaction data
                        if each_object == CordaObject.Type.FLOW_AND_TRANSACTIONS and each_object.value in self.result['log_files'][file_id]["results"]:
                            object_list = self.result['log_files'][file_id]['results'][each_object.value]
                            for each_item in object_list:
                                # co = CordaObject()
                                # co.from_dict(object_list[each_item])
                                storage.save_corda_object(object_list[each_item])

                        # Serialise SpecialBlocks
                        if each_object == CordaObject.Type.SPECIAL_BLOCKS and each_object.value in self.result['log_files'][file_id]["results"]:
                            block_type_list = self.result['log_files'][file_id]['results'][CordaObject.Type.SPECIAL_BLOCKS.value]['collected_blocktypes']
                            for each_block_type in block_type_list:
                                for each_block in block_type_list[each_block_type]:
                                    storage.save_block_item(block_type_list[each_block_type][each_block])

                        # Serialise UMLSteps
                        if each_object == CordaObject.Type.UML_STEPS and each_object.value in self.result['log_files'][file_id]["results"]:
                            uml_steps = self.result['log_files'][file_id]['results'][CordaObject.Type.UML_STEPS.value]

                    storage.disconnect()

    def load_ticket_details(self):
        """

        :param datainfo:
        :return:
        """
        customer = self.datainfo.get(DataInfo.Attribute.CUSTOMER)
        ticket = self.datainfo.get(DataInfo.Attribute.TICKET)
        storage = YamlDataDriver()
        # connect to get tickets details
        ticket_details=storage.connect(data_dir=f'./data/storage/{customer}/{ticket}')

        return ticket_details

    def trace_analysis(self, logfile_id, reference_id):
        """
        Generate corresponding UML representation from given logfile and reference_id
        :param logfile_id: logfile_id to trace
        :param reference_id: reference to trace
        :return: UML representation or None otherwise
        """
        storage = YamlDataDriver()
        customer = self.datainfo.get(DataInfo.Attribute.CUSTOMER)
        ticket = self.datainfo.get(DataInfo.Attribute.TICKET)
        ticket_details = self.load_ticket_details()
        saved_data = storage.connect(data_dir=f'./data/storage/{customer}/{ticket}/{logfile_id}')
        data_analysis = saved_data.load_data()

        file_check = FileManagement(ticket_details['log_files'][logfile_id])
        file_check.pre_analysis()
        file_check.discover_file_format()

        # Load all recovered data into FileManagement class
        FileManagement.add_list(elements_dict=data_analysis)

        # Define default entity object endpoints...
        UMLEntityEndPoints.load_default_endpoints()

        # using loaded data from disk, identify which roles are assigned on each party
        file_check.identify_roles()

        uml_trace = UMLStepSetup(Configs,
                                 data_analysis[CordaObject.Type.FLOW_AND_TRANSACTIONS.value][reference_id])
        uml_trace.file=file_check
        # for each_item in data_analysis['flow&transactions']:
        uml_trace.parallel_process()

        # Add results into unique_results on file management.

        c_uml = CreateUML(uml_trace.cordaobject, file_check)

        FileManagement.add_list(elements_dict={CordaObject.Type.UML_STEPS.value:c_uml.corda_object.uml_steps})

        results = self.object_to_dict(FileManagement.unique_results)


        # self.save_analysis()
        pass



    def get_file_hash(self, chunk_size=65536):
        """
        Genera un hash SHA-256 del contenido del archivo.
        Si el contenido es idéntico, el hash será idéntico.
        """
        hasher = hashlib.sha256()

        with open(self.log_file_path, 'rb') as f:
            # Leemos el archivo en bloques (chunks) para no cargar logs gigas en RAM
            while chunk := f.read(chunk_size):
                hasher.update(chunk)

        # 16 caracteres son más que suficientes para evitar colisiones en este contexto
        return hasher.hexdigest()[:16]

    # def get_analysis_for(self, log_file_path: str, reference_id: str):
    #     """
    #     Get specific results from a reference_id
    #     :param log_file_path: file to analyse
    #     :param reference_id: Transaction ID or Flow ID
    #     :return:
    #     """
    #     data_dir = Configs.get_config_for('FILE_SETUP.CONFIG.data_dir')
    #
    #     app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"
    #
    #     # 1. Configurar archivo
    #     file_to_analyse = FileManagement(log_file_path, block_size_in_mb=15)
    #
    #     if not file_to_analyse.state:
    #         raise ValueError(f"Unable to to read given file due to: {file_to_analyse.state_message}")
    #
    #     file_to_analyse.discover_file_format()
    #
    #     def _run_trace_analysis(ref_id, co):
    #         """
    #         Función que ejecuta el análisis en un hilo separado
    #         """
    #         try:
    #
    #             # Proceso de análisis
    #             uml_trace = UMLStepSetup(Configs, co)
    #             uml_trace.file = file_to_analyse
    #             uml_trace.parallel_process(co)
    #
    #             c_uml = CreateUML(co, file_to_analyse)
    #             script_file = c_uml.generate_uml_pages(
    #                 client_name=self.customer,
    #                 ticket=self.ticket,
    #                 output_prefix=ref_id
    #             )
    #
    #             if not script_file:
    #                 write_log('No useful information was related to this reference id', level='WARN')
    #             else:
    #                 write_log("\n".join(script_file))
    #                 success = CreateUML.render_uml(file=script_file)
    #                 if success:
    #                     self.add_generated_file(ref_id, script_file)
    #
    #             write_log('=============================================================================')
    #
    #         except Exception as e:
    #             write_log(f"Error during analysis: {str(e)}", level='ERROR')
    #
    #     def _start_trace(ref_id, file_to_analyse, co):
    #         """
    #          Método que lanza el trace en un hilo separado
    #         """
    #         # Mostrar mensaje de inicio en UI
    #
    #
    #
    #         write_log(f"Starting trace analysis for {ref_id}...")
    #
    #         # Crear y lanzar el hilo
    #         analysis_thread = threading.Thread(
    #             target=_run_trace_analysis,
    #             args=(ref_id, file_to_analyse, co),
    #             name=f"AnalysisThread-{ref_id}",
    #             daemon=True  # El hilo se cerrará cuando termine la aplicación
    #         )
    #         analysis_thread.start()
    #
    #         # Opcional: guardar referencia al hilo para poder monitorearlo
    #         # self.active_threads.append(analysis_thread)
    #
    #     def _trace(source):
    #         """
    #         Trace
    #         :param source: reference id for the object to trace
    #         :return:
    #         """
    #         global file_to_analyse
    #
    #         if not file_to_analyse.get_party_role('log_owner'):
    #             write_log("Unable to perform a tracing, 'log_owner' role is not being assigned...", level="WARN")
    #             write_log("You will need to manually setup it up, otherwise will not be possible to trace any item...", level="WARN")
    #             self.tk_popup_window(origen=TTkButton_flow_trace, message="Unable to continue role:\n 'log_owner' hasn't been assigned.")
    #             return
    #
    #         if source == 'flow':
    #             ref_id = ttk.TTkString.toAscii(TTkList_flow.selectedLabels()[0])
    #
    #
    #         if source == 'txn':
    #             ref_id = ttk.TTkString.toAscii(TTkList_transaction.selectedLabels()[0])
    #
    #
    #         if not source:
    #             return
    #
    #         sref_id = Icons.remove_unicode_symbols(ref_id)
    #         co = CordaObject.get_object(sref_id)
    #
    #         if not ref_id or not co:
    #             write_log("Reference ID not found unable to trace it, please try another", level='WARN')
    #             return
    #
    #         _start_trace(sref_id, file_to_analyse, co)
    # def uml_analysis(self, ref_id, file_to_analyse:FileManagement, co):
    #     """
    #     Run UML analysis and tracing of a corda object(Transaction or Flow)
    #     :return:
    #     """
    #     # Proceso de análisis
    #     uml_trace = UMLStepSetup(Configs, co)
    #     uml_trace.file = file_to_analyse
    #     uml_trace.parallel_process(co)
    #     c_uml = CreateUML(co, file_to_analyse)
    #     script_file = c_uml.generate_uml_pages(
    #         client_name=self.datainfo.get(DataInfo.Attribute.CUSTOMER),
    #         ticket=self.datainfo.get(DataInfo.Attribute.TICKET),
    #         output_prefix=ref_id
    #     )
    #
    #     if not script_file:
    #        pass
    #     else:
    #         success = CreateUML.render_uml(file=script_file)
    #         if success:
    #            pass

    def list_current_logs(self):
        """
        Return a list of all actual pre-analysed logs
        :return:
        """

        storage = YamlDataDriver()
        # data_path = './data/storage'
        storage.connect()
        _payload = Payload()
        if self.datainfo and self.datainfo.get(DataInfo.Attribute.CUSTOMER):
            customer = self.datainfo.get(DataInfo.Attribute.CUSTOMER)
            # if customer:
            #     storage.connect(data_dir=f'./data/storage/{customer}')


            return storage.get_customer_tickets(customer)

        return storage.get_customer_tickets()

class DataInfo:
    class Attribute(Enum):
        """
        Allowed Types to set
        """

        CUSTOMER = 'customer'
        TICKET = 'ticket'
        CORDA_VERSION = "corda_version"
        JAVA_VERSION = "java_version"
        OS = "operating_system"
        RUNNING_ON_DOCKER = "running_on_docker"
        RUNNING_ON_K8S = "running_on_k8s"
        K8S_VERSION = "k8s_version"
        DOCKER_VERSION = "docker_version"
        ENVIRONMENT = "environment"
        DESCRIPTION = "description"
        ISSUE = "issue"
        CUSTOMER_PATH = "customer_path"
        TICKET_STATUS = "ticket_status"

    def __init__(self):
        """
        Data info structure, to hold information about customer or ticket being handled.
        """

        self.data = {}

    def set(self, key, value):
        """
        Set a data attribute
        :param key: attribute name
        :param value: attribute value
        :return: void
        """
        if isinstance(key, DataInfo.Attribute):
            selement_type = key.value
            key = selement_type

        self.data[key] = value

    def get(self, key):
        """
        return an attribute from data info dictionary
        :param key: attribute name
        :return: value if attribute exist, None otherwise
        """

        if isinstance(key, DataInfo.Attribute):
            selement_type = key.value
            key = selement_type

        if key in self.data:
            return self.data[key]

        return None

    def get_all(self):
        """
        Get a dictionary with all attributes stored.
        :return: dictionary
        """

        return self.data

class Payload:
    def __init__(self, data=None):
        # Si recibimos data (ej. de la API), la cargamos; si no, empezamos de cero
        self._data = data if data is not None else {}

    def add(self, path: str, value):
        """Asigna un valor creando la ruta si no existe."""
        parts = path.split('.')
        # Navegamos hasta el penúltimo elemento
        target = self._get_or_create_path('.'.join(parts[:-1]))
        # El último elemento es la clave final
        target[parts[-1]] = value

    def get(self, path: str, default=None):
        """Extrae un valor usando una ruta de puntos. Retorna default si no existe."""
        current = self._data
        for part in path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def _get_or_create_path(self, path: str):
        if not path:
            return self._data
        current = self._data
        for part in path.split('.'):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        return current

    def to_dict(self):
        return self._data