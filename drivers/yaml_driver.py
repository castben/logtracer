# drivers/yaml_driver.py
from collections import OrderedDict

import yaml
import os
from pathlib import Path
from typing import Optional, List, Dict
from data_interface import DataDriver
from object_class import CordaObject, Party
from object_class import BlockItems
from object_class import Error

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
        self.cache = {}  # Opcional: cache para mejorar rendimiento

    def connect(self, **config):
        """
        Configurar directorio de datos
        config = {
            'data_dir': '/ruta/a/data/',
            'cache_enabled': True
        }
        """
        self.data_dir = Path(config.get('data_dir', './data'))
        self.entities_dir = self.data_dir / "entities"
        self.parties_dir = self.data_dir / "parties"
        self.blocks_dir = self.data_dir / "blocks"
        self.errors_dir = self.data_dir / "errors"

        # Crear directorios
        for dir_path in [self.entities_dir, self.parties_dir, self.blocks_dir, self.errors_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Cargar cache si está habilitada
        if config.get('cache_enabled', False):
            self._load_cache()

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

    def save_corda_object(self, corda_obj: CordaObject):
        entity_file = self.entities_dir / f"entity_{corda_obj.reference_id}.yaml"
        data = self._corda_object_to_dict(corda_obj)

        with open(entity_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # Actualizar cache
        if hasattr(self, 'cache'):
            self.cache[f"entity_{corda_obj.reference_id}"] = corda_obj

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

    def save_party(self, party: Party):
        party_file = self.parties_dir / f"{party.name}.yaml"
        data = self._party_to_dict(party)

        with open(party_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    # --- BLOCK ITEMS OPERATIONS ---

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

    def save_block_item(self, block_item: BlockItems):
        block_file = self.blocks_dir / f"block_{block_item.reference}_{block_item.type}.yaml"
        data = self._block_item_to_dict(block_item)

        with open(block_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    # --- ERROR OPERATIONS ---

    def get_errors_by_category(self, category: str) -> List[Error]:
        errors = []
        for error_file in self.errors_dir.glob(f"error_*_{category}.yaml"):
            with open(error_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                errors.append(self._dict_to_error(data))
        return errors

    def get_errors_by_type(self, error_type: str) -> List[Error]:
        errors = []
        for error_file in self.errors_dir.glob(f"error_{error_type}_*.yaml"):
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

    def save_error(self, error: Error):
        error_file = self.errors_dir / f"error_{error.type}_{error.category}.yaml"
        data = self._error_to_dict(error)

        with open(error_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

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