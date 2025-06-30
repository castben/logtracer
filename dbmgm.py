# Database class to manage program data

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from object_class import Party,CordaObject

class LogDatabase(ABC):
    @abstractmethod
    def connect(self, **kwargs):
        pass

    @abstractmethod
    def insert_party(self, party: Party) -> int:
        pass

    @abstractmethod
    def get_party_id(self, name: str) -> Optional[int]:
        pass


    @abstractmethod
    def insert_corda_object(self, cordaobject: CordaObject):
        """
        This will insert given corda object that it may contain A Transaction or a Flow
        :param cordaobject: Actual cordaobject to persist
        """
        pass


    @abstractmethod
    def insert_event(self,
                     timestamp: str,
                     log_line: str):
        pass

    @abstractmethod
    def get_events(self, reference_id: str, object_type: str) -> List[Dict]:
        pass


    @abstractmethod
    def close(self):
        pass