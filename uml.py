import re
from enum import Enum
from object_class import generate_internal_access, Configs, CordaObject, RegexLib


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
        line_message = self.get(UMLStep.Attribute.LINE_MESSAGE)

        match = self.get(UMLStep.Attribute.REGEX_COMPILED).search(line_message)
        # Extract any defined field on this line
        fields = match.groupdict()
        if fields:
            self.set(UMLStep.Attribute.FIELDS, fields)

        # Try to extract all fields on this line (expected_fields)
        for each_field in expected_fields:
            action,field = each_field.split(':')
            #
            # Check if I have value for given field
            if field in fields and field not in uml_actions:
                # collect appropriate uml action for this field
                uml_actions[action] = fields[field]
                # then get next one
                for each_obj in uml_corda_objects.keys():
                    if field in ",".join(uml_corda_objects[each_obj]['EXPECT']):
                        new_uml_step = UMLStep()
                        new_uml_step.copy(self)

                continue

            # Unable to get proper definition from extracted fields, so then look for another way
            # to extract such information...
            #

            definition = CordaObject.get_corda_object_definition_for(field)

            if definition:
                if isinstance(definition, str):
                    definition = [definition]
                for each_definition in definition:
                    pattern = RegexLib.build_regex(each_definition)
                    check = re.search(pattern, line_message)
                    if check:
                        uml_actions[f"{field}={check.group(1)}"] = action
                        break

        return uml_list


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


    # def copy(self, original):
    #     """
    #     Create a copy of given UMLStep
    #     :param original: Original UMLStep to copy from
    #     :return: void
    #     """
    #
    #     for key, value in original.__dict__.items():
    #         setattr(self, key, deepcopy(value))

class UMLStepSetup:
    uml_candidate_steps = []
    Configs = None
    file = None
    uml_definitions = {}
    full_rule_search = None

    def __init__(self, get_configs):
        """
        Class initialization
        """

        UMLStepSetup.Configs = get_configs
        UMLStepSetup.file = None
        self.type = None
        # Load actual "patterns" to look for that can identify a potential UML step...
        #
        if not UMLStepSetup.uml_definitions:
            tmp = UMLStepSetup.Configs.get_config_for("UML_DEFINITIONS")
            for each_cmd in tmp:
                if 'COMMAND' in tmp[each_cmd]:
                    UMLStepSetup.uml_definitions[each_cmd] = tmp[each_cmd]

    @staticmethod
    def check_for_uml_step(original_line, current_line_no):
        """
        Pre-load all required regex to speed up searches.
        :return:
        """

        umlsteps_list = []

        for each_uml_definition in UMLStepSetup.uml_definitions:
            # now for each uml definition, try to see if we have a match
            #
            # Stage 1: Find out which UML command should be applied to given line, as all UML_DEFINITIONS are
            # created as "meta-definitions" I need below line to extract actual regex that need to be used...
            # In this section, i will loop over all defined UML commands, and find out if this line match any of them
            #
            # NOTE: THIS METHOD DO NOT RECOGNISE IF WHAT IT FOUND IS EITHER A TX OR A FLOW...

            list_of_expects_to_try = UMLStepSetup.uml_definitions[each_uml_definition]["EXPECT"]

            expect_to_use = RegexLib.regex_to_use(list_of_expects_to_try, original_line)

            if expect_to_use is None:
                # If we do not have any valid regex for this line, try next list
                continue

            regex_expect = list_of_expects_to_try[expect_to_use]

            each_expect = RegexLib.build_regex(regex_expect)
            umlstep = UMLStep()
            umlstep.set(UMLStep.Attribute.LINE_NUMBER, current_line_no)
            umlstep.set(UMLStep.Attribute.LINE_MESSAGE, original_line)
            # umlstep.set_attribute(UMLStep.Attribute.TYPE, UMLStepSetup.uml_definitions[each_uml_definition]["EXPECT"][expect_to_use])
            umlstep.set(UMLStep.Attribute.UML_COMMAND, each_uml_definition)
            umlstep.set(UMLStep.Attribute.REGEX_TO_APPLY, each_expect)
            umlstep.set(UMLStep.Attribute.REGEX_COMPILED, re.compile(each_expect))
            umlstep.set(UMLStep.Attribute.REGEX_INDEX, expect_to_use)
            umlsteps_list.append(umlstep)
            uml_analysis = umlstep.analyse()
            # for each_step in uml_analysis:
            #     UMLStepSetup.uml_candidate_steps.append(each_step)
            #     umlsteps_list.append(each_step)

            # # Remove used expect to do not use it again, and repeat same thing.
            # list_of_expects_to_try.pop(expect_to_use)

        if umlsteps_list:
            return umlsteps_list
        else:
            return None


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
            # if key == 'USAGES':
            #     for each_usage in entity_details['USAGES']:
            #         setattr(self, each_usage, entity_details['USAGES'][each_usage])
            # else:
            setattr(self, key, entity_details[key])

        UMLEntityEndPoints.endpoint_list[entity_name] = self

    def get_usages(self, usage_case=None, expect_list=False, ignore_list=False):
        """
        Return actual usages details of current endpoint
        :usage_case: which usage case you want to have details on
        :return: actual usage case if is different of None, otherwise will return all current usages cases
        """

        if not usage_case:
            return list(self.USAGES.keys())

        if usage_case and usage_case not in self.USAGES.keys():
            return None

        if expect_list:
            return self.USAGES[usage_case]['EXPECT']

        if ignore_list:
            return self.USAGES[usage_case]['IGNORE']

        return None

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
    def get_entity_endpoint(cls, entity_name):
        """
        Will return given entity name endpoint if it is found
        :param entity_name: entity role name to look for
        :return: entity endpoint object
        """

        if entity_name in cls.endpoint_list:
            return cls.endpoint_list[entity_name]

        return None

