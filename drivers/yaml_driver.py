# drivers/yaml_driver.py
import re
from collections import OrderedDict

import yaml
import os
from pathlib import Path, PosixPath
from typing import Optional, List, Dict

from numpy.distutils.fcompiler import none

from data_interface import DataDriver
from log_handler import write_log
from object_class import CordaObject, Party
from object_class import BlockItems
from object_class import Error
from uml import UMLStep


class YamlDataDriver(DataDriver):
    """
    Driver de datos usando archivos YAML basado en tus estructuras
    """

    def __init__(self):
        self.data_dir = None
        self.entities_dir = None
        self.parties_dir = None
        self.blocks_dir = None
        self.errors_dir = None
        self.summary = None
        self.ticket_details = None
        self.logfile_hash = None
        self.datainfo = None
        self.file_id = None
        self.read_only = False
        self.cache = {}  # Opcional: cache para mejorar rendimiento

    def configure_dirs(self, dir_setup):
        """
        Configure access to all data
        :param dir_setup:
        :return:
        """

        if not isinstance(dir_setup, PosixPath):
            dir_setup = PosixPath(dir_setup)

        self.entities_dir = dir_setup / "entities"
        self.parties_dir = dir_setup / "parties"
        self.blocks_dir = dir_setup / "blocks"
        self.errors_dir = dir_setup / "errors"

    def connect(self, **config):
        """
        Configurar directorio de datos
        config = {
            'data_dir': '/ruta/a/data/',
            'cache_enabled': True
        }
        """
        if not config.get('data_dir'):
            only_list = True
        else:
            only_list = False
        customer = None
        ticket = None
        self.datainfo = config.get('datainfo', None)
        self.file_id = config.get('file_id')
        self.data_dir = Path(config.get('data_dir', './data/storage'))
        self.summary = config.get("summary", None)
        self.ticket_details = config.get("ticket_details", None)

        if self.datainfo:
            only_list = False
            ticket = self.datainfo.get('ticket')
            customer = self.datainfo.get('customer')
            # self.data_dir = f'./data/storage/{self.datainfo.get("customer")}/{self.datainfo.get("ticket")}'

        if customer and ticket and  os.path.exists(f'{self.data_dir}/{customer}/{ticket}/ticket_details.yaml'):
            # Verify if ticket details exist, if it does, then no dir creation is required
            with open(f'{self.data_dir}/{customer}/{ticket}/ticket_details.yaml', 'r') as fh_td:
                self.ticket_details = yaml.safe_load(fh_td)
        else:
            if self.datainfo:
                self.ticket_details = self.datainfo.get_all()

        if self.file_id and ticket and customer and os.path.exists(f'{self.data_dir}/{customer}/{ticket}/{self.file_id}/summary.yaml'):
            self.configure_dirs(self.data_dir)
            with open(f'{self.data_dir}/{customer}/{ticket}/{self.file_id}/summary.yaml', 'r') as fh_sm:
                self.summary = yaml.safe_load(fh_sm)

        if not only_list:
            # Crear directorios
            if self.file_id and ticket and customer:
                self.configure_dirs(f'{self.data_dir}/{customer}/{ticket}/{self.file_id}')
                for dir_path in [self.entities_dir, self.parties_dir, self.blocks_dir, self.errors_dir]:
                    if not os.path.exists(dir_path):
                        dir_path.mkdir(parents=True, exist_ok=True)

        if self.read_only:
            return self

        if self.summary:
           self.save_summary()

        if config.get("ticket_details"):
            self.save_details()

        return self


    def load_data(self):
        """
        Load all saved data
        :return:
        """
        content = {
            CordaObject.Type.FLOW_AND_TRANSACTIONS.value: {},
            CordaObject.Type.PARTY.value: {},
            CordaObject.Type.ERROR_ANALYSIS.value: {},
            CordaObject.Type.SPECIAL_BLOCKS.value: {},
        }
        # Cargar CordaObjects
        for entity_file in self.entities_dir.glob("*.yaml"):
            ref_id = entity_file.stem.replace("entity_", "")
            content[CordaObject.Type.FLOW_AND_TRANSACTIONS.value][f"{ref_id}"] = self.get_corda_object_by_id(ref_id)

        # Cargar Parties
        for party_file in self.parties_dir.glob("*.yaml"):
            party_name = party_file.stem
            content[CordaObject.Type.PARTY.value][f"{party_name}"] = self.get_party_by_name(party_name)

        # Cargar Errores

        for each_category in  self.get_errors_category_list():
            if each_category not in content[CordaObject.Type.ERROR_ANALYSIS.value]:
                content[CordaObject.Type.ERROR_ANALYSIS.value][each_category] = {}

                for each_error_type in self.get_error_type_list(each_category):
                    if each_error_type not in content[CordaObject.Type.ERROR_ANALYSIS.value][each_category]:
                        content[CordaObject.Type.ERROR_ANALYSIS.value][each_category][each_error_type] = []

                    content[CordaObject.Type.ERROR_ANALYSIS.value][each_category][each_error_type].append(self.get_errors_by_category_type(each_category,each_error_type))


        # Cargar bloques especiales
        content[CordaObject.Type.SPECIAL_BLOCKS.value] = self.get_block_type_list()

        return content

    def _load_cache(self):
        """Cargar datos en memoria para acceso rápido"""
        # Cargar CordaObjects
        for entity_file in self.entities_dir.glob("*.yaml"):
            ref_id = entity_file.stem.replace("entity_", "")
            self.cache[f"entity_{ref_id}"] = self.get_corda_object_by_id(ref_id)

        # Cargar Parties
        for party_file in self.parties_dir.glob("*.yaml"):
            party_name = party_file.stem
            self.cache[f"party_{party_name}"] = self.get_party_by_name(party_name)


    def get_customer_tickets(self, customer=None):
        storage = Path(self.data_dir)
        inventory = {"customer": {}}

        def get_tickets(customer_dir):
            """
            Get all tickets under customer name
            :param customer_dir: customer dir object (path) name to look at
            :return: list of tickets and description
            """
            ticket_list = {}
            # Iteramos sobre los tickets de cada cliente
            for ticket_dir in customer_dir.iterdir():
                if ticket_dir.is_dir():
                    ticket_id = ticket_dir.name

                    # Buscamos el archivo summary.yaml para obtener la descripción
                    ticket_details = ticket_dir / "ticket_details.yaml"
                    description = "No description available"
                    log_files = None
                    if ticket_details.exists():
                        try:
                            with open(ticket_details, 'r') as f:
                                data = yaml.safe_load(f)
                                # Ajusta 'description' según la clave real en tu YAML
                                description = data['description']
                                log_files = data['log_files']
                        except Exception:
                            description = "Error reading summary"

                    if not log_files:
                        write_log("Unable to collect summary information for given file id/ticket combination", level='ERROR')
                        return None

                    ticket_list[ticket_id] = {
                        'description': description,
                        'log_files': log_files
                    }
                    # inventory["customer"][customer_name]["tickets"][ticket_id] = description
            return ticket_list

        # Iteramos sobre los directorios de clientes
        if not customer:
            for customer_dir in storage.iterdir():
                if customer_dir.is_dir():
                    customer_name = customer_dir.name
                    # inventory["customer"][customer_name] = {"tickets": {}}
                    inventory["customer"][customer_name] = {}
                    inventory["customer"][customer_name]['tickets'] = get_tickets(customer_dir)
        else:
            if not os.path.exists(f"{self.data_dir}/{customer}"):
                return {'Error': f'{customer} does not exist' }
            customer_dir = Path(f"{self.data_dir}/{customer}")
            # ticket_list = get_tickets(customer_dir)
            inventory["customer"][customer] = {}
            inventory["customer"][customer]['tickets'] = get_tickets(customer_dir)


        return inventory

    def get_ticket_logs(self):
        pass

    def get_ticket_details(self):
        """

        :return:
        """

        return self.ticket_details

    def get_summary(self):
        """
        Return summary
        :return: returns a dictionary with all summary information about log file
        """

        return self.summary

    # --- CORDAOBJECT OPERATIONS ---

    def get_corda_object_by_id(self, ref_id: str) -> Optional[CordaObject]:
        entity_file = self.entities_dir / f"entity_{ref_id}.yaml"

        if entity_file.exists():
            with open(entity_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return self._dict_to_corda_object(data)
        return None

    def get_corda_objects_by_type(self, obj_type: str) -> List[CordaObject]:
        objects = []
        for entity_file in self.entities_dir.glob("entity_*.yaml"):
            with open(entity_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data.get('type') == obj_type:
                    objects.append(self._dict_to_corda_object(data))
        return objects

    def get_corda_objects_by_time_range(self, start_time: str, end_time: str) -> List[CordaObject]:
        objects = []
        for entity_file in self.entities_dir.glob("entity_*.yaml"):
            with open(entity_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                timestamp = data.get('timestamp')
                if timestamp and start_time <= timestamp <= end_time:
                    objects.append(self._dict_to_corda_object(data))
        return objects

    def get_corda_objects_by_participant(self, party_name: str) -> List[CordaObject]:
        objects = []
        for entity_file in self.entities_dir.glob("entity_*.yaml"):
            with open(entity_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                # Asumiendo que 'references' contiene parties
                if party_name in str(data.get('references', {})):
                    objects.append(self._dict_to_corda_object(data))
        return objects

    def save_corda_object(self, corda_obj):
        """
        Save corda object data as JSON file
        :param corda_obj: either a CordaObject class or a dictionary
        :return:
        """

        if isinstance(corda_obj, CordaObject ):
            data = self._corda_object_to_dict(corda_obj)
        else:
            data = corda_obj
        entity_file = self.entities_dir / f"entity_{data['reference_id']}.yaml"
        with open(entity_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # Actualizar cache
        if hasattr(self, 'cache'):
            self.cache[f"entity_{data['reference_id']}"] = corda_obj

    def save_corda_objects(self, corda_objects: List[CordaObject]):
        for obj in corda_objects:
            self.save_corda_object(obj)

    # --- PARTY OPERATIONS ---

    def get_all_parties(self) -> List[Party]:
        parties = []
        for party_file in self.parties_dir.glob("*.yaml"):
            with open(party_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                parties.append(self._dict_to_party(data))
        return parties

    def get_party_by_name(self, party_name: str) -> Optional[Party]:
        party_file = self.parties_dir / f"{party_name}.yaml"
        if party_file.exists():
            with open(party_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return self._dict_to_party(data)
        return None

    def save_party(self, party):

        if isinstance(party, Party):
            data = self._party_to_dict(party)
        else:
            data = party
        party_file = self.parties_dir / f"{data['name']}.yaml"
        with open(party_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    # --- BLOCK ITEMS OPERATIONS ---

    def get_block_type_list(self):
        """
        Return all block type list
        :return:
        """

        block_type_list = {}
        for block_file in self.blocks_dir.glob(f"block*.yaml"):
            block_type = re.search(r'block_[0-9a-zA-Z-]+_([a-zA-Z-_]+)', block_file.stem)
            if block_type and block_type.group(1) not in block_type_list:
                block_type_list[block_type.group(1)] = {}

        for each_block_type in block_type_list.keys():
            for each_block in self.get_block_items_by_type(each_block_type):
                block_type_list[each_block_type][each_block.reference] = each_block

        return block_type_list

    def get_block_items_by_type(self, block_type: str) -> List[BlockItems]:
        blocks = []
        for block_file in self.blocks_dir.glob(f"block_*_{block_type}.yaml"):
            with open(block_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                blocks.append(self._dict_to_block_item(data))
        return blocks

    def get_block_items_by_reference(self, ref_id: str) -> List[BlockItems]:
        blocks = []
        for block_file in self.blocks_dir.glob(f"block_{ref_id}_*.yaml"):
            with open(block_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                blocks.append(self._dict_to_block_item(data))
        return blocks

    def save_summary(self):
        """
        Save summary for received payload
        :return:
        """
        with open(f"{self.data_dir}/{self.ticket_details.get('customer')}/{self.ticket_details.get('ticket')}/{self.file_id}/summary.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(self.summary, f, allow_unicode=True, default_flow_style=False)

    def save_details(self):
        """
        Save ticket details for received payload
        :return:
        """
        with open(f"{self.data_dir}/{self.datainfo.get('customer')}/{self.datainfo.get('ticket')}/ticket_details.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(self.ticket_details, f, allow_unicode=True, default_flow_style=False)

    def save_block_item(self, block_item):

        if isinstance(block_item, BlockItems):
            data = self._block_item_to_dict(block_item)
        else:
            data = block_item

        block_file = self.blocks_dir / f"block_{data['reference']}_{data['type']}.yaml"
        with open(block_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def save_uml_step(self, uml_step):
        """
        Save uml steps
        :param uml_step: uml_step in dictionary format
        :return:
        """

        if isinstance(uml_step, UMLStep):
            data = self.object_to_dict(uml_step)
        else:
            data = uml_step

        if isinstance(data, list):
            for index, each_step in enumerate(data):
                uml_step_file = self.uml_steps_dir / f'umlstep_{each_step["reference"]}_{index}.yaml'
                with open(uml_step_file, 'w', encoding='utf-8') as f:
                    yaml.dump(each_step, f, allow_unicode=True, default_flow_style=False)
        else:
            uml_step_file = self.uml_steps_dir / f'umlstep_{data["reference"]}.yaml'
            with open(uml_step_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        pass

    # --- ERROR OPERATIONS ---

    def get_errors_category_list(self) -> List[str]:
        """

        :return:
        """
        category_list = []
        for each_error_file in self.errors_dir.glob(f"error_*.yaml"):
            category = re.search(r'error_([a-zA-Z]+)_.*', each_error_file.stem)
            if category and category.group(1) not in category_list:
                category_list.append(category.group(1))

        return category_list


    def get_error_type_list(self, category: str) -> List[str]:
        """
        Return all error types unde a category
        :param category:
        :return:
        """
        type_list = []
        for error_file in self.errors_dir.glob(f"error_{category}_*.yaml"):
            error_type = re.search(r'error_[a-zA-Z-]+_([a-zA-Z-]+).*', error_file.stem)
            if error_type and error_type.group(1) and not error_type.group(1) in type_list:
                type_list.append(error_type.group(1))

        return type_list

    def get_errors_by_category(self, category: str) -> List[Error]:
        errors = []
        for error_file in self.errors_dir.glob(f"error_{category}_*.yaml"):
            with open(error_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                errors.append(self._dict_to_error(data))
        return errors

    def get_errors_by_category_type(self, category:str, error_type):
        """

        :param category:
        :param error_type:
        :return:
        """
        errors = []
        for error_file in self.errors_dir.glob(f"error_{category}_{error_type}_*.yaml"):
            with open(error_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                errors.append(self._dict_to_error(data))
                # errors.append(data)

        return errors

    def get_errors_by_type(self, error_type: str) -> List[Error]:
        errors = []
        for error_file in self.errors_dir.glob(f"error_*_{error_type}.yaml"):
            with open(error_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                errors.append(self._dict_to_error(data))
        return errors

    def get_all_errors(self) -> List[Error]:
        errors = []
        for error_file in self.errors_dir.glob("error_*.yaml"):
            with open(error_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                errors.append(self._dict_to_error(data))
        return errors

    def save_error(self, error):

        if isinstance(error, Error):
            data = self._error_to_dict(error)
        else:
            data = error

        error_file = self.errors_dir / f"error_{data['category']}_{data['type']}_{data['reference_id']}.yaml"
        with open(error_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def save_object(self, object_to_save):
        """
        Save serialised UML steps
        :param object_to_save: instanced object class
        :return: a representation of instanced objec as a dictionary
        """

        if isinstance(object_to_save, UMLStep) or \
            isinstance(object_to_save, Error) or \
                isinstance(object_to_save, Party):
            serialised_dict = self.object_to_dict(object_to_save)
        else:
            serialised_dict = object_to_save

        return serialised_dict

    def disconnect(self):
        # No hay conexión persistente en YAML
        pass

    # --- SERIALIZACIÓN/DESERIALIZACIÓN ---

    def _corda_object_to_dict(self, obj: CordaObject) -> Dict:
        """Convierte CordaObject a diccionario serializable"""
        return {
            'reference_id': obj.reference_id,
            'type': obj.type,
            'line_number': obj.line_number,
            'timestamp': obj.timestamp,
            'error_level': obj.error_level,
            'data': obj.data,
            'references': dict(obj.references),  # Convertir OrderedDict a dict
            'uml_steps': self._serialize_uml_steps(obj.uml_steps),
        }

    def _dict_to_corda_object(self, data: Dict) -> CordaObject:
        """Convierte diccionario a CordaObject"""
        obj = CordaObject()
        obj.reference_id = data.get('reference_id')
        obj.type = data.get('type')
        obj.line_number = data.get('line_number')
        obj.timestamp = data.get('timestamp')
        obj.error_level = data.get('error_level')
        obj.data = data.get('data', {})
        obj.references = OrderedDict(data.get('references', {}))
        obj.uml_steps = self._deserialize_uml_steps(data.get('uml_steps', {}))
        return obj

    def _party_to_dict(self, party: Party) -> Dict:
        return {
            'name': party.name,
            'reference_id': party.reference_id,
            'role': party.role,
            'type': party.type,
            'corda_role': party.corda_role,
            'default_endpoint': party.default_endpoint,
            'alternate_names': party.alternate_names,
            'original_string': party.original_string,
            'attributes': party.attributes,
        }

    def _dict_to_party(self, data: Dict) -> Party:
        party = Party(x500name=data.get('name'))
        party.reference_id = data.get('reference_id')
        party.role = data.get('role', '')
        party.type = data.get('type', 'Party')
        party.corda_role = data.get('corda_role', [])
        party.default_endpoint = data.get('default_endpoint')
        party.alternate_names = data.get('alternate_names', [])
        party.original_string = data.get('original_string')
        party.attributes = data.get('attributes', {})
        return party

    def _block_item_to_dict(self, block: BlockItems) -> Dict:
        return {
            'timestamp': block.timestamp,
            'line_number': block.line_number,
            'reference': block.reference,
            'content': block.content,
            'type': block.type,
        }

    def _dict_to_block_item(self, data: Dict) -> BlockItems:
        block = BlockItems()
        block.timestamp = data.get('timestamp')
        block.line_number = data.get('line_number')
        block.reference = data.get('reference')
        block.content = data.get('content', [])
        block.type = data.get('type')
        return block

    def _error_to_dict(self, error: Error) -> Dict:
        return {
            'reference_id': error.reference_id,
            'timestamp': error.timestamp,
            'log_line': error.log_line,
            'line_number': error.line_number,
            'type': error.type,
            'category': error.category,
        }

    def _dict_to_error(self, data: Dict) -> Error:
        error = Error()
        error.reference_id = data.get('reference_id')
        error.timestamp = data.get('timestamp')
        error.log_line = data.get('log_line')
        error.line_number = data.get('line_number')
        error.type = data.get('type')
        error.category = data.get('category')
        return error

    def _serialize_uml_steps(self, uml_steps):
        """Serializa OrderedDict de UMLSteps (implementar según tu estructura)"""
        # Esto depende de cómo defines tus UMLSteps
        serialized = {}
        for line_num, steps in uml_steps.items():
            serialized[str(line_num)] = [self._serialize_uml_step(step) for step in steps]
        return serialized

    def _deserialize_uml_steps(self, serialized):
        """Deserializa OrderedDict de UMLSteps"""
        uml_steps = OrderedDict()
        for line_num_str, steps_data in serialized.items():
            line_num = int(line_num_str)
            uml_steps[line_num] = [self._deserialize_uml_step(step_data) for step_data in steps_data]
        return uml_steps

    def _serialize_uml_step(self, step):
        """Serializa un UMLStep individual"""
        # Implementar según tu clase UMLStep
        return step.__dict__  # O usa un método específico de UMLStep

    def _deserialize_uml_step(self, data):
        """Deserializa un UMLStep individual"""
        # Implementar según tu clase UMLStep
        from uml import UMLStep  # Ajustar import según tu estructura
        step = UMLStep()
        for key, value in data.items():
            setattr(step, key, value)
        return step

    def object_to_dict(self, obj):
        """
        This method converts a instanced class object into a dictionary to be serialised
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

