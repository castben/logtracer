import os
import re
import textwrap
from collections import OrderedDict
from datetime import datetime
from enum import Enum
from pickletools import optimize
from queue import Queue
from log_handler import write_log
from object_class import Configs, generate_internal_access, CordaObject, RegexLib, get_fields_from_log, X500NameParser
import threading
from typing import List, Callable, Any, Dict


class UMLCommand:
    """
    Container for all uml commands, like '->','<-', etc...
    """

    def __init__(self,configs):
        self.attribute = {}
        self.configs = configs
        self.command_action = {}

        self.initialize()

    def initialize(self):
        """Load all commands into memory
        """

        self.command_action = self.configs

    def set(self, att,value):
        """
        Set attribute
        :param att: name
        :param value: value
        :return:
        """

        self.attribute[att] = value

    def get(self, att):
        """
        Return value from att name
        :param att: attribute name, if attribute is within a nested dictionary, you can use 'dot' notation to reach
        any parameter in lower levels, for example 'USAGES.default_source.EXPECT'
        :return: value none otherwise
        """

        _,value = generate_internal_access(self.attribute,att)
        if value:
            return value

        return None

class UMLStep:
    """
    Class representing actual uml step found
    """

    uml_steps = {}

    def __init__(self):
        """
        UMLStep attributes
        """
        self.attribute = {}
        self.reference_id = None

    class Attribute(Enum):
        """
        Allowed attributes to set
        """
        LINE_NUMBER = 0
        LINE_MESSAGE = 1
        UML_COMMAND = 2
        UML_COMMAND_DEFINITION = 3
        ROLE = 4
        TYPE = 5
        REGEX_TO_APPLY = 6
        REGEX_COMPILED = 7
        REGEX_INDEX = 8
        ID = 9
        FIELDS = 10
        TIMESTAMP = 11
        TIMESTAMP_FMT = 12

    def analyse(self):
        """
        Analyse current step to determine correct UML setup
        :return:
        """


        # TODO:
        #       1) obtener el objeto UML candidato
        #       2) extraer los settings y opciones para este objeto
        #       3) en caso de aparecer la opcion "SINGLE_DEFINITION" esto significa que el party involucrado debera
        #       definirse solo una vez -- esto no lo voy a manejar aqui; es mejor en `build_uml`
        #       4) extraer los campos esperados en la linea a analizar
        #       5) rellenar las variables con los valores apropiados a cada campo esperado
        #       6) en caso de que el campo no este presente en la linea, obtener el valor por defecto
        #       7) agregar un nuevo diccionario con las acciones UML con sus respectivos valores

        # list of steps found on given line
        uml_list = []
        # Criteria to split step in two, when more than one CORDA_OBJECT is being found
        uml_corda_objects = Configs.get_config_for('CORDA_OBJECTS')
        # Variable to hold UML actions
        uml_actions = {}
        # Get UML command
        uml_command = self.get(UMLStep.Attribute.UML_COMMAND)
        # Get any ignore string within line
        uml_ignore = Configs.get_config_for(f'UML_DEFINITIONS.{uml_command}.IGNORE')
        # Get any option required
        uml_options = Configs.get_config_for(f'UML_DEFINITIONS.{uml_command}.OPTIONS')
        # Get all expected fields for this given uml_command; this help to get proper information from analysed line
        expected_fields = Configs.get_config_for(f'UML_DEFINITIONS.{uml_command}.FIELDS')
        fields_found = list(expected_fields)
        fields_orig = list(expected_fields)
        # delete any field that is not in regex line
        for each_field in expected_fields:
            ztag, zaction = each_field.split(':')
            rgx = self.get(UMLStep.Attribute.REGEX_TO_APPLY)
            if ((f"__{zaction}__" not in rgx and f"<{zaction}>" not in rgx) and
                    (f"__{ztag}__" not in rgx and f"<{ztag}>" not in rgx)):
                fields_found.remove(each_field)

        expected_fields = fields_found

        extra_data_list = list(set(fields_orig) - set(fields_found))

        extra_data = self.extract_extra_data(extra_data_list)

        line_message = self.get(UMLStep.Attribute.LINE_MESSAGE)

        match = self.get(UMLStep.Attribute.REGEX_COMPILED).search(line_message)
        # Extract any defined field on this line
        fields = match.groupdict()
        if extra_data:
            fields.update(extra_data)
        if fields:
            self.set(UMLStep.Attribute.FIELDS, fields)

        # Try to extract all fields on this line (expected_fields)
        for each_field in expected_fields:
            field,action = each_field.split(':')
            #
            # Check if I have value for given field
            if action in fields and action not in uml_actions:
                # collect appropriate uml action for this field
                uml_actions[field] = fields[action]

                # continue

            # Unable to get proper definition from extracted fields, so then look for another way
            # to extract such information...
            #

            definition = CordaObject.get_corda_object_definition_for(action, True)

            if definition:
                if isinstance(definition, str):
                    definition = [definition]
                for each_definition in definition:
                    pattern = RegexLib.build_regex(each_definition)
                    check = re.search(pattern, line_message)
                    if check:
                        # uml_actions[f"{field}|{check.group(1)}"] = action
                        uml_actions[action] = f"{field}|{check.group(1)}"
                        break

            self.set(UMLStep.Attribute.UML_COMMAND_DEFINITION, uml_actions)

        return self

    def extract_extra_data(self, fields):
        """
        This will extract extra data when it is available in scanned line.
        :param fields: extra fields to get
        :return: a dictionary with all extra data found
        """

        log_line = self.get(UMLStep.Attribute.LINE_MESSAGE)
        extra_data = {}

        for each_field in fields:
            if 'annotation' in each_field:
                _,field = each_field.split(':')
                definition = CordaObject.get_corda_object_definition_for(field, True)
                if definition:
                    if isinstance(definition, str):
                        definition = [definition]
                    for each_definition in definition:
                        pattern = RegexLib.build_regex(each_definition)
                        check = re.search(pattern, log_line)
                        if check:
                            extra_data[field] = check.group(1)
        return extra_data

    def add_into_attribute(self, attribute, value,  field):
        """
        Add a new item to given attribute, attribute *MUST* be a UMLStep.Attribute otherwise it will be ignored
        :param attribute: Attribute description to modify
        :param value: item that need to be added
        :return: None
        """

        # Attribute *MUST* exist and *MUST* be a list otherwise will be ignored
        if attribute not in self.attribute or not isinstance(self.attribute[attribute], dict):
            return

        if field in self.attribute[attribute] and self.attribute[attribute][field] != value:
            # if actual attribute already exist... key need to be modified to accomodate new value *ONLY* if new value
            # do not exist in actual dict
            fint = 0
            tfield = ""
            while True:
                tfield = f"{field}|0"
                if tfield not in self.attribute[attribute]:
                    break
            self.attribute[attribute][tfield] = value
        else:
            self.attribute[attribute][field] = value

    def set(self, name, value):
        """
        Property to set
        :param name:
        :param value:
        :return:
        """
        if isinstance(name, UMLStep.Attribute):
            self.attribute[name] = value
            if name == UMLStep.Attribute.LINE_NUMBER:
                self.reference_id = value

    def get(self, attribute):
        """
        Get property stored
        :param attribute: property name to get
        :return:
        """
        if isinstance(attribute, UMLStep.Attribute):
            if attribute in self.attribute:
                return  self.attribute[attribute]

        return None

    @classmethod
    def set_direct_list(cls, reference_id, step_list):
        """
        Add a list of items directly into internal list
        :param reference_id: reference_id associated
        :param step_list: list of steps to be added
        :return:
        """

        if reference_id in cls.uml_steps and isinstance(cls.uml_steps[reference_id], list):
            cls.uml_steps[reference_id].extend(step_list)
        else:
            cls.uml_steps[reference_id] = step_list


    def add(self):
        """
        Add given UML step into class list
        :return: void
        """
        if self.get(UMLStep.Attribute.ID) and self.get(UMLStep.Attribute.ID) not in UMLStep.uml_steps:
            # Create a new step
            UMLStep.uml_steps[self.get(UMLStep.Attribute.ID)] = []

        UMLStep.uml_steps[self.get(UMLStep.Attribute.ID)].append(self)

    def get_step_list(self):
        """
        Return list of all steps for this object

        :return: a list of UMLStep
        """

        if self.get(UMLStep.Attribute.ID) and self.get(UMLStep.Attribute.ID) in UMLStep.uml_steps:
            return UMLStep.uml_steps[self.get(UMLStep.Attribute.ID)]

        return None

    @classmethod
    def get_steps_for(cls, reference_id, type=None):
        """
        Return steps from given reference ID

        :param type:  ddd
        :param reference_id: reference Id required
        :return: a list of steps related to that reference_id none otherwise
        """

        if reference_id in UMLStep.uml_steps:
            if not type:
                return cls.uml_steps[reference_id]

            if type:

                pass

        return None

