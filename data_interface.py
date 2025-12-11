# data_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from collections import OrderedDict
import threading

# Importar tus clases
from object_class import CordaObject, Party
from object_class import BlockItems
from object_class import Error

class DataDriver(ABC):
    """
    Interfaz abstracta para todos los drivers de datos
    Adaptada a las estructuras de Log Tracer
    """

    @abstractmethod
    def connect(self, **config):
        """Iniciar conexión o carga de datos"""
        pass

    # --- OPERACIONES PARA CORDAOBJECT (Flows/Transactions) ---

    @abstractmethod
    def get_corda_object_by_id(self, ref_id: str) -> Optional[CordaObject]:
        """Obtener un CordaObject (flow o transaction) por ID"""
        pass

    @abstractmethod
    def get_corda_objects_by_type(self, obj_type: str) -> List[CordaObject]:
        """Obtener todos los objetos de un tipo específico (FLOW, TRANSACTION, etc.)"""
        pass

    @abstractmethod
    def get_corda_objects_by_time_range(self, start_time: str, end_time: str) -> List[CordaObject]:
        """Obtener objetos en un rango de tiempo"""
        pass

    @abstractmethod
    def get_corda_objects_by_participant(self, party_name: str) -> List[CordaObject]:
        """Obtener objetos donde participa una party específica"""
        pass

    @abstractmethod
    def save_corda_object(self, corda_obj: CordaObject):
        """Guardar un CordaObject (flow o transaction)"""
        pass

    @abstractmethod
    def save_corda_objects(self, corda_objects: List[CordaObject]):
        """Guardar múltiples CordaObjects (para procesamiento por lotes)"""
        pass

    # --- OPERACIONES PARA PARTIES ---

    @abstractmethod
    def get_all_parties(self) -> List[Party]:
        """Obtener todas las parties conocidas"""
        pass

    @abstractmethod
    def get_party_by_name(self, party_name: str) -> Optional[Party]:
        """Obtener party por nombre"""
        pass

    @abstractmethod
    def save_party(self, party: Party):
        """Guardar una party"""
        pass

    # --- OPERACIONES PARA BLOCK ITEMS ---

    @abstractmethod
    def get_block_items_by_type(self, block_type: str) -> List[BlockItems]:
        """Obtener bloques de un tipo específico"""
        pass

    @abstractmethod
    def get_block_items_by_reference(self, ref_id: str) -> List[BlockItems]:
        """Obtener bloques relacionados a un reference_id"""
        pass

    @abstractmethod
    def save_block_item(self, block_item: BlockItems):
        """Guardar un bloque de items"""
        pass

    # --- OPERACIONES PARA ERRORES ---

    @abstractmethod
    def get_errors_by_category(self, category: str) -> List[Error]:
        """Obtener errores por categoría"""
        pass

    @abstractmethod
    def get_errors_by_type(self, error_type: str) -> List[Error]:
        """Obtener errores por tipo"""
        pass

    @abstractmethod
    def get_all_errors(self) -> List[Error]:
        """Obtener todos los errores"""
        pass

    @abstractmethod
    def save_error(self, error: Error):
        """Guardar un error"""
        pass

    @abstractmethod
    def disconnect(self):
        """Cerrar conexión o guardar datos pendientes"""
        pass