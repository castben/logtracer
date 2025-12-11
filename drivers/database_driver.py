# drivers/database_driver.py
from collections import OrderedDict

import psycopg2
from typing import Optional, List, Dict
from data_interface import DataDriver
from object_class import CordaObject, Party
from object_class import BlockItems
from object_class import Error

class DatabaseDataDriver(DataDriver):
    """
    Driver de datos usando base de datos SQL (PostgreSQL)
    """

    def __init__(self):
        self.connection = None
        self.config = {}

    def connect(self, **config):
        """
        Configurar conexión a base de datos
        config = {
            'host': 'localhost',
            'database': 'logtracer',
            'user': 'username',
            'password': 'password',
            'port': 5432
        }
        """
        self.config = config
        self.connection = psycopg2.connect(
            host=config['host'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            port=config.get('port', 5432)
        )
        self._create_tables_if_not_exists()

    def _create_tables_if_not_exists(self):
        """Crear tablas si no existen"""
        cursor = self.connection.cursor()

        # Tabla para CordaObjects (Flows/Transactions)
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS corda_objects (
                                                                    reference_id VARCHAR(255) PRIMARY KEY,
                           type VARCHAR(50),
                           line_number INTEGER,
                           timestamp VARCHAR(50),
                           error_level VARCHAR(20),
                           data JSONB,
                           references_data JSONB,
                           uml_steps JSONB
                           );
                       """)

        # Tabla para Parties
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS parties (
                                                              name VARCHAR(255) PRIMARY KEY,
                           reference_id VARCHAR(255),
                           role VARCHAR(100),
                           type VARCHAR(50),
                           corda_role JSONB,
                           default_endpoint VARCHAR(255),
                           alternate_names JSONB,
                           original_string TEXT,
                           attributes JSONB
                           );
                       """)

        # Tabla para BlockItems
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS block_items (
                                                                  id SERIAL PRIMARY KEY,
                                                                  timestamp VARCHAR(50),
                           line_number INTEGER,
                           reference VARCHAR(255),
                           content TEXT[],
                           type VARCHAR(50)
                           );
                       """)

        # Tabla para Errors
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS errors (
                                                             id SERIAL PRIMARY KEY,
                                                             reference_id VARCHAR(255),
                           timestamp VARCHAR(50),
                           log_line TEXT,
                           line_number INTEGER,
                           type VARCHAR(50),
                           category VARCHAR(50)
                           );
                       """)

        self.connection.commit()
        cursor.close()

    # --- CORDAOBJECT OPERATIONS ---

    def get_corda_object_by_id(self, ref_id: str) -> Optional[CordaObject]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM corda_objects WHERE reference_id = %s", (ref_id,))
        row = cursor.fetchone()
        cursor.close()

        if row:
            return self._row_to_corda_object(row)
        return None

    def get_corda_objects_by_type(self, obj_type: str) -> List[CordaObject]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM corda_objects WHERE type = %s", (obj_type,))
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_corda_object(row) for row in rows]

    def get_corda_objects_by_time_range(self, start_time: str, end_time: str) -> List[CordaObject]:
        cursor = self.connection.cursor()
        cursor.execute("""
                       SELECT * FROM corda_objects
                       WHERE timestamp BETWEEN %s AND %s
                       """, (start_time, end_time))
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_corda_object(row) for row in rows]

    def get_corda_objects_by_participant(self, party_name: str) -> List[CordaObject]:
        cursor = self.connection.cursor()
        # Buscar en el campo 'references_data' que contiene parties
        cursor.execute("""
                       SELECT * FROM corda_objects
                       WHERE references_data::text LIKE %s
                       """, (f'%{party_name}%',))
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_corda_object(row) for row in rows]

    def save_corda_object(self, corda_obj: CordaObject):
        cursor = self.connection.cursor()
        data_dict = self._corda_object_to_dict(corda_obj)

        cursor.execute("""
                       INSERT INTO corda_objects (
                           reference_id, type, line_number, timestamp, error_level,
                           data, references_data, uml_steps
                       ) VALUES (%(reference_id)s, %(type)s, %(line_number)s, %(timestamp)s,
                                 %(error_level)s, %(data)s, %(references_data)s, %(uml_steps)s)
                           ON CONFLICT (reference_id) DO UPDATE SET
                           type = EXCLUDED.type,
                                                             line_number = EXCLUDED.line_number,
                                                             timestamp = EXCLUDED.timestamp,
                                                             error_level = EXCLUDED.error_level,
                                                             data = EXCLUDED.data,
                                                             references_data = EXCLUDED.references_data,
                                                             uml_steps = EXCLUDED.uml_steps
                       """, data_dict)

        self.connection.commit()
        cursor.close()

    def save_corda_objects(self, corda_objects: List[CordaObject]):
        cursor = self.connection.cursor()
        for obj in corda_objects:
            data_dict = self._corda_object_to_dict(obj)
            cursor.execute("""
                           INSERT INTO corda_objects (
                               reference_id, type, line_number, timestamp, error_level,
                               data, references_data, uml_steps
                           ) VALUES (%(reference_id)s, %(type)s, %(line_number)s, %(timestamp)s,
                                     %(error_level)s, %(data)s, %(references_data)s, %(uml_steps)s)
                               ON CONFLICT (reference_id) DO UPDATE SET
                               type = EXCLUDED.type,
                                                                 line_number = EXCLUDED.line_number,
                                                                 timestamp = EXCLUDED.timestamp,
                                                                 error_level = EXCLUDED.error_level,
                                                                 data = EXCLUDED.data,
                                                                 references_data = EXCLUDED.references_data,
                                                                 uml_steps = EXCLUDED.uml_steps
                           """, data_dict)

        self.connection.commit()
        cursor.close()

    # --- PARTY OPERATIONS ---

    def get_all_parties(self) -> List[Party]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM parties")
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_party(row) for row in rows]

    def get_party_by_name(self, party_name: str) -> Optional[Party]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM parties WHERE name = %s", (party_name,))
        row = cursor.fetchone()
        cursor.close()

        if row:
            return self._row_to_party(row)
        return None

    def save_party(self, party: Party):
        cursor = self.connection.cursor()
        party_dict = self._party_to_dict(party)

        cursor.execute("""
                       INSERT INTO parties (
                           name, reference_id, role, type, corda_role,
                           default_endpoint, alternate_names, original_string, attributes
                       ) VALUES (%(name)s, %(reference_id)s, %(role)s, %(type)s, %(corda_role)s,
                                 %(default_endpoint)s, %(alternate_names)s, %(original_string)s, %(attributes)s)
                           ON CONFLICT (name) DO UPDATE SET
                           reference_id = EXCLUDED.reference_id,
                                                     role = EXCLUDED.role,
                                                     type = EXCLUDED.type,
                                                     corda_role = EXCLUDED.corda_role,
                                                     default_endpoint = EXCLUDED.default_endpoint,
                                                     alternate_names = EXCLUDED.alternate_names,
                                                     original_string = EXCLUDED.original_string,
                                                     attributes = EXCLUDED.attributes
                       """, party_dict)

        self.connection.commit()
        cursor.close()

    # --- BLOCK ITEMS OPERATIONS ---

    def get_block_items_by_type(self, block_type: str) -> List[BlockItems]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM block_items WHERE type = %s", (block_type,))
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_block_item(row) for row in rows]

    def get_block_items_by_reference(self, ref_id: str) -> List[BlockItems]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM block_items WHERE reference = %s", (ref_id,))
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_block_item(row) for row in rows]

    def save_block_item(self, block_item: BlockItems):
        cursor = self.connection.cursor()
        block_dict = self._block_item_to_dict(block_item)

        cursor.execute("""
                       INSERT INTO block_items (
                           timestamp, line_number, reference, content, type
                       ) VALUES (%(timestamp)s, %(line_number)s, %(reference)s, %(content)s, %(type)s)
                       """, block_dict)

        self.connection.commit()
        cursor.close()

    # --- ERROR OPERATIONS ---

    def get_errors_by_category(self, category: str) -> List[Error]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM errors WHERE category = %s", (category,))
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_error(row) for row in rows]

    def get_errors_by_type(self, error_type: str) -> List[Error]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM errors WHERE type = %s", (error_type,))
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_error(row) for row in rows]

    def get_all_errors(self) -> List[Error]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM errors")
        rows = cursor.fetchall()
        cursor.close()

        return [self._row_to_error(row) for row in rows]

    def save_error(self, error: Error):
        cursor = self.connection.cursor()
        error_dict = self._error_to_dict(error)

        cursor.execute("""
                       INSERT INTO errors (
                           reference_id, timestamp, log_line, line_number, type, category
                       ) VALUES (%(reference_id)s, %(timestamp)s, %(log_line)s, %(line_number)s,
                                 %(type)s, %(category)s)
                       """, error_dict)

        self.connection.commit()
        cursor.close()

    def disconnect(self):
        if self.connection:
            self.connection.close()

    # --- CONVERSION METHODS ---

    def _row_to_corda_object(self, row) -> CordaObject:
        obj = CordaObject()
        obj.reference_id = row[0]
        obj.type = row[1]
        obj.line_number = row[2]
        obj.timestamp = row[3]
        obj.error_level = row[4]
        obj.data = row[5] if row[5] else {}
        obj.references = OrderedDict(row[6]) if row[6] else OrderedDict()
        obj.uml_steps = self._deserialize_uml_steps(row[7]) if row[7] else OrderedDict()
        return obj

    def _row_to_party(self, row) -> Party:
        party = Party(x500name=row[0])
        party.reference_id = row[1]
        party.role = row[2]
        party.type = row[3]
        party.corda_role = row[4] if row[4] else []
        party.default_endpoint = row[5]
        party.alternate_names = row[6] if row[6] else []
        party.original_string = row[7]
        party.attributes = row[8] if row[8] else {}
        return party

    def _row_to_block_item(self, row) -> BlockItems:
        block = BlockItems()
        block.timestamp = row[1]  # timestamp
        block.line_number = row[2]  # line_number
        block.reference = row[3]  # reference
        block.content = row[4] if row[4] else []
        block.type = row[5]  # type
        return block

    def _row_to_error(self, row) -> Error:
        error = Error()
        error.reference_id = row[1]  # reference_id
        error.timestamp = row[2]  # timestamp
        error.log_line = row[3]  # log_line
        error.line_number = row[4]  # line_number
        error.type = row[5]  # type
        error.category = row[6]  # category
        return error

    def _corda_object_to_dict(self, obj: CordaObject) -> Dict:
        return {
            'reference_id': obj.reference_id,
            'type': obj.type,
            'line_number': obj.line_number,
            'timestamp': obj.timestamp,
            'error_level': obj.error_level,
            'data': obj.data,
            'references_data': dict(obj.references),
            'uml_steps': self._serialize_uml_steps(obj.uml_steps),
        }

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

    def _block_item_to_dict(self, block: BlockItems) -> Dict:
        return {
            'timestamp': block.timestamp,
            'line_number': block.line_number,
            'reference': block.reference,
            'content': block.content,
            'type': block.type,
        }

    def _error_to_dict(self, error: Error) -> Dict:
        return {
            'reference_id': error.reference_id,
            'timestamp': error.timestamp,
            'log_line': error.log_line,
            'line_number': error.line_number,
            'type': error.type,
            'category': error.category,
        }

    # Métodos de serialización/deserialización (mismos que en YAML)
    def _serialize_uml_steps(self, uml_steps):
        serialized = {}
        for line_num, steps in uml_steps.items():
            serialized[str(line_num)] = [self._serialize_uml_step(step) for step in steps]
        return serialized

    def _deserialize_uml_steps(self, serialized):
        uml_steps = OrderedDict()
        for line_num_str, steps_data in serialized.items():
            line_num = int(line_num_str)
            uml_steps[line_num] = [self._deserialize_uml_step(step_data) for step_data in steps_data]
        return uml_steps

    def _serialize_uml_step(self, step):
        return step.__dict__

    def _deserialize_uml_step(self, data):
        from uml import UMLStep
        step = UMLStep()
        for key, value in data.items():
            setattr(step, key, value)
        return step