class UMLStepSetup:
    uml_candidate_steps = []
    Configs = None
    file = None
    uml_definitions = {}
    full_rule_search = None

    def __init__(self, get_configs, corda_object):
        """
        Class initialization
        """

        UMLStepSetup.Configs = get_configs
        UMLStepSetup.file = None
        self.cordaobject = corda_object
        self.type = None
        self.max_items = 100

        # Load actual "patterns" to look for that can identify a potential UML step...
        #
        if not UMLStepSetup.uml_definitions:
            tmp = UMLStepSetup.Configs.get_config_for("UML_DEFINITIONS")
            for each_cmd in tmp:
                if 'COMMAND' in tmp[each_cmd]:
                    UMLStepSetup.uml_definitions[each_cmd] = tmp[each_cmd]


    def check_for_uml_step(self, original_line, current_line_no):
        """
        Pre-load all required regex to speed up searches.
        :return:
        """

        umlsteps_list = []
        otype = self.cordaobject.get_type()
        orefid = self.cordaobject.get_reference_id()
        for each_uml_definition in UMLStepSetup.uml_definitions:
            # now for each uml definition, try to see if we have a match
            #
            # Stage 1: Find out which UML command should be applied to given line, as all UML_DEFINITIONS are
            # created as "meta-definitions" I need below line to extract actual regex that need to be used...
            # In this section, i will loop over all defined UML commands, and find out if this line match any of them

            list_of_expects_to_try = UMLStepSetup.uml_definitions[each_uml_definition]["EXPECT"]
            expect_to_use = RegexLib.regex_to_use(list_of_expects_to_try, original_line)

            # Extract timestamp from current line where this step was found:
            log_fields = get_fields_from_log(original_line,self.file.logfile_format, self.file)

            if 'timestamp' in log_fields:
                timestamp = log_fields['timestamp']
            else:
                timestamp = self.cordaobject.timestamp
                write_log(f'File line {current_line_no}: Unable to extract a proper timestamp from this line:\n{original_line}', level='WARN')

            if expect_to_use is None:
                # If we do not have any valid regex for this line, try next list
                continue

            regex_expect = list_of_expects_to_try[expect_to_use]

            each_expect = RegexLib.build_regex(regex_expect)
            umlstep = UMLStep()
            umlstep.set(UMLStep.Attribute.ID, orefid)
            umlstep.set(UMLStep.Attribute.TYPE, otype)
            umlstep.set(UMLStep.Attribute.LINE_NUMBER, current_line_no)
            umlstep.set(UMLStep.Attribute.LINE_MESSAGE, original_line)
            umlstep.set(UMLStep.Attribute.UML_COMMAND, each_uml_definition)
            umlstep.set(UMLStep.Attribute.REGEX_TO_APPLY, regex_expect)
            umlstep.set(UMLStep.Attribute.REGEX_COMPILED, re.compile(each_expect))
            umlstep.set(UMLStep.Attribute.REGEX_INDEX, expect_to_use)
            fmt, standard_timestamp = UMLStepSetup.normalize_timestamp(timestamp)
            if standard_timestamp:
                umlstep.set(UMLStep.Attribute.TIMESTAMP, standard_timestamp)
                umlstep.set(UMLStep.Attribute.TIMESTAMP_FMT, fmt)
            else:
                # Unable to process timestamp!
                umlstep.set(UMLStep.Attribute.TIMESTAMP, self.cordaobject.timestamp)

            umlsteps_list.append(umlstep)
        if umlsteps_list:
            self.cordaobject.add_uml_step(current_line_no, umlsteps_list)
            return umlsteps_list
        else:
            return None

    @staticmethod
    def normalize_timestamp(timestamp_str: str):
        """
        A method to normalize timestamp into a unified format
        :param timestamp_str: timestamp to try to parse
        :return: standard timestamp
        """

        """
        Intenta parsear un timestamp de log a un objeto datetime.
        Soporta múltiples formatos comunes en logs.
        """
        # Lista de formatos posibles
        formats = Configs.get_config_for('FILE_SETUP.FORMATS.TIMESTAMP')

        for fmt in formats:
            try:
                # Reemplazar coma por punto para milisegundos
                if ',%f' in fmt:
                    timestamp_str = timestamp_str.replace(',', '.')
                stamp_check = datetime.strptime(timestamp_str, fmt)
                return fmt, stamp_check
            except ValueError:
                continue

        # Si ningún formato funciona
        raise ValueError(f"Unable to parse this timestamp: {timestamp_str}, please a parsing format at JSON file")


    def set_element_type(self, element_type):
        """
        Set actual type of element being processed
        :return: None
        """
        if isinstance(element_type, CordaObject.Type):
            selement_type = element_type.value
            element_type = selement_type

        self.type = element_type

    def get_element_type(self):
        """
        Return element type for this item; element type could be "Party" which represents party element, or
        'Flows&Transactions' which represents all tx and flows found.
        """
        return self.type

    def analyse_references(self):
        """
        Count number of references and if they are greater than max_item, then will split several processes
        to speed up
        :return:
        """
        pass


    def process_uml_chunk(self, chunk: Dict[int, str]):
        """Procesa un bloque del diccionario y genera los UMLSteps"""
        write_log(f"[{threading.current_thread().name}]: {len(chunk)} "
              f"steps processed: {list(chunk.keys())[0]} - {list(chunk.keys())[len(chunk)-1]}" )

        for line_num, line in chunk.items():
            # uml_step = parse_line_to_uml_step(line)
            self.check_for_uml_step(line, line_num)

    @staticmethod
    def chunked_dict(data: Dict[int, str], chunk_size: int):
        """Divide un diccionario ordenado en sublistas de tamaño chunk_size"""
        items = list(data.items())  # Convertimos a lista de tuplas
        return [
            dict(items[i:i + chunk_size])  # Recreamos dicts pequeños
            for i in range(0, len(items), chunk_size)
    ]


    def parallel_processX(self,log_dict: Dict[int, str], chunk_size: int = 100, max_threads: int = 4):
        chunks = UMLStepSetup.chunked_dict(log_dict, chunk_size)

        threads = []
        for i, chunk in enumerate(chunks):
            if i >= max_threads:
                break  # Limita la cantidad de hilos activos al mismo tiempo
            thread = threading.Thread(
                target=self.process_uml_chunk,
                args=(chunk,),
                name=f"Thread-{i+1}"
            )
            threads.append(thread)
            thread.start()

        # Esperar a que todos los hilos terminen
        for t in threads:
            t.join()

        write_log("✅ All block has been processed.")

    def parallel_process(self, corda_object: CordaObject, chunk_size: int = 100, max_threads: int = 4):
        # Dividir el diccionario en bloques

        if not corda_object.get_references():
            write_log(f'Sorry {corda_object.reference_id} has no references to generate a UML diagram, please select another reference...', level='WARN')
            return
        log_dict = {corda_object.get_line(): corda_object.get_data('Original line')}
        log_dict.update(corda_object.get_references())
        chunks = UMLStepSetup.chunked_dict(log_dict, chunk_size)

        # Crear una cola y llenarla con todos los bloques
        queue = Queue()
        for chunk in chunks:
            queue.put(chunk)

        # Función interna para procesar bloques
        def worker():
            while not queue.empty():
                try:
                    chunk = queue.get()
                    self.process_uml_chunk(chunk)
                    queue.task_done()
                except Exception as e:
                    write_log(f"Error processing block: {e}")
                    queue.task_done()

        # Crear y lanzar hilos
        threads = []
        for i in range(max_threads):
            thread = threading.Thread(target=worker, daemon=True, name=f"Thread-{i + 1}")
            thread.start()
            threads.append(thread)

        # Esperar a que todos los bloques se procesen
        queue.join()
        self.cordaobject.uml_steps = UMLStepSetup.sort_uml_steps(self.cordaobject.uml_steps)
        write_log("✅ Done")

    @staticmethod
    def sort_uml_steps(uml_dict):
        """
        Ordena un diccionario (OrderedDict) por número de línea (clave entera)

        :param uml_dict: OrderedDict con claves como números de línea
        :return: Nuevo OrderedDict ordenado
        """
        return OrderedDict(sorted(uml_dict.items(), key=lambda x: x[0]))

    def get_uml(self, line_number=None):
        """
        Will return specified UML representation for given line
        :param line_number: log line number
        :return: uml representation for given line, or all of them if no line is give(dictionary), None if no line found
        """

        if not line_number:
            return self.cordaobject.get_uml()

        if self.cordaobject.get_uml(line_number):
            return self.cordaobject.get_uml(line_number)

        return None
    @staticmethod
    def execute(each_line, current_line):
        """

        :param each_line:
        :param current_line:
        :return:
        """
        return UMLStepSetup.check_for_uml_step(each_line, current_line)

class UMLEntity:
    """
    Entity definition for UML
    """

    uml_entity_role_definition = None
    entity_role = {}
    config = None
    uml_line_candidate = {}

    def __init__(self):
        self.attribute = {}

    @staticmethod
    def initialize(config):

        UMLEntity.config = config
        if not UMLEntity.uml_entity_role_definition:
            UMLEntity.uml_entities_list = config.get_config_for('UML_ENTITY.OBJECTS')

        for each_entity in UMLEntity.uml_entities_list:
            uml_entity = UMLEntity()
            uml_entity_att_list = UMLEntity.uml_entities_list[each_entity]
            for each_entity_att in uml_entity_att_list:
                uml_entity.set(each_entity_att, uml_entity_att_list[each_entity_att])

            uml_entity.add(each_entity)

    def add(self, name):
        """
        Add this instance to internal instances list
        :return:
        """
        UMLEntity.entity_role[name] = self

    def set(self, att,value):
        """
        Set attribute
        :param att: name
        :param value: value
        :return:
        """

        self.attribute[att] = value

    def get(self, att):
        """
        Return value from att name
        :param att: attribute name, if attribute is within a nested dictionary, you can use 'dot' notation to reach
        any parameter in lower levels, for example 'USAGES.default_source.EXPECT'
        :return: value none otherwise
        """

        _,value = generate_internal_access(self.attribute,att)
        if value:
            return value

        return None

    @property
    def get_list(self):
        """
        List loaded entities roles
        :return:
        """

        return UMLEntity.entity_role

    @staticmethod
    def get_entity(name, att=None):
        """
        Return entity instance class for given name
        :param name: name of instance stored
        :param att: attribute required from given stored instance
        :return:
        """
        if name not in UMLEntity.entity_role:
            return None

        if not att:
            return UMLEntity.entity_role[name]

        _, value = generate_internal_access(UMLEntity.entity_role[name].get(f'UML_ENTITY.OBJECTS.{name}'), att)

        if value:
            return value

        return None

class UMLEntityEndPoints:

    endpoint_list = {}

    def __init__(self):
        """
        Endpoint definition
        """
        self.name = None


    def add_endpoint(self,entity_name, entity_details):
        """
        Add new entity into list
        :param entity_name: entity name, basically its role -- log_owner, notary, flow_hospital, etc...
        :param entity_details: detailed definition of such entity, this contains way to pull correct information
        from log message
        :return: None
        """
        self.name = entity_name
        for key in entity_details:
            setattr(self, key, entity_details[key])

        UMLEntityEndPoints.endpoint_list[entity_name] = self

    def get_usages(self, usage_case=None, expect_list=False, ignore_list=False):
        """
        Return actual usages details of current endpoint
        :param usage_case: which usage case you want to have details on default usage case names are 'default_source' and
        'default_destination', if not usage case is being given, it will list all usage cases.
        :param expect_list: if is true will give a list of all regex expressions for given case
        :param ignore_list: will list any regex that need to be considered to avoid this usage_case
        :return: actual usage case if is different of None, otherwise will return all current usages cases
        """

        if 'USAGES' not in  self.__dict__:
            return None

        if not usage_case:
            return list(self.USAGES.keys())

        if usage_case and usage_case not in self.USAGES.keys():
            return None

        if expect_list:
            return self.USAGES[usage_case]['EXPECT']

        if ignore_list:
            return self.USAGES[usage_case]['IGNORE']

        return self.USAGES[usage_case]


    def get_endpoint(self, default_use_case):
        """
        Return list of expected regex for given default_use_case
        :param default_use_case: name of default_use_case required
        :return: list of Expects that identify this default_use_case as what it is...
        """

        if default_use_case in self.USAGES:
            return self.USAGES[default_use_case]['EXPECT']

        return None

    def get_return_object(self, default_use_case):
        """
        Will return defined list of objects on this default use case

        :default_use_case: name of usage case return object is required
        :return: list of objects
        """

        if self.get_entity_endpoint(default_use_case):
            return self.USAGES[default_use_case]['RETURN_OBJECT']

        return None



    @classmethod
    def load_default_endpoints(cls):
        """
        Load defined default endpoints
        :return: None
        """
        ep = Configs.get_config_for('UML_ENTITY.OBJECTS')
        for each_entity in Configs.get_config_for('UML_ENTITY.OBJECTS'):
            new_default_endpoint = cls()
            new_default_endpoint.add_endpoint(each_entity, ep[each_entity])


    @classmethod
    def get_default_endpoints(cls, entity_name=None):
        """
        Will return given entity name endpoint if it is found
        :param entity_name: entity role name to look for
        :return: entity endpoint object
        """

        if not entity_name:
            return cls.endpoint_list

        if entity_name in cls.endpoint_list:
            return cls.endpoint_list[entity_name]

        return None

class CreateUML:
    """
    Class in charge of UML script representation
    """

    unverified_participants = []
    verified_participants = []

    def __init__(self, corda_object, file_management=None):
        self.corda_object = corda_object
        self.file_management = file_management
        self.final_uml = OrderedDict(
            {
                'uml_start': [],
                'uml_body': [],
                'uml_end': []
            }
        )
        self.title = "" # will keep information from whole file if this is divided by pages
        self.pages = 0
        self.uml_highlight = Configs.get_config_for('UML_HIGHLIGHT')
        self.highlight_check = {}
        for each_highlight in self.uml_highlight:
            rgx = '|'.join(self.uml_highlight[each_highlight]['EXPECT'])
            self.highlight_check[each_highlight] = {
                'REGEX': re.compile(rgx),
                'UML_COMMAND': self.uml_highlight[each_highlight]['UML_COMMAND']
            }

    @classmethod
    def add_unverified_participant(cls, participant):
        """
        Add a participant
        :return:
        """

        if participant not in cls.unverified_participants:
            cls.unverified_participants.append(participant)

    @classmethod
    def add_verified_participant(cls, participant):
        """
        Add a participant
        :return:
        """

        if participant not in cls.verified_participants:
            cls.verified_participants.append(participant)


    def setup_endpoints_and_verify_participants(self):
        special_cases = {}
        # Get a list of all parties
        parties = self.file_management.get_all_unique_results(CordaObject.Type.PARTY, False)
        log_owner = self.file_management.get_party_role('log_owner')
        if log_owner:
            log_owner = log_owner[0]
            special_cases['log_owner'] = f'participant "{log_owner}"'

        special_cases['FlowHospital'] = 'control FlowHospital'
        special_cases['database'] = 'database vault'
        special_cases['vault'] = 'database vault'

        # verify participants
        #
        for each_party in parties:
            if each_party in ",".join(CreateUML.unverified_participants):

                CreateUML.add_verified_participant(f'participant "{each_party}"')

        # Search special cases:
        for each_special in special_cases:
            if each_special in CreateUML.unverified_participants:
                CreateUML.add_verified_participant(special_cases[each_special])

    @staticmethod
    def check_overlapped_notes(body):
        """
        This method will check if given text has overlapped notes,
         and then it will join them to be a single note
        :param body: array list that contains the uml text to check
        :return: corrected body without overlapped notes
        """
        new_body = list(body)
        index_counter = 0
        while index_counter < len(body) - 1:
            for each_note_type in ["note left", "note right", "note over"]:
                first_line = re.search(each_note_type, body[index_counter])
                second_line = re.search(each_note_type, body[index_counter + 1])
                if first_line and second_line:
                    new_body[index_counter] = new_body[index_counter].replace("\nend note", "\n---")
                    new_body[index_counter + 1] = new_body[index_counter + 1].replace("%s\n" % (each_note_type,), "")
            index_counter += 1

        return new_body

    def create_script_old(self):
        """
        Create actual uml script
        :return:
        """

        self.analyse_uml()

        self.setup_endpoints_and_verify_participants()
        self_node = self.file_management.get_party_role('log_owner')
        if self_node and isinstance(self_node, list):
            self_node = self_node[0]
        uml_objects = self.corda_object.get_uml()

        for each_item in uml_objects:
            for each_step in uml_objects[each_item]:
                command_dict = each_step.get(UMLStep.Attribute.UML_COMMAND_DEFINITION)
                action = each_step.get(UMLStep.Attribute.UML_COMMAND)

                if action == '->' or action == '<-':
                    note = self.setup_note(each_step)
                    if action == '<-':
                        source = CreateUML.define_field_limits(CreateUML.get_value_for('destination', command_dict),
                                                               'uml_object')
                        destination = CreateUML.define_field_limits(CreateUML.get_value_for('source', command_dict),
                                                                    'uml_object')
                    else:
                        source = CreateUML.define_field_limits(CreateUML.get_value_for('source', command_dict),
                                                               'uml_object')
                        destination = CreateUML.define_field_limits(CreateUML.get_value_for('destination', command_dict),
                                                                    'uml_object')

                    self.uml('uml_body',source=source,action=action,destination=destination,note=note)

                if action == 'self-annotation':
                    destination = self_node
                    source = self_node
                    new_note = self.setup_note(each_step)
                    self.uml('uml_body',source=source,action='->',destination=destination,note=new_note)

                if action == 'note left':
                    new_note = self.setup_note(each_step, True)
                    self.uml('uml_body',f'note left\n{new_note}\nend note')

                if action == 'note right':
                    new_note = self.setup_note(each_step, True)
                    self.uml('uml_body',f'note right\n{new_note}\nend note')

        self.uml('uml_start', ['@startuml', 'hide unlinked'])

        if Configs.get_config(section="UML_CONFIG", param="title"):
            start_key = min(uml_objects.keys())
            end_key = max(uml_objects.keys())
            time_format = uml_objects[start_key][0].get(UMLStep.Attribute.TIMESTAMP_FMT)
            start_timestamp = uml_objects[start_key][0].get(UMLStep.Attribute.TIMESTAMP)
            end_timestamp = uml_objects[end_key][0].get(UMLStep.Attribute.TIMESTAMP)

            elapsed_time = (end_timestamp - start_timestamp).seconds

            if elapsed_time > 60:
                time_msg = f'{elapsed_time / 60:.2f} minute(s).'
            else:
                time_msg = f'{elapsed_time:.4f} seconds.'

            self.uml('uml_start', instruction=Configs.get_config(section="UML_CONFIG", param="title",sub_param="CONTENT"))

            title = [
                'title',
                #'Tracer for %s: %s' % (self.corda_object.type, self.corda_object.data["id_ref"]),
                f'| Reference | {self.corda_object.data["id_ref"]} |',
                f'| Type     | {self.corda_object.type} |',
                f'| Started  | {start_timestamp.strftime(time_format)} |',
                f'| Finished | {end_timestamp.strftime(time_format)} |',
                f'| Elapsed time | {time_msg} |',
                'end title'
            ]
            self.uml('uml_start', instruction=title)
            self.uml('uml_start', instruction=CreateUML.verified_participants)

        self.uml('uml_end', '@enduml')

        return self.get_uml_script()

    def uml(self, section, instruction=None, source=None, action=None, destination=None, note=None):
        """
        Generate a string representing actual UML step
        :param section: refer to uml section
        :param source: starting point of message
        :param action: Action, send/receive
        :param destination: end point
        :param note: a note over
        :return: uml step
        """

        highlight = None

        # if note:
        for each_highlight in self.highlight_check:
            check = None
            if note:
                check = self.highlight_check[each_highlight]['REGEX'].search(note)
            if isinstance(instruction, str):
                check = self.highlight_check[each_highlight]['REGEX'].search(instruction)
            if check:
                highlight = each_highlight
                break

        if section == 'uml_body':
            if not instruction:
                uml_str = f'"{source}" {action} "{destination}": {note}'
            else:
                uml_str = f"{instruction}"

            if highlight:
                for each_step in self.highlight_check[highlight]['UML_COMMAND']:
                    action, command = each_step.split('|')
                    if 'BODY' in each_step:
                        command = uml_str

                    self.final_uml[section].append(command)
            else:
                self.final_uml[section].append(uml_str)

            return

        if section == 'uml_start' or section == 'uml_end':
            if isinstance(instruction, list):
                self.final_uml[section].extend(instruction)
            if isinstance(instruction, str):
                uml_str = f'{instruction}'
                self.final_uml[section].append(uml_str)

    def get_uml_script(self, section=None):
        """
        Will return all uml instructions collated in a single list
        :return: a list of strings
        """
        final_uml = []
        if not section:
            for each_section in self.final_uml:
                if each_section == 'uml_body':
                    result = self.optimize_highlight_blocks(each_section)
                    final_uml.extend(result)
                else:
                    final_uml.extend(self.final_uml[each_section])

            return final_uml

        if section in self.final_uml:
            return self.final_uml[section]
        else:
            return None

    def create_script(self, steps_block=None, include_header=True, page=None):
        """
        Genera el script UML para un bloque específico

        :param steps_block: OrderedDict de UMLSteps (ej: {266: [step1], 270: [step2], ...})
        :param include_header: Si True, incluye @startuml, título y participantes
        :return: List[str] con las líneas del script UML
        """
        if steps_block is None:
            steps_block = self.corda_object.get_uml()

        # Reiniciar final_uml para esta página
        self.final_uml = OrderedDict({
            'uml_start': [],
            'uml_body': [],
            'uml_end': []
        })

        # Cabecera opcional
        if include_header:
            self._add_header( page)

        # Cuerpo del diagrama

        self_node = self.file_management.get_party_role('log_owner')
        if self_node and isinstance(self_node, list):
            self_node = self_node[0]

        for line_key in steps_block:
            for each_step in steps_block[line_key]:
                command_dict = each_step.get(UMLStep.Attribute.UML_COMMAND_DEFINITION)
                action = each_step.get(UMLStep.Attribute.UML_COMMAND)

                if action in ['<-','->']:
                    note = self.setup_note(each_step)
                    if action == '<-':
                        source = CreateUML.define_field_limits(CreateUML.get_value_for('destination', command_dict),
                                                               'uml_object')
                        destination = CreateUML.define_field_limits(CreateUML.get_value_for('source', command_dict),
                                                                    'uml_object')
                    else:
                        source = CreateUML.define_field_limits(CreateUML.get_value_for('source', command_dict),
                                                               'uml_object')
                        destination = CreateUML.define_field_limits(CreateUML.get_value_for('destination',
                                                                                            command_dict),
                                                                    'uml_object')
                    self.uml('uml_body', source=source, action=action, destination=destination, note=note)

                elif action == 'self-annotation':
                    new_note = self.setup_note(each_step)
                    self.uml('uml_body', source=self_node, action='->', destination=self_node, note=new_note)

                elif action in ['note left', 'note right']:
                    new_note = self.setup_note(each_step, True)
                    note_type = 'left' if action == 'note left' else 'right'
                    self.uml('uml_body', f'note {note_type}\n{new_note}\nend note')

        # Pie de página
        self.uml('uml_end', '@enduml')

        return self.get_uml_script()

    def _add_header(self, page):
        """
        Añade el encabezado del diagrama (título, participantes, etc.)
        """
        if self.final_uml['uml_start']:  # Evitar duplicados
            return

        # Iniciar el diagrama
        self.uml('uml_start', ['@startuml', 'hide unlinked'])

        # Añadir título (opcional)
        if Configs.get_config(section="UML_CONFIG", param="title"):
            color_scheme = Configs.get_config(section="UML_CONFIG", param="title",sub_param="CONTENT")
            self.uml('uml_start', instruction=color_scheme)
            self.uml('uml_start', instruction=[f'header Page {page} of {self.pages}'])
            self.uml('uml_start', instruction=[f'footer Page {page} of {self.pages}'])
            self.uml('uml_start', instruction=self.title)

        # Añadir participantes verificados
        self.uml('uml_start', instruction=CreateUML.verified_participants)
        # Opcional: otros elementos comunes (ej: estilo, temas, etc.)

    def generate_uml_pages(self, client_name,ticket, steps_per_page=25, output_prefix="uml_page"):
        """
        Genera múltiples archivos UML, uno por página

        :param steps_per_page: cantidad de pasos por página
        :param output_prefix: nombre base para los archivos de salida
        :return: lista de nombres de archivo generados
        """

        self.analyse_uml()
        self.setup_endpoints_and_verify_participants()
        # Obtener todos los pasos UML
        uml_objects = self.corda_object.get_uml()

        if not uml_objects:
            write_log(f'{self.corda_object.data["id_ref"]}: Has not valid UML representation steps...', level='WARN')
            return None

        app_path = os.path.dirname(os.path.abspath(__file__))

        save_path = f"{app_path}/plugins/plantuml_cmd/data/{client_name}/{ticket}"

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # Before creating blocks I need to pull information about time used
        # from first time reference appears
        # until last line; basically will need to build 'title' header
        if Configs.get_config(section="UML_CONFIG", param="title"):
            line_keys = sorted(uml_objects.keys())
            first_step = uml_objects[line_keys[0]][0]
            last_step = uml_objects[line_keys[-1]][0]

            start_timestamp = first_step.get(UMLStep.Attribute.TIMESTAMP)
            end_timestamp = last_step.get(UMLStep.Attribute.TIMESTAMP)
            time_format = first_step.get(UMLStep.Attribute.TIMESTAMP_FMT)

            elapsed_time = (end_timestamp - start_timestamp).seconds
            time_msg = f'{elapsed_time / 60:.2f} min' if elapsed_time > 60 else f'{elapsed_time:.4f} s'

            self.title = [
                'title',
                f'| Reference | {self.corda_object.data["id_ref"]} |',
                f'| Type      | {self.corda_object.type} |',
                f'| Started   | {start_timestamp.strftime(time_format)} |',
                f'| Finished  | {end_timestamp.strftime(time_format)} |',
                f'| Duration  | {time_msg} |',
                'end title'
            ]

        # Dividir en bloques de tamaño steps_per_page
        chunks = UMLStepSetup.chunked_dict(uml_objects, steps_per_page)
        self.pages = len(chunks)
        generated_files = []

        # Generar cada página
        for i, chunk in enumerate(chunks, 1):
            page_script = self.create_script(chunk, include_header=True, page=i)
            filename = f"{save_path}/{output_prefix}_page_{i}.puml"
            with open(filename, "w") as f:
                f.write("\n".join(page_script))
            generated_files.append(filename)

        write_log(f"✅ {len(generated_files)} UML files created")
        return generated_files

    def optimize_highlight_blocks(self, section):
        """

        :param section:
        :return:
        """
        uml_lines = self.final_uml[section]
        commands = {}
        for each_highlight in self.uml_highlight:
            for each_command in self.uml_highlight[each_highlight]['UML_COMMAND']:
                action, command = each_command.split('|')
                commands[action] = command

        for i,each_line in enumerate(uml_lines):
            if each_line.startswith(commands['START']):
                if uml_lines[i-1] == commands['END']:
                    uml_lines[i] = ""
                    uml_lines[i-1] = ""

        return  [line for line in uml_lines if line]

    def optimize_highlight_blocks_ia(self, section):
        """
        Fusiona bloques de error consecutivos en un solo `alt#Gold #Pink Error`

        :param uml_lines: Lista de líneas UML (ej: final_uml['uml_body'])
        :return: Lista optimizada
        """

        uml_lines = self.final_uml[section]

        result = []
        i = 0
        in_error_block = False

        while i < len(uml_lines):
            line = uml_lines[i]

            # Inicio de un bloque de error
            if line.startswith("alt#Gold #Pink Error"):
                if in_error_block:
                    # Si ya estamos en un error, ignoramos el nuevo `alt`
                    i += 1
                    continue
                else:
                    result.append("alt#Gold #Pink Error")
                    in_error_block = True
                    i += 1
                    continue

            # Fin de un bloque de error
            if line.strip() == "end" and in_error_block:
                # Solo cerramos el grupo si el siguiente no es otro error
                j = i + 1
                if j < len(uml_lines) and uml_lines[j].startswith("alt#Gold #Pink Error"):
                    i += 1  # Saltamos el 'end' si viene otro error
                    continue
                else:
                    result.append("end")
                    in_error_block = False
                    i += 1
                    continue

            # Si no es parte de un error, lo agregamos directamente
            if not in_error_block:
                result.append(line)
                i += 1
                continue

            # Si estamos dentro de un error, agregamos la línea al bloque
            if in_error_block and not line.startswith("alt#") and not line.startswith("note"):
                result.append(line)
                i += 1
                continue

            # Si dentro del error aparece una nota u otro elemento, cerramos el grupo temporalmente
            if in_error_block and (line.startswith("note") or line.startswith("alt#")):
                result.append("end")
                in_error_block = False
                result.append(line)
                i += 1
                continue

        return result

    @staticmethod
    def get_value_for(key, command_dict):
        """
        Retorna el "Key" de un diccionario invertido, esto es, buscar el valor y retornar la clave
        :param key: clave a buscar
        :return: valor requerido
        """

        if key in command_dict:
            rvalue = command_dict[key]
            if '|' in rvalue:
                _, tmp = rvalue.split('|')
                return tmp
            else:
                # if not '|' is in the value
                return rvalue

        # The actual key puede que no este en el diccionario como 'key' pero puede que haya un patron de ellas,
        # por ejemplo varias anotaciones 'annotation_0...' en este caso las busco todas y las retorno como una lista
        str_pattern = f'^{key}(|[0-9]+)?$'
        pattern = re.compile(str_pattern)
        if pattern:
            return {k: command_dict[k] for k in command_dict if pattern.match(k)}

        return None

        # keyword = next((k for k, v in command_dict.items() if v == key), None)
        #
        # if keyword and  '|' in  keyword:
        #     _, tmp = keyword.split('|')
        #     keyword = tmp

        # return keyword

    @staticmethod
    def define_field_limits(value, uml_definition):
        """
        This method will apply text limits, and wrap its contents depending of length defined on configuration
        :param uml_definition: actual UML definition (uml_object, '->', '<-', etc)
        :param value: Text that need to be checked/limited
        :return: string with the actual value wrapped text using "\n" where is required...
        """

        max_len = {}
        # Setup an alias for max_len for easy handling
        for each_item in Configs.get_config(section="UML_DEFINITIONS"):
            if "MAX_LEN" in Configs.get_config(section="UML_DEFINITIONS", param=each_item):
                max_len[each_item] = Configs.get_config(section="UML_DEFINITIONS",
                                                        param=each_item)["MAX_LEN"]
        if uml_definition in max_len:
            if uml_definition == "note left":
                response = textwrap.fill("%s" % (value,), max_len[uml_definition])
            else:
                response = textwrap.fill("%s" % (value,), max_len[uml_definition]).replace("\n", "\\n")
        else:
            response = value

        return response

    @staticmethod
    def datetime2strtime(datetime_obj: datetime, fmt) -> str:
        """
        Transform datetime object into str
        :param datetime_obj: object datetime to transform
        :return:
        """

        timestamp = datetime.strftime(datetime_obj, fmt)

        return timestamp

    def setup_note(self, uml_step, side_note=False):
        """

        :return:
        """


        uml_fields = uml_step.get(UMLStep.Attribute.FIELDS)

        uml_fields['timestamp'] = CreateUML.datetime2strtime(uml_step.get(UMLStep.Attribute.TIMESTAMP),
                                                             uml_step.get(UMLStep.Attribute.TIMESTAMP_FMT))
        uml_fields['line'] = f"{uml_step.get(UMLStep.Attribute.LINE_NUMBER)}"

        # Note formatting for some extra data types
        formatting = OrderedDict({
            'line':'<b>Line number:<b> %s\\n',
            'timestamp': "<b>Time stamp:</b>\\n%s\\n",
            'tx_id': "<b>Transaction:</b>\\n%s\\n",
            'flow_id': "<b>Flow:</b>\\n%s\\n",
            'message': "<b>Message:</b>\\n%s"
        })

        # Delete unnecessary data from messages as this is being stated at the top title
        if self.corda_object.type == 'TRANSACTION':
            del formatting['tx_id']

        if self.corda_object.type == 'FLOW':
            del formatting['flow_id']

        final_note = []

        # fill information available from uml_step
        for each_item in formatting:
            if each_item in uml_fields:
                if each_item == 'message':
                    if uml_step.get(UMLStep.Attribute.UML_COMMAND) == 'note left':
                        uml_fields[each_item] = CreateUML.define_field_limits(uml_fields[each_item],
                                                                              'note left')
                    else:
                        uml_fields[each_item] = CreateUML.define_field_limits(uml_fields[each_item], 'self-annotation')

                if not side_note:
                    final_note.append(formatting[each_item] % uml_fields[each_item])
                else:
                    # It seems, side notes do not manage '\n' as carrige return, I will simulate
                    # a hard cr adding a new item to `final_note`
                    tmpfrmt = formatting[each_item].replace('\\n','')
                    tmpfrmt = tmpfrmt.replace('%s','')
                    final_note.append(tmpfrmt)
                    final_note.append(uml_fields[each_item])
        if not side_note:
            note = "".join(final_note)
        else:
            note = "\n".join(final_note)

        return note

    def verify_participant(self, participant):
        """
        Check participant
        :param participant: possible x500 name or control entity
        :return: true if is ok false otherwise
        """
        rules = self.file_management.rules['RULES']

        check = X500NameParser(rules)
        verified = check.parse_line(participant, [])

        return verified

    def analyse_uml(self):
        """
        Using corda_object, extract all steps within this object and analyse them to complete essential parts
        like source or destination
        :return:
        """
        uml_requiring_endpoints = ['<-','->']
        uml_endpoint_literal = ['source','destination']


        # Iterate over all UMLs
        for each_batch in self.corda_object.get_uml():
            # Batch contains a list of UMLs so I need to see one by one
            for each_step in self.corda_object.get_uml(each_batch):
                write_log(f"{each_batch}: {each_step.get(UMLStep.Attribute.UML_COMMAND)}")

                # Analyse given UML so it define initial fields, like source, destination, participants, message, etc
                each_step.analyse()
                if ('note' in each_step.get(UMLStep.Attribute.UML_COMMAND) or
                        'self-annotation' in each_step.get(UMLStep.Attribute.UML_COMMAND)) :
                    write_log(f'   `---> message: {each_step.get(UMLStep.Attribute.FIELDS)["message"]}')

                # Prepare a dictionary to gather endpoints, with this I will know if an endpoint is missing (either
                # source or destination)
                end_point_step = {}
                require_endpoint = False

                # Check if command require an endpoint (like '->' or '<-')
                if each_step.get(UMLStep.Attribute.UML_COMMAND) in uml_requiring_endpoints:
                    require_endpoint = True
                    for each_endpoint_literal in uml_endpoint_literal:
                        if each_endpoint_literal in each_step.get(UMLStep.Attribute.UML_COMMAND_DEFINITION):
                            each_definition_value = each_step.get(UMLStep.Attribute.UML_COMMAND_DEFINITION)[each_endpoint_literal]
                            if '|' in each_definition_value:
                                _,end_point_step[each_endpoint_literal] = each_definition_value.split('|')
                            else:
                                end_point_step[each_endpoint_literal] = each_definition_value

                # If an endpoint is required, check which one is missing
                #
                if require_endpoint:
                    missing_endpoint = list(set(uml_endpoint_literal) - set(list(end_point_step.keys())))
                    # write_log(f"Missing endpoint: {missing_endpoint}")
                    message_line = each_step.get(UMLStep.Attribute.LINE_MESSAGE)
                    for each_endpoint in missing_endpoint:
                        default_usage = f'default_{each_endpoint}'
                        # get a list of all entity default endpoints,this will help to find out missing endpoint
                        #
                        for each_entity in UMLEntityEndPoints.get_default_endpoints():
                            ep = UMLEntityEndPoints.get_default_endpoints(each_entity)
                            rgx_list = ep.get_usages(default_usage, True)
                            # Now check which one match correct endpoint... get all regex to compare

                            rgx_to_use = RegexLib.regex_to_use(rgx_list, message_line, True)

                            if rgx_to_use is not None:

                                if ep.name == 'log_owner':
                                    if self.file_management.get_party_role('log_owner'):
                                        ep.name = self.file_management.get_party_role('log_owner')[0]

                                endp = f'{ep.UML_REPRESENTATION}|{ep.name}'

                                each_step.add_into_attribute(UMLStep.Attribute.UML_COMMAND_DEFINITION, endp, each_endpoint)
                                break

                    # check both endpoints are set
                    ep_check = list(uml_endpoint_literal)
                    cpy_command_list = dict(each_step.get(UMLStep.Attribute.UML_COMMAND_DEFINITION))
                    ref_command_list = each_step.get(UMLStep.Attribute.UML_COMMAND_DEFINITION)
                    for each_ep in cpy_command_list:
                        value = cpy_command_list[each_ep]
                        if each_ep in ep_check:
                            write_log(f'   `--> {each_ep}: {value}')
                            write_log(f'        note: {CreateUML.get_value_for("note over", each_step.get(UMLStep.Attribute.UML_COMMAND_DEFINITION))}')
                            # collect participant list
                            if '|' in value:
                                _, participant = value.split('|')
                                check = self.verify_participant(participant)
                                if check:
                                    # this will make sure that only clean names are introduced
                                    #
                                    del ref_command_list[each_ep]
                                    participant = check[0].name
                                    ref_command_list[each_ep] = f'{_}|{participant}'

                                CreateUML.add_unverified_participant(participant)

                            ep_check.remove(each_ep)

                    if ep_check:
                        write_log(f"   *** Missing {ep_check}", level="WARN")
    @staticmethod
    def render_uml(file):

        # TODO: Implementar esta rutina para generar los archivos de imagen
        import subprocess
        app_path = os.path.dirname(os.path.abspath(__file__))

        success = False
        if isinstance(file, list):
            for each_file in file:
                status = subprocess.call(['java', '-jar',
                                 f'{app_path}/plugins/plantuml_cmd/plantuml.jar',
                                 '-tsvg',
                                 '-quiet',
                                 f'{each_file}'])

                status1 = subprocess.call(['java', '-jar',
                                 f'{app_path}/plugins/plantuml_cmd/plantuml.jar',
                                 '-tutxt',
                                 '-quiet',
                                 f'{each_file}'])

                if status+status1 == 0:
                    success = True


        else:
            status = subprocess.call(['java', '-jar',
                             f'{app_path}/plugins/plantuml_cmd/plantuml.jar',
                             '-tsvg',
                             '-quiet',
                             f'{file}'])
            if status == 0:
                success = True

        return  success