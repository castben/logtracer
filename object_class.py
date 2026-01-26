import concurrent.futures
import hashlib
import json
import mmap
import os,time
import regex as re
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import numpy as np
from typing import List, Tuple, Dict, Optional
from log_handler import write_log
from shutdown_event import shutdown_event
from support_icons import Icons
from ui_commands import schedule_ui_update
import signal
from contextlib import contextmanager

class CordaObject:
    """
    This class object will hold all transaction results and many other useful objects
    """
    # This represents all ID's registered so far
    id_ref = []
    # This keep a list of all instances of this class
    list = {}
    relations = {}
    # Default UML references
    # This represents entities endpoints (for source and destination)
    default_uml_endpoints = {}
    # To store all uml setup
    uml = {}
    # Setup uml participants and initial fields
    uml_init = []
    uml_active_participants = []
    # An auxiliary field to allow me find out what are additional fields that need to be added to final summary table
    additional_table_fields = []
    # List of all participants; and roles
    uml_participants = {}
    # Reference registration: this will register each reference that "visit" a "UML_DEFAULT" object if proper flag is
    # enabled
    entity_register = {}
    # Define current object as Log Owner
    log_owner = None
    # References
    corda_object_regex = []
    corda_object_types = []

    # Clear group names cache
    #
    clear_group_list = {}

    def __init__(self):
        self.data = {}
        self.reference_id = None
        self.references = OrderedDict()
        self.type = None
        self.line_number = None
        self.timestamp = None
        self.error_level = None
        self.uml_steps = OrderedDict()
        self._uml_steps_lock = threading.RLock()  # ✅ Lock para acceso seguro

    def to_dict(self):
        """Convierte el objeto a diccionario serializable"""
        return {
            'reference_id': self.reference_id,
            'type': self.type,
            'line_number': self.line_number,
            'timestamp': self.timestamp,
            'error_level': self.error_level,
            'data': self.data,
            'references': dict(self.references),
            'uml_steps': self._serialize_uml_steps(),
        }

    def from_dict(self, data: dict):
        """Crea objeto desde diccionario"""
        self.reference_id = data.get('reference_id')
        self.type = data.get('type')
        self.line_number = data.get('line_number')
        self.timestamp = data.get('timestamp')
        self.error_level = data.get('error_level')
        self.data = data.get('data', {})
        self.references = OrderedDict(data.get('references', {}))
        self._deserialize_uml_steps(data.get('uml_steps', {}))
        return self

    def _serialize_uml_steps(self):
        """Serializa OrderedDict de UMLSteps"""
        serialized = {}
        for line_num, steps in self.uml_steps.items():
            serialized[str(line_num)] = [step.__dict__ for step in steps]
        return serialized

    def _deserialize_uml_steps(self, serialized):
        """Deserializa OrderedDict de UMLSteps"""
        self.uml_steps = OrderedDict()
        for line_num_str, steps_data in serialized.items():
            line_num = int(line_num_str)
            steps = []
            for step_data in steps_data:
                # Aquí debes recrear tu objeto UMLStep desde el dict
                from uml import UMLStep  # Ajustar import
                step = UMLStep()
                for key, value in step_data.items():
                    setattr(step, key, value)
                steps.append(step)
            self.uml_steps[line_num] = steps

    @classmethod
    def clear_all(cls):
        """
        Clear all base variables for class
        :return:
        """

        # This represents all ID's registered so far
        cls.id_ref = []
        # This keep a list of all instances of this class
        cls.list = {}
        cls.relations = {}
        # Default UML references
        # This represents entities endpoints (for source and destination)
        cls.default_uml_endpoints = {}
        # To store all uml setup
        cls.uml = {}
        # Setup uml participants and initial fields
        cls.uml_init = []
        cls.uml_active_participants = []
        # An auxiliary field to allow me find out what are additional fields that need to be added to final summary table
        cls.additional_table_fields = []
        # List of all participants; and roles
        cls.uml_participants = {}
        # Reference registration: this will register each reference that "visit" a "UML_DEFAULT" object if proper flag is
        # enabled
        cls.entity_register = {}
        # Define current object as Log Owner
        cls.log_owner = None
        # References
        cls.corda_object_regex = []
        cls.corda_object_types = []

        # Clear group names cache
        #
        cls.clear_group_list = {}

    @staticmethod
    def get_clear_group_list(raw_list):
        """
        This method will check if given list is already on memory; otherwise, will process the list, and add it into
        memory for further usage.

        :param raw_list: list that need to be checked
        :return:
        """

        signature = generate_hash("$$".join(raw_list))

        if signature in CordaObject.clear_group_list:
            return CordaObject.clear_group_list[signature]

        return CordaObject.add_clear_group_list(raw_list)

    @staticmethod
    def add_clear_group_list(raw_list):
        """
        Add a new list with all groups cleared
        :param raw_list: list with required groups to be cleared
        :return: initial group given; with no groups names.
        """

        signature = generate_hash("$$".join(raw_list))
        no_group_list = []
        for each_item in raw_list:
            # Expand all macro variables from their pseudo form
            expand_macro = RegexLib.build_regex(each_item, nogroup_name=True)
            # Check how many "group names" are within the given string
            #
            clear_groups = expand_macro
            for each_group in range(expand_macro.count('?P<')):
                start = clear_groups.find('?P<')
                end = clear_groups.find('>')+1
                clear_groups = clear_groups.replace(clear_groups[start:end], "")

            no_group_list.append(clear_groups)

        CordaObject.clear_group_list[signature] = no_group_list

        return no_group_list

    @staticmethod
    def get_cordaobject_regex_definition():
        """

        :return:
        """
        return CordaObject.corda_object_regex

    @staticmethod
    def get_cordaobject_types_definition():
        """

        :return:
        """
        return CordaObject.corda_object_types

    @staticmethod
    def set_cordaobject_regex_definition(corda_regex_definition):
        """

        :return:
        """
        CordaObject.corda_object_regex = corda_regex_definition

    @staticmethod
    def set_cordaobject_types_definition(corda_type_definition):
        """

        :return:
        """
        CordaObject.corda_object_types = corda_type_definition

    @staticmethod
    def reset():
        """
        Clears up actual object class and deletes all info
        :return:
        """
        CordaObject.list = {}
        CordaObject.uml_init = []
        CordaObject.log_owner = None
        CordaObject.uml_participants = {}
        CordaObject.uml_active_participants = []
        CordaObject.additional_table_fields = []
        CordaObject.id_ref = []
        CordaObject.relations = {}


    @staticmethod
    def set_log_owner(log_owner):
        """
        Set actual log owner for analysed log
        :param log_owner: party which is owner/producer of log being analised
        :return: None
        """

        CordaObject.log_owner = log_owner
        # Party.party_expected_role_list.remove('log_owner')



    def add_data(self, cproperty, value):
        """
        Add internal data into instance of this object

        :param cproperty: property name to add
        :param value: value
        :return:
        """
        if not self:
            pass

        if cproperty == 'id_ref':
            self.reference_id = value

        if cproperty == 'line_number':
            self.line_number = value

        if cproperty in self.data:
            # If property already exist, I need to keep its previous value, and add new one
            if not isinstance(self.data[cproperty], list):
                tmpdata = self.data[cproperty]
                # convert this field to a list
                self.data[cproperty] = [tmpdata]
                return

            if isinstance(self.data[cproperty], list):
                self.data[cproperty].append(value)
                return


        self.data[cproperty] = value

        # Extract extra data
        if isinstance(value, str) and  "=" in value:
            if ";" in value:
                for each_data in value.split(";"):
                    if not each_data:
                        continue
                    values = each_data.split("=")
                    if len(values) > 1:
                        self.data[values[0].strip()] = values[1].strip().replace("}", "")

            for each_data in value.split(","):
                if not each_data:
                    continue
                values = each_data.split("=")
                if values:
                    if len(values) > 1:
                        self.data[values[0].strip()] = values[1].strip().replace("}", "")

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp

    def set_error_level(self, error_level):
        self.error_level = error_level

    def set_type(self, object_type):
        self.type = object_type

    def set_line_number(self, line_number):
        self.line_number = line_number

    def set_reference_id(self, reference_id):
        self.data['id_ref'] = reference_id
        self.reference_id = reference_id

    def get_uml(self, line_number=None):
        """
        Will return specified UML representation for given line
        :param line_number: log line number
        :return: uml representation for given line, or all of them if no line is give(dictionary), None if no line found
        """

        if not line_number:
            return self.uml_steps

        if line_number in self.uml_steps:
            return self.uml_steps[line_number]

        return None

    def get_timestamp(self):
        return self.timestamp

    def get_error_level(self):
        return self.error_level

    def get_reference_id(self):
        return self.reference_id

    def get_line(self):
        return self.line_number

    def get_type(self):
        return self.type

    def get_data(self, data_property):
        """
        Return value
        :param data_property:
        :return:
        """

        if data_property in self.data:
            return self.data[data_property]
        else:
            return None

    def get_relationship(self):
        """
        Will check what fields will be key to make relationships between transactions/flows
        :return:
        """

        relation = Configs.get_config("IDENTIFICATION", self.type, "OBJECT")

        if not relation:
            write_log("No relationship defined for %s" % self.type)
            return None

        return relation

    def add_object(self):
        """
        Add given object into internal class list of objects
        :return:
        """

        if self.type not in CordaObject.list:
            CordaObject.list[self.type] = OrderedDict()

        if self.data["id_ref"] not in CordaObject.id_ref:
            # Add a new reference found into the list
            CordaObject.id_ref.append(self.data["id_ref"])

        if self.data["id_ref"] not in CordaObject.list[self.type]:
            CordaObject.list[self.type][self.data["id_ref"]] = self

    def add_relation(self):
        """

        :return:
        """

        if self.type not in CordaObject.relations:
            CordaObject[self.type] = {}

        relations = self.get_relationship()

    def add_uml_step(self, line, umlstep):
        """
        Add umlstep related to this object
        :param line: Line number corresponding to log line
        :param umlstep: UMLStep object associated to this line
        :return:
        """
        with self._uml_steps_lock:  # ✅ Proteger escritura
            self.uml_steps[line] = umlstep

    # def load_from_database(self):
    #     """
    #
    #     :return:
    #     """
    #     global database
    #     # TODO: Aqui estoy tratando de cargar las referencias por "demanda" esto ayudara a cargar las cosas
    #     #  cuando sean necesarias lo cual servira cuando hay miles de referencias... este metodo carga
    #     #  la referencia que es requerida, ahora bien creo que tengo que revisar la re-asignacion porque el
    #     #  objeto va a sobre escribir la seccion `data` que contiene mucha informacion... de verda es requerido???
    #     #
    #     #
    #
    #     query = database.query(support.TracerReferences).filter(and_(
    #         support.TracerReferences.logfile_hash_key == self.get_data('logfile_hash_key'),
    #         support.TracerReferences.logfile_hash_key == self.get_data('id_ref')).order_by(
    #         support.TracerReferences.line_no)
    #     ).all()
    #
    #     for each_reference in query:
    #         self.add_reference(each_reference.line_no, json.loads(each_reference.details))
    #         self.data = json.loads(each_reference.data)


    @classmethod
    def add_uml_participant(cls, uml_participant):
        """
        Add a uml participant, program need to search for valid participants (x500 names) or
        a specific special participant like control unit (Flow Hospital) or database (Vault)
        :param uml_participant: participant to be added
        :return:
        """



        pass


    def get_references(self, line_no=None, field=None):
        """
        Will return all objects where this reference was found.

        :param line_no: this is the line number to get from references
        :param field: If field is valid from reference storage this will be returned.
        :return: depends on parameters given (list, dictionary, or string)
        """

        # Check if object has references

        if not self.references:
            return None

        if self.references and not line_no and not field:
            return self.references

        if self.references and line_no and not field:
            if line_no in self.references:
                return self.references[line_no]
            else:
                return None

        # if there's no line_no reference, I can't return proper reference, or I got the line_no, but that line is not
        # in the references, then return None

        if not line_no or line_no and line_no not in self.references:
            return None

        if field:
            if field in self.references[line_no]:
                return self.references[line_no][field]

        return None

    @staticmethod
    def add_register(control, reference, reference_type, state, line_no, cause=None):
        """
        Will add given reference into control section, this will highlight and count number of references on each
        control entity (like flow hospital)
        :param cause: reason why need to be registered
        :param reference_type: of reference ID
        :param state: This state is coming from actual config file; Entity setup
        :param line_no: actual line number
        :param reference: reference ID
        :param control: name of control entity (like flowhospital)
        :return:
        """

        if control not in CordaObject.entity_register:
            CordaObject.entity_register[control] = {
                "state": state
            }

        if reference_type not in CordaObject.entity_register[control]:
            CordaObject.entity_register[control][reference_type] = {}

        if reference not in CordaObject.entity_register[control][reference_type]:
            CordaObject.entity_register[control][reference_type][reference] = {
                "lines": {line_no: cause}
            }
        else:
            if line_no not in CordaObject.entity_register[control][reference_type][reference]["lines"]:
                CordaObject.entity_register[control][reference_type][reference]["lines"][line_no] = cause

    @staticmethod
    def set_participant_role(participant, role, attach_usages=False):
        """
        Method that will setup properly endpoint and attach endpoint references if is possible
        This will help for example to set the log Owner, this will help with messages that do not explicitly give
        source or destination of message
        :param participant: a string (essentially a Party / uml_object)
        :param role: role that need to be setup for this uml_object
        :param attach_usages: Will indicate if default values will be attached to the default_uml_endpoints

        :return: void
        """
        party = Party.get_party(participant)
        party.set_corda_role(role)
        if role == "log_owner":
            CordaObject.set_log_owner(participant)

        if attach_usages:
            for each_crole in party.get_corda_roles():
                if Configs.get_config(section="UML_ENTITY", param="OBJECTS", sub_param=each_crole):
                    default_endpoint = Configs.get_config(section="UML_ENTITY", param="OBJECTS", sub_param=each_crole)
                    if "USAGES" in default_endpoint:
                        if participant not in CordaObject.default_uml_endpoints:
                            CordaObject.default_uml_endpoints[participant] = default_endpoint["USAGES"]
                            CordaObject.default_uml_endpoints[participant]["ROLE"] = [each_crole]
                        else:

                            additional_endpoints = Configs.get_config_for(f"UML_ENTITY.OBJECTS.{each_crole}.ROLE")
                            check_roles = CordaObject.default_uml_endpoints[participant]['ROLE']
                            if each_crole in check_roles:
                                # if usage group was already added for this role, skip
                                continue
                            additional_endpoints = Configs.get_config_for(f"UML_ENTITY.OBJECTS.{each_crole}")


                    else:
                        write_log("Unable to attach default usages for '%s': %s" % (each_crole, participant))
                        write_log("Configuration file is not having this config section!")
                else:
                    write_log("There's no config section for '%s' unable to define default properly" % (each_crole,))
                    write_log("Default destination/source will be shown as 'None' at UML")

        # Check if this participant has extra endpoints to attach (A notary for example)
        #
        # if party.get_corda_role():
        #     additional_endpoints = Configs.get_config(section="UML_ENTITY", param="OBJECTS",
        #                                               sub_param=party.get_corda_role().lower())
        #     if party.get_corda_role().lower() in additional_endpoints:
        #         additional_endpoints = additional_endpoints[party.get_corda_role().lower()]
        #     else:
        #         additional_endpoints = None
        #
        #     if additional_endpoints and 'USAGES' in additional_endpoints:
        #         for each_endpoint in additional_endpoints['USAGES']:
        #             additional_usages = additional_endpoints['USAGES'][each_endpoint]['EXPECT']
        #             CordaObject.default_uml_endpoints[participant][each_endpoint]['EXPECT'].extend(additional_usages)

    @staticmethod
    def get_log_owner():
        """
        Will return who is the owner of current log (if it is know)
        :return: String representing a Party / uml_object
        """

        return CordaObject.log_owner

    @staticmethod
    def analyse(original_line, uml_definition, line_no=None):
        """
        Analyse line and covert it into UML
        :return:
        """

        # uml_definition = Configs.get_config(section="UML_DEFINITIONS")
        uml_rtn = {}
        uml_step = {}
        # Loop over all UML definitions

        for each_uml_definition in uml_definition:
            # now for each uml definition, try to see if we have a match
            #
            # Stage 1: Find out which UML command should be applied to given line, as all UML_DEFINITIONS are
            # created as "meta-definitions" I need below line to extract actual regex that need to be used...
            # In this section, i will loop over all defined UML commands, and find out if this line match any of them
            #

            expect_to_use = RegexLib.regex_to_use(uml_definition[each_uml_definition]["EXPECT"], original_line)

            if expect_to_use is None:
                # If we do not have any valid regex for this line, try next list
                continue

            regex_expect = uml_definition[each_uml_definition]["EXPECT"][expect_to_use]
            each_expect = RegexLib.build_regex(regex_expect)
            # each_expect = RegexLib.use(each_expect)
            match = RegexLib.Search(RegexLib.build_regex(each_expect), original_line)
            # match = each_expect.search(original_line)
            if match:
                # rx = RegexLib.Search(build_regex(each_expect), original_line)
                grp = 1
                if match.groupdict():

                    for each_dict in match.groupdict():
                        for each_field in each_dict:
                            ignore = False

                            if 'IGNORE' in uml_definition[each_uml_definition]:
                                for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
                                    if each_ignore_word in original_line:
                                        ignore = True
                            # Check if this specific statement has some specific words that should prevent this
                            # assignation to take place
                            #
                            if not ignore:
                                # CordaObject.add_uml(match.group(grp), each_field)
                                # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)

                                # if match.group(each_field):
                                # grp_value = match.group(each_field).strip().strip(".")
                                grp_value = each_dict[each_field]

                                if "OPTIONS" in uml_definition[each_uml_definition] and \
                                        "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
                                    already_defined = False
                                    for each_definition in CordaObject.uml_init:
                                        if grp_value in each_definition:
                                            already_defined = True
                                    if already_defined:
                                        continue
                                    else:
                                        uml_def = CordaObject.get_corda_object_definition_for(each_uml_definition)
                                        # grp_value = define_field_limits(grp_value, uml_def)
                                        if uml_def:
                                            CordaObject.add_uml_object(grp_value, uml_def)
                                            # CordaObject.uml_init.append('%s "%s"' % (uml_def, grp_value))
                                        else:
                                            CordaObject.add_uml_object(grp_value, each_uml_definition)
                                            # CordaObject.uml_init.append('%s "%s"' % (each_uml_definition,
                                            #                                          grp_value))
                                else:
                                    uml_set = False
                                    # Search each field on given line to see if it exists and extract its value
                                    #
                                    for each_field_def in uml_definition[each_uml_definition]["FIELDS"]:
                                        if ":" in each_field_def:
                                            extract_field = each_field_def.split(":")[1]
                                        else:
                                            extract_field = each_field_def
                                            write_log("Warning: This definition is missing proper labels on regex\n"
                                                  "%s" % each_expect)

                                        # if value for this field already exist on the EXPECTED (default one) then
                                        # get it otherwise, get proper expect to extract it from current log line

                                        if each_field == extract_field:
                                            uml_set = True
                                            uml_rtn[grp_value] = each_field_def
                                            uml_step[each_uml_definition] = uml_rtn

                                    if not uml_set:
                                        write_log("Warning unable to set proper values for group %s, not UML group"
                                              " set on '%s' definition" % (each_field, each_uml_definition))
                                        write_log("Offending line: \n%s" % original_line)

                else:
                    #
                    # TODO: no estoy seguro para que hice esta seccion, por lo que se ve en la logica ^^
                    #  nunca se llegara a alcanzar esta parte porque match.groupdict() "SIEMPRE" devolvera
                    #  un grupo amenos que no tenga la definicion de grupo en el "EXPECT" lo cual seria un error
                    for each_field in uml_definition[each_uml_definition]["FIELDS"]:
                        if grp > len(match.groups()):
                            write_log("Warning: There's no group to cover %s definition on '%s' setting...!" %
                                  (each_field, each_uml_definition))
                            write_log("Scanned line:\n %s" % (original_line,))
                        else:
                            ignore = False
                            if 'IGNORE' in uml_definition[each_uml_definition]:
                                for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
                                    if each_ignore_word in original_line:
                                        ignore = True
                            # Check if this specific statement has some specific words that should prevent this
                            # assignation to take place
                            #
                            if not ignore:
                                # CordaObject.add_uml(match.group(grp), each_field)
                                # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)

                                if match.group(grp):
                                    grp_value = match.group(grp).strip().strip(".")
                                    # grp_value = define_field_limits(grp_value, each_uml_definition)

                                    if "OPTIONS" in uml_definition[each_uml_definition] and \
                                            "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
                                        if '%s "%s"' % (each_uml_definition, grp_value) not in CordaObject.uml_init:
                                            CordaObject.add_uml_object(grp_value, each_uml_definition)
                                            # CordaObject.uml_init.append('%s "%s"' % (each_uml_definition,
                                            #                                          grp_value))
                                        else:
                                            continue
                                    else:

                                        uml_rtn[grp_value] = each_field
                                        uml_step[each_uml_definition] = uml_rtn

                        grp += 1

                    # A match message was found (uml action definition), it doesn't make sense to go through the
                    # rest This will avoid to do a regex of each 'EXPECT' over action UML_DEFINITION
                    #break

            if uml_step and each_uml_definition in uml_step:
                # Will loop over the required fields for this uml action, and try to pull the info on the log line
                # also will skip any field that was already populated
                for each_required_field in uml_definition[each_uml_definition]["FIELDS"]:
                    # first check if we had value already...

                    if each_required_field in uml_step[each_uml_definition].values():
                        # We got this field covered, let's see next one...
                        continue

                    # First, obtain way how to extract desired field
                    # This definition should be under "CORDA_OBJECT_DEFINITIONS/OBJECTS"
                    if ':' in each_required_field:
                        uml_field, field_role = each_required_field.split(":")
                    else:
                        uml_field, field_role = each_required_field
                    # Get actual Corda Object Definition branch for this particular object
                    codefinition = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS",
                                                      param="OBJECTS",
                                                      sub_param=field_role)

                    ignore_this_clause = False
                    if codefinition and "IGNORE" in codefinition:
                        # Check if we need to ignore this message...

                        for each_ignore_line in codefinition["IGNORE"]:
                            ignore_this = re.search(each_ignore_line, original_line)
                            if ignore_this:
                                # We don't need to search destination on this section as it could potentially clash
                                # with source
                                ignore_this_clause = True
                                break

                    if ignore_this_clause:
                        continue

                    expect_list = CordaObject.get_corda_object_definition_for(field_role, expect=True)

                    if expect_list is None:
                        # This mean there's no definition how to get this field out from source log line, which is an
                        # error
                        write_log("ERROR: I can't find proper definition of 'EXPECT' for %s please check this"
                              " as this will impact my ability to get proper UML definitions for current log" %
                              each_required_field)
                        continue
                    # Now go over each expect definition, and try to get field info...
                    #
                    for each_expect in expect_list:
                        # Make sure all regex substitution are done
                        fill_regex = RegexLib.build_regex(each_expect)
                        # now with proper regex, check message to see if we can gather field data
                        field_match = re.search(fill_regex, original_line)

                        # Check if we have a match
                        if field_match and field_match.groupdict():
                            if uml_field in field_match.groupdict():
                                grp_value = field_match.group(uml_field)
                                if grp_value in uml_rtn:
                                    # Do no overwrite previous values...
                                    continue
                                uml_rtn[grp_value] = each_required_field
                                uml_step[each_uml_definition] = uml_rtn
                                break
                            else:
                                for each_field_found in field_match.groupdict():
                                    if each_field_found in each_required_field:
                                        grp_value = field_match.group(each_field_found)
                                        uml_rtn[grp_value] = each_required_field
                                        uml_step[each_uml_definition] = uml_rtn
                                        break

        return uml_step

    @staticmethod
    def get_corda_object_definition_for(cobject, expect=False):
        """
        Will check against "CORDA_OBJECT_DEFINITIONS" section at configuration file to define what kind of object
        for UML should be related to
        :param cobject: name of the object to check out
        :return: actual UML Object name
        """

        # Basic Corda object definition
        corda_uml_definition = Configs.get_config_for("CORDA_OBJECT_DEFINITIONS.OBJECTS")
        # Check if given cobject has more detailed way to identify it. This need to be done because in the case of
        # Transaction the simple __tx_id__ definition is too ambiguous and can be confused with something else that is
        # not a proper transaction...

        # Detailed corda object description -- This definition *MUST-BE* Atomic only one macro-variable must appear,
        # on each line.
        corda_object_description = Configs.get_config(section="CORDA_OBJECTS")
        variable_to_search = "__%s__" % (cobject,)
        for each_corda_object in corda_object_description:
            for each_expect in corda_object_description[each_corda_object]['EXPECT']:
                if variable_to_search in each_expect:
                    return corda_object_description[each_corda_object]['EXPECT']

        # In the case no detailed description exist for this object, continue with the basic definition...

        if expect and cobject in corda_uml_definition.keys():
            if 'EXPECT' in corda_uml_definition[cobject]:
                return corda_uml_definition[cobject]['EXPECT']
            else:
                return None

        for each_definition in corda_uml_definition:
            if "APPLY_TO" in corda_uml_definition[each_definition] \
                    and cobject in corda_uml_definition[each_definition]["APPLY_TO"] and not expect:
                return each_definition

        return None

    @staticmethod
    def check_default_uml_references(line):
        """
        Check for default references to collect; when no source or destination are found on log message this will
        help to tell to program what can be used to infer source or destination references when they are missing
        for example, when a message is being sent back from a remote source will be the node that owns the actual log
        that will be the destination...
        Warning: This process only works when program is able to find automatically log_owner or notary; otherwise
        these entities when are setup manually will not have proper default endpoints defined!
        :param line: line to check
        :return:
        """

        uml_defaults = Configs.get_config(section="UML_ENTITY", param="OBJECTS")

        if not uml_defaults:
            return

        for each_default in uml_defaults:
            # if EXPECT option is found, this mean value should be extracted from the log itself
            # This EXPECTS will try to identify automatically an entity based on the regex contains on that expect, for
            # example identify automatically the log_owner, or a notary... and then add actual regex that will
            # recognise them as default endpoints. THIS WILL NOT WORK WHEN these are set manually (by the user)
            if "EXPECT" in uml_defaults[each_default]:
                usage_expect_counter = 0
                for each_usage_expect in uml_defaults[each_default]["EXPECT"]:
                    nregex = RegexLib.build_regex(each_usage_expect)
                    match = re.search(nregex, line)
                    if match and each_default not in CordaObject.default_uml_endpoints:
                        if each_default in match.groupdict():
                            # CordaObject.default_uml_endpoints[each_default] = match.group(each_default)
                            if match.group(each_default) not in CordaObject.default_uml_endpoints:
                                CordaObject.default_uml_endpoints[match.group(each_default)] = {}
                            for each_usage in uml_defaults[each_default]['USAGES']:
                                CordaObject.default_uml_endpoints[match.group(each_default)][each_usage] = \
                                    uml_defaults[each_default]['USAGES'][each_usage]

                            check_role = Configs.get_config(section="UML_ENTITY",
                                                            param="OBJECTS",
                                                            sub_param=each_default)
                            activate_role = False
                            if "ACTIVATE_ROLE" in check_role:
                                if check_role["ACTIVATE_ROLE"]:
                                    activate_role = check_role["ACTIVATE_ROLE"]
                            # if each_default == "log_owner":
                            if activate_role:
                                CordaObject.default_uml_endpoints[
                                    match.group(each_default)
                                ]["ROLE"] = each_default

                        else:
                            # I need to check if there's a default definition name that is not "standard" if so,
                            # then need to check "RETURN_OBJECT" then return that one instead of the name of
                            # this section; this will help to correct issue at the UML end definition, an example of
                            # this is the "log_owner" object that has no UML definition, this object in fact will be
                            # returned as "uml_object" to make it compatible with UML definition, but program will know
                            # that in this specific example, this uml_object is the Owner of current log, this is done
                            # to setup the default source/destination for some messages that are lacking of it
                            # a good example is saving into the Vault... the destination is the vault, but the source
                            # in this case will be the "log_owner"...
                            #
                            return_object = None
                            entity_list = dict(Configs.get_config(section="UML_ENTITY",
                                                                  param="OBJECTS",
                                                                  sub_param=each_default)['USAGES'])
                            # for each_endpoint in uml_defaults[each_default]["USAGES"]:
                            # write_log("Fuera del loop...")
                            for each_endpoint in entity_list:
                                if "RETURN_OBJECT" in uml_defaults[each_default]["USAGES"][each_endpoint]:
                                    return_object = uml_defaults[each_default]["USAGES"][each_endpoint]["RETURN_OBJECT"]
                                    for each_return_object in return_object:
                                        if each_return_object in match.groupdict():

                                            # for each_usage in uml_defaults[each_default]['USAGES']:
                                            for each_usage in entity_list:
                                                # write_log("Segundo loop test dict:", entity_list.keys())
                                                # write_log("Segundo loop org dict:",
                                                # uml_defaults[each_default]['USAGES'].keys())
                                                if match.group(each_return_object) not in \
                                                        CordaObject.default_uml_endpoints:
                                                    CordaObject.default_uml_endpoints[
                                                        match.group(each_return_object)
                                                    ] = {}
                                                CordaObject.default_uml_endpoints[
                                                    match.group(each_return_object)
                                                ][each_usage] = uml_defaults[each_default]['USAGES'][each_usage]
                                                check_role = Configs.get_config(section="UML_ENTITY",
                                                                                param="OBJECTS",
                                                                                sub_param=each_default)
                                                activate_role = False
                                                if "ACTIVATE_ROLE" in check_role:
                                                    if check_role["ACTIVATE_ROLE"]:
                                                        activate_role = check_role["ACTIVATE_ROLE"]
                                                # if each_default == "log_owner":
                                                if activate_role:
                                                    CordaObject.default_uml_endpoints[
                                                        match.group(each_return_object)
                                                    ]["ROLE"] = each_default
                                                    if not CordaObject.get_log_owner():
                                                        CordaObject.set_participant_role(
                                                            match.group(each_return_object),
                                                            role=each_default)

                                                # Finish the loop if I got the right definition do not
                                            # need more interactions
                                            break

                            if not return_object:
                                CordaObject.default_uml_endpoints[each_default] = each_default

                    # else:
                    #     # TODO: El problema que hay aqui es que la referencia a default esta iendo a "log_owner" o
                    #     #  por ejemplo "notary" debo hallar una manera de cambiar los roles a sus respectivos contra
                    #     #  partes es decir en el caso del log_owner deberia aparecer el x500 name en su lugar.
                    #     #  en la base de datos aparentemente aparece la informacion de el rol tal vez pueda usar eso
                    #
                    #     if "USAGES" in uml_defaults[each_default]:
                    #         for each_usage in uml_defaults[each_default]["USAGES"]:
                    #             usage_expect_counter = 0
                    #             for each_usage_expect in uml_defaults[each_default]["USAGES"][each_usage]["EXPECT"]:
                    #                 match_usage = re.search(each_usage_expect, line)
                    #                 if match_usage:
                    #                     if len(match_usage.groups()) == 0:
                    #                         if each_default not in CordaObject.default_uml_endpoints:
                    #                             CordaObject.default_uml_endpoints[each_default] = {}
                    #                         CordaObject.default_uml_endpoints[each_default][each_usage] = \
                    #                             uml_defaults[each_default]["USAGES"][each_usage]
                    #                     else:
                    #                         if each_default not in CordaObject.default_uml_endpoints:
                    #                             CordaObject.default_uml_endpoints[each_default] = {}
                    #
                    #                         default_object = uml_defaults[each_default]["USAGES"]\
                    #                             [each_usage]["RETURN_OBJECT"][usage_expect_counter]
                    #                         CordaObject.default_uml_endpoints[each_default] = default_object
                    #
                    #                 usage_expect_counter += 1
            else:
                if "USAGES" in uml_defaults[each_default]:
                    for each_usage in uml_defaults[each_default]["USAGES"]:
                        usage_expect_counter = 0
                        for each_usage_expect in uml_defaults[each_default]["USAGES"][each_usage]["EXPECT"]:
                            match_usage = re.search(each_usage_expect, line)
                            if match_usage:
                                if len(match_usage.groups()) == 0:
                                    if each_default not in CordaObject.default_uml_endpoints:
                                        CordaObject.default_uml_endpoints[each_default] = {}
                                    CordaObject.default_uml_endpoints[each_default][each_usage] = \
                                        uml_defaults[each_default]["USAGES"][each_usage]
                                else:
                                    if each_default not in CordaObject.default_uml_endpoints:
                                        CordaObject.default_uml_endpoints[each_default] = {}

                                    default_object = uml_defaults[each_default]["USAGES"] \
                                        [each_usage]["RETURN_OBJECT"][usage_expect_counter]
                                    CordaObject.default_uml_endpoints[each_default] = default_object

                            usage_expect_counter += 1

    @staticmethod
    def get_type_for(id_ref):
        """
        Search which type belongs to given reference
        :return: A string representing type of reference object, if is not found will return None
        """

        for each_type in CordaObject.list:
            if id_ref in CordaObject.list[each_type]:
                return each_type

        return None

    def add_reference(self, line, creference, line_no=None):
        """
        Add a new reference line to this object, this will be used to make the tracing of this object
        this action will also:
         - analyse and try to create a UML statements
         - analyse and extract actual status for the message
        :param line: line where this reference was found
        :param creference: a Dictionary that contains data to be referenced
        :return: None
        """

        # if the object has already "field_stage" means that it was already analised, and is coming from database...
        if "field_name" not in creference:
            object_type = CordaObject.get_type_for(self.data["id_ref"])
            if not object_type:
                write_log("Object without any type defined: %s" % self.data["id_ref"])
                write_log("Found in this line %s: %s" % (line, creference))
                return

            # Analyse UML -- Create UML step
            uml = self.analyse(creference["message"], line_no=line_no)

            if uml:
                if "uml" not in creference:
                    creference["uml"] = []
                # Add only one uml reference, do not make duplicates.
                if uml not in creference["uml"]:
                    creference["uml"].append(uml)

            # Extract stage
            # Get description setup for this reference:
            corda_object_reference = Configs.get_config(self.type, "ANALYSIS", section="CORDA_OBJECTS")
            if corda_object_reference and "EXPECT" in corda_object_reference:
                for each_regex_analysis in corda_object_reference["EXPECT"]:
                    # Apply regex to message line to extract a meaningful message
                    # analysis_group = re.search(each_regex_analysis, creference["message"])
                    reach_regex_analysis = RegexLib.use(each_regex_analysis)
                    analysis_group = reach_regex_analysis.search(creference["message"])

                    if analysis_group:
                        if len(analysis_group.groups()) > len(corda_object_reference["EXPECT"][each_regex_analysis]):
                            write_log("Unable to extract status properly; analysis has more group than defined fields")
                            write_log("Analysis group regex: '%s'" % each_regex_analysis)
                            write_log("expected groups: %s vs %s group found" %
                                  (len(corda_object_reference["EXPECT"][each_regex_analysis]),
                                   analysis_group.groups()))
                            continue
                        group_count = 1
                        for each_group in analysis_group.groups():
                            field = corda_object_reference["EXPECT"][each_regex_analysis][group_count-1]
                            creference[field] = each_group
                            if "field_name" not in creference:
                                # Add field name reference for later use (Print table with this field)
                                creference["field_name"] = []

                            creference["field_name"].append(field)
                            # Store this field to be able to create final summary table
                            if field not in CordaObject.additional_table_fields:
                                CordaObject.additional_table_fields.append(field)

        self.references[line] = creference
        # CordaObject.list[object_type][id_ref].references[line] = creference

    @staticmethod
    def get_object(ref_id):
        """
        Will return a corda object identified by ref_id
        :param ref_found:
        :return:
        """

        otype = CordaObject.get_type_for(ref_id)

        if not otype:
            return None

        return CordaObject.list[otype][ref_id]

    @staticmethod
    def add_uml_object(incoming_uml_object, uml_role):
        """
        Add new objects
        Also, it will try to identify if given object has a role

        :param incoming_uml_object: Normally party name
        :param uml_role: role assigned to this party (participant, control node, etc)

        :return:
        """
        # Add participants with proper UML role
        # standard_party = check_party(uml_object)

        # Verify if this UML object definition has a rule to accomplish
        # rules = Configs.get_config(uml_role, "RULES-D", "UML_DEFINITIONS")
        rules = Configs.get_config_for(f'CORDA_OBJECT_DEFINITIONS.OBJECTS.{uml_role}.RULES')
        if rules:
            uml_list = CordaObject.uml_apply_rules(incoming_uml_object, rules)
        else:
            uml_list = [incoming_uml_object]

        for umlobject in uml_list:
            uml_object = '%s "%s"' % (uml_role, umlobject)
            party = Party()
            party.name = umlobject
            party.role = uml_role
            # if I'm not able to add this new party name, means it is already in.
            if not party.add():
                continue

            CordaObject.uml_init.append(uml_object)

            CordaObject.uml_participants[uml_object] = ""
            # Check object Role...

    @staticmethod
    def uml_apply_rules(original_line, rules):
        """

        :param original_line:
        :param rules:
        :return:
        """
        global x500_build_list

        list_to_return = []
        parser = X500NameParser(rules)
        parsed_names = parser.parse_line(original_line, x500_build_list)

        for each_name in parsed_names:
            list_to_return.append(each_name.string())

        return list_to_return

    @staticmethod
    def get_corda_object_definition(macro_variable):
        """
        This method will return a list of ways to identify a macro_variable
        :param macro_variable: macro variable required
        :return: it will return a list of "EXPECT" which will teach how to identify given macro_variable in line context
        if not macro_variable is found at the expect list, will return None.
        """

        base_check = Configs.get_config(section="CORDA_OBJECTS")
        variable_to_search = "__%s__" % (macro_variable,)
        for each_corda_object in base_check:
            for each_expect in base_check[each_corda_object]['EXPECT']:
                if variable_to_search in base_check[each_corda_object][each_expect]:
                    return base_check[each_corda_object]['EXPECT']

        return None

    @staticmethod
    def get_all_objects(export=True):
        """
        Returns all objects stored
        :return: a dictionary
        """
        data = {}
        if not export:
            return CordaObject.list

        for each_type in CordaObject.list:
            for each_item in CordaObject.list[each_type]:
                if each_type not in data:
                    data[each_type] = {}

                data[each_type][each_item] = CordaObject.list[each_type][each_item].data

        return data

    class Type(Enum):
        """
        Allowed Types to set
        """

        FLOW_AND_TRANSACTIONS = "Flows&Transactions"
        UML_STEPS = "UML-Steps"
        PARTY = "Party"
        ERROR_ANALYSIS = 'Error-Log'

class FileManagement:
    """
    A class to help to read big files...
    """

    unique_results = {}

    def __init__(self, filename, block_size_in_mb=1, debug=False,scan_lines=7000,min_percent_merge=15):
        """
        Class created to manage all file operations. This class will help to process large files spliting them into
        blocks and starting up a thread per block.
        :param filename: Path to file
        :param block_size_in_mb: max blocksize of file, if it is bigger than 1 blocksize, it will be split using
        this value
        :param debug: will show debug message during procesing
        :param scan_lines: number of lines program will scan initially to detect log layout
        :param min_percent_merge: this will specify which percentage will be used to merge a block (in case block is too
        small to be left as a single block, this correct issues like launching a single thread to check a single line)
        """
        self.filename = filename
        self.block_size = block_size_in_mb * 1024 * 1024
        self.logfile_format = None
        self.scan_lines = scan_lines
        self.parallel_process = {}
        self.rules = None
        self.parser = None
        self.lock = threading.Lock()
        self.chunk_info = []
        self.file_size = None
        self.statistics = {}
        self.identified_roles = {}
        self.debug = debug
        self.min_percent_merge = min_percent_merge  # Porcentaje mínimo para no fusionar el bloque final
        self.special_blocks: BlockExtractor # Collect all blocks that are not collectable by multithread process
        self.log_line_regex = None
        self.state = None

        if not os.path.exists(self.filename):
            write_log("Unable to open given filename, it doesn't exist", level="ERROR")
            # self.state = "File not found"
            self.state = False
        else:
            self.state =True

        if not self.rules:
            self.rules = Configs.get_config_for('CORDA_OBJECT_DEFINITIONS.OBJECTS.participant')
        if not self.parser:
            self.parser = X500NameParser(self.rules['RULES'])

        FileManagement.clear()

    @classmethod
    def clear(cls):
        """
        Clear all results
        :return:
        """
        cls.unique_results = {}

    @staticmethod
    def get_element(element_type, element_reference_id):
        """
        Return party object from FileManager.unique_results
        :param element_type: identify which type element you want to get
        :param element_reference_id: specify actual element you want to get
        :return: element required, None otherwise
        """

        if isinstance(element_type, CordaObject.Type):
            selement_type = element_type.value
            element_type = selement_type

        if element_type in FileManagement.unique_results:
            if element_reference_id in FileManagement.unique_results[element_type]:
                return FileManagement.unique_results[element_type][element_reference_id]

        return None

    @staticmethod
    def get_all_unique_results(element_type=None, get_values=True):
        """
        Return a list of all unique results
        :param get_values: if it is true, will return a list with values, if it is false, will return a dictionary
        with key and value
        :param element_type: Specify which kind of data you want to retrieve
        :return: return a list of element values from given type
        """

        if isinstance(element_type, CordaObject.Type):
            selement_type = element_type.value
            element_type = selement_type

        if not element_type:
            return FileManagement.unique_results

        if element_type in FileManagement.unique_results:
            if get_values:
                return FileManagement.unique_results[element_type].values()
            else:
                return FileManagement.unique_results[element_type]
        else:
            write_log(f'Error: Unable to retrieve elements for type {element_type}')
            return None

    @staticmethod
    def result_has_element(element_type):
        """
        Method to check if given element exist on results
        :param element_type:  Element type, which is one supported at the moment Flows&Transactions or Party
        :return: True if elemets exists, false otherwise
        """
        if isinstance(element_type, CordaObject.Type):
            selement_type = element_type.value
            element_type = selement_type

        return element_type in FileManagement.unique_results

    @staticmethod
    def delete_element(element_type, element_id):
        """
        Delete an element from mail element list
        :param element_type: element type you want to delete
        :param element_id: element ID to delete
        :return:
        """
        if isinstance(element_type, CordaObject.Type):
            selement_type = element_type.value
            element_type = selement_type

        elements = FileManagement.get_all_unique_results(element_type, False)

        del elements[element_id.reference_id]

        FileManagement.unique_results[element_type] =  elements

    @staticmethod
    def add_element(element_type, item):
        """
        This method will add given element into unique repository for all elements collected
        this repository will hold all types of elements, "Party" elements and Flow & Transactions Elements
        for this to work all element types should share same property 'item.reference_id' because this
        will setup proper name/id to search for it.
        :param element_type: element, which will be defined as "Party" or "Flow&Transactions"  object
        :param item: Item to store
        :return: None
        """

        if isinstance(element_type, CordaObject.Type):
            selement_type = element_type.value
            element_type = selement_type


        if element_type not in FileManagement.unique_results:
            FileManagement.unique_results[element_type] = {}

        if element_type == CordaObject.Type.UML_STEPS.value and  item.reference_id in FileManagement.unique_results[element_type]:
            # This mean another item.reference_id is already there with same reference in this case line number, this
            # could be because same line contains a transaction and a flow for example...
            # let's check container is a list to be able to add it, otherwise I need to convert container into a list, add previous
            # value, and allow new value to be added..., other wise, if it is already a list, add new value
            #
            if not isinstance(FileManagement.unique_results[element_type][item.reference_id], list):
                previous_value =  FileManagement.unique_results[element_type][item.reference_id]
                FileManagement.unique_results[element_type][item.reference_id] = []
                FileManagement.unique_results[element_type][item.reference_id].append(previous_value)

            FileManagement.unique_results[element_type][item.reference_id].append(item)
        else:
            FileManagement.unique_results[element_type].setdefault(item.reference_id, item)

    @staticmethod
    def print_parties():

        for index,each_id in enumerate(FileManagement.get_all_unique_results('Party')):
            if each_id.get_corda_role():
                role = f'{each_id.get_corda_role()}'
            else:
                role = 'party'
            write_log(f"[{index+1:>3}] [{role:^11}] {each_id.name}")
            if each_id.has_alternate_names():
                for each_alternate_name in each_id.get_alternate_names():
                    write_log(f"              `-->  {each_alternate_name}")

    def identify_party_role(self, line, line_no=None):
        """
        This method will try to identify a specific party like a Notary or log producer (low_owner)
        :return:
        """

        get_role_definitions = Configs.get_config_for("UML_ENTITY.OBJECTS")
        for each_role in get_role_definitions:
            expect = Configs.get_config_for(f"UML_ENTITY.OBJECTS.{each_role}.EXPECT")
            if not expect:
                continue

            # list of patterns from configuration *may* have macrovariables used to replace parties and
            # other stuff like "__notary__" or "__participant__" this need to be "expanded" into real one, to be
            # able to get correct regex patter to look for

            # Expand regex:
            # for each_expect in expect:
            # real_regex = RegexLib.build_regex(each_expect)

            check_pattern = RegexLib.regex_to_use(expect, line, line_no=line_no)

            if  check_pattern is None:
                # No role found for this entity
                continue
            real_regex = RegexLib.build_regex(expect[check_pattern])
            validate = re.search(real_regex, line)

            # TODO: actual regext to pull x500 still buggy and it doesn't collect x500 names correctly
            #
            if validate:
                x = X500NameParser(rules=self.rules['RULES'])
                x500 = x.parse_line(validate.group(1), [])
                self.add_party_role(x500[0].string(), each_role)

    def add_party_role(self, party, role):
        """
        this method will collect all roles found on file, when running x500name identification
        this will help to save time for this step verifying same line
        :param party: party you want to add
        :param role: role assigned to this party
        :return:
        """

        if role not in self.identified_roles:
            self.identified_roles[role] = set()

        self.identified_roles[role].add(party)

    def get_party_role(self, role=None):
        """
        Return roles found
        :param role: role name
        :return: list party found under that role, if not role defined, it will return actual roles found
        """

        if role and role in self.identified_roles:
            return list(self.identified_roles[role])

        return list(self.identified_roles.keys())

    def assign_roles(self):
        """
        Will gather roles found at given file,  and will assign corresponding role to each one of them
        Actual roles to assign are defined in json file (ie notary, log_owner, etc)
        :return: None
        """

        # Get roles found
        for each_role in self.get_party_role():
            for each_party in self.get_party_role(each_role):
                party = FileManagement.get_element('Party', each_party)
                if party:
                    party.set_corda_role(each_role)

    def start_stop_watch(self, process_name, start=False):
        """
        A method to measure time between processes
        :param start: True Will start Chrono, False will stop it
        :param process_name: process you want to chrono, this is to keep an inventory of all processes
        in an ordered way
        :return: Time spent -- only when start is False
        """
        if process_name not in self.statistics:
            self.statistics[process_name] = {}

        if start:
            self.statistics[process_name]['chrono-start'] = time.time()
        else:
            self.statistics[process_name]['chrono-stop'] = time.time()
            elapsed_time =   self.statistics[process_name]['chrono-stop'] - self.statistics[process_name]['chrono-start']

            if elapsed_time > 60:
                time_msg = f'{elapsed_time / 60:.2f} minute(s).'
            else:
                time_msg = f'{elapsed_time:.4f} seconds.'

            self.statistics[process_name]['chrono-elapsed-time'] = elapsed_time
            self.statistics[process_name]['chrono-elapsed-time-message'] = time_msg

            return time_msg

    def get_statistics_data(self, process_name, data_name):
        """
        Return saved statistic data from process given
        :param process_name: process name for statistic data
        :param data_name: data name
        :return: statistic data value
        """

        if process_name in self.statistics and data_name in self.statistics[process_name]:
            return self.statistics[process_name][data_name]

        return None

    def pre_analysis(self):
        try:
            file_size = os.path.getsize(self.filename)
            fsize = file_size / 1024 / 1024
            bsize = self.block_size / 1024 / 1024
            write_log(f'Block size for reading: {bsize:.2f} Mbytes')
            write_log(f'Pre-analysing file size {fsize:.2f} Mbytes calculating block sizes')

            if self.block_size > file_size:
                write_log(f'Adjusting blocksize to {fsize:.2f}Mb because blocksize given({bsize:.2f}Mb) is too big')
                self.block_size = file_size

            line_counter = 1
            self.chunk_info = []
            with open(self.filename, 'r') as file:
                while file.tell() < file_size:
                    start_pos = file.tell()
                    start_line = line_counter

                    remaining = file_size - start_pos

                    # Si estamos cerca del final y el resto es menor al porcentaje mínimo, fusionamos
                    if remaining < (self.block_size * self.min_percent_merge / 100):
                        chunk = file.read(remaining)
                        last_newline = chunk.rfind('\n')
                        if last_newline != -1:
                            end_pos = start_pos + last_newline + 1
                            lines_in_chunk = chunk[:last_newline + 1].count('\n')
                        else:
                            end_pos = file_size
                            lines_in_chunk = chunk.count('\n') + (1 if chunk else 0)

                        if self.chunk_info:
                            prev_start, prev_size, prev_start_line, prev_end_line = self.chunk_info[-1]
                            self.chunk_info[-1] = (
                                prev_start,
                                end_pos - prev_start,
                                prev_start_line,
                                prev_end_line + lines_in_chunk
                            )
                        else:
                            end_line = start_line + lines_in_chunk - 1
                            self.chunk_info.append((start_pos, end_pos - start_pos, start_line, end_line))
                        break  # Salimos del bucle, ya procesamos todo

                    else:
                        # Leer bloque normal
                        chunk = file.read(self.block_size)
                        last_newline = chunk.rfind('\n')
                        if last_newline != -1:
                            end_pos = start_pos + last_newline + 1
                        else:
                            end_pos = start_pos + len(chunk)

                        lines_in_chunk = chunk[:last_newline + 1].count('\n') if last_newline != -1 else 0
                        end_line = start_line + lines_in_chunk - 1

                        self.chunk_info.append((start_pos, end_pos - start_pos, start_line, end_line))
                        line_counter += lines_in_chunk
                        file.seek(end_pos)

                        write_log(f"Processed block: start_pos={start_pos}, lines={start_line}-{end_line}")
            write_log(f'Will launch {len(self.chunk_info)} threads to read full file...')
            self.state = True

        except IOError as io:
            write_log(f'Unable to read file due to {io}', level='ERROR')
        except UnicodeDecodeError as ude:
            write_log(f'Unable to read file due to {ude}', level='ERROR')
        except UnicodeError as ue:
            write_log(f'Unable to read file due to {ue}', level='ERROR')


    def add_process_to_execute(self, method):
        """
        This will add a method to be executed.
        :param method: Class/object which represents and have an internal method called
        "execute" which will instruct what need to be performed
        :return:
        """
        if not method.type:
            method_type = 'Unknown'
        else:
            method_type = method.type

        self.parallel_process[method_type] = method
        write_log(f"Searching for {method_type}...")

    def remove_process_to_execute(self, method_type):
        """
        Remove process/task to execute
        :type method_type: method type to be removed
        :return:
        """
        if isinstance(method_type, CordaObject.Type):
            smethod_type = method_type.value
            method_type = smethod_type

        if method_type in self.parallel_process:
            del self.parallel_process[method_type]
            write_log(f"{method_type} search complete.")

    def clean_all_processes_to_execute(self):
        self.parallel_process = {}

    def get_methods_type(self):
        """
        Return all methods defined for execution
        :return: list
        """
        return list(self.parallel_process.keys())

    def get_method(self, method_type):
        """

        :param method_type: method you want to get
        :return:
        """
        if isinstance(method_type, CordaObject.Type):
            smethod_type = method_type.value
            method_type = smethod_type

        if method_type in self.parallel_process:
            return self.parallel_process[method_type]
        else:
            return None

    def process_block(self, args):
        """
        Method in charge to do actual processing of data, searching for required information and
        storing it
        :param args:
        :return:
        """

        # TODO: Este metodo guarda los resultados; necesito hacer una revision de esto, ya que el hecho de ejecutar
        #  el metodo que procesa la informacion en el caso de los ref_ids ya esta guardando los resultados, asi que
        #  probablemente este repitiendo el proceso sin necesidad aqui.

        start, size, start_line, end_line = args
        local_results = {}
        current_line = start_line
        try:
            # Verificar si ya se solicitó cierre antes de empezar
            if shutdown_event.is_set():
                return None
            with open(self.filename, "r") as file:
                with mmap.mmap(file.fileno(), length=0, access=mmap.ACCESS_READ) as mmapped_file:
                    chunk = mmapped_file[start:start+size].decode('utf-8', errors='ignore')
                    lines = chunk.splitlines()

                    for i, line in enumerate(lines):
                        for each_method in self.get_methods_type():
                            # Verificar cada 100 líneas si es hora de terminar
                            if i % 100 == 0 and shutdown_event.is_set():
                                write_log(f"Interrupting block processing {start_line}-{end_line} due to close request")
                                return None

                            result = self.get_method(each_method).execute(line, current_line)
                            #write_log(f"{each_method} -- {result}")
                            if each_method == 'Party':
                                # if method running is related to parties, line below will run an extra
                                # analysis on that line to see if this line is able to identify a role (like owner of log
                                # or notary...
                                self.identify_party_role(line,start_line+i)

                            if result:
                                if each_method not in local_results:
                                    local_results[each_method] = []
                                if isinstance(result, list):
                                    local_results[each_method].extend(result)
                                else:
                                    local_results[each_method].append(result)
                        current_line += 1

            if local_results:
                with self.lock:
                    for each_method in self.get_methods_type():
                        write_log(f"Saving {each_method}...")
                        if each_method in local_results:
                            for each_result in local_results[each_method]:
                                FileManagement.add_element(each_method, each_result)

            return FileManagement.get_all_unique_results()

        except Exception as e:
            if not shutdown_event.is_set():  # Solo registrar errores reales
                write_log(f"Error Processing block {start_line}-{end_line}: {str(e)}", level="ERROR")
            return None

    def parallel_processing(self):
        """
        Procesamiento paralelo CORREGIDO para mantener la UI responsive
        """
        tasks = [(start, size, start_line, end_line) for start, size, start_line, end_line in self.chunk_info]
        write_log(f"{Icons.INFO} Block processing initiated with {len(tasks)} blocks")
        if not self.logfile_format:
            write_log(f'{Icons.ERROR} Unable to process this file, I can\'t determine its format')
            write_log(f'{Icons.MAGNIFYING_GLASS} Add proper format at configuration file under \'IDENTITY_FORMAT\' section...')
            return
        # Variables para monitoreo
        futures = []
        active_tasks = tasks.copy()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            # Función para monitorear tareas SIN BLOQUEAR
            def monitor_tasks():
                nonlocal active_tasks

                if shutdown_event.is_set() or not active_tasks:
                    return

                # Actualizar lista de tareas activas
                completed_indices = [
                    future.thread_index for future in futures
                    if future.done() and not future.cancelled()
                ]
                active_tasks = [
                    task for task in active_tasks
                    if tasks.index(task) not in completed_indices
                ]

                # Registrar progreso cada 5% de completado
                completed_percent = 100 - (len(active_tasks) * 100 // len(tasks))
                if completed_percent % 2 == 0 and self.debug:
                    if completed_percent != 100:
                        schedule_ui_update('TTkLabel_analysis_stat','setText',f"{Icons.CLOCK}...{completed_percent}%")
                    else:
                        schedule_ui_update('TTkLabel_analysis_stat', "setText", '\u2705 Done...')


                # Programar próxima verificación
                if active_tasks and not shutdown_event.is_set():
                    threading.Timer(0.1, monitor_tasks).start()  # ¡Solo 100ms!

            # Iniciar monitoreo
            monitor_tasks()

            # Enviar tareas al pool
            for index, each_task in enumerate(tasks):
                if shutdown_event.is_set():
                    break

                self.start_stop_watch(f'Thread-{index}', start=True)
                future = pool.submit(self.process_block, each_task)
                future.thread_index = index
                future.start_time = self.get_statistics_data(f'Thread-{index}', 'chrono-start')
                future.info = each_task[1]
                futures.append(future)

        # Procesar resultados solo si no se está cerrando
        if not shutdown_event.is_set() and self.debug:
            total_time = 0
            total_data = 0

            for future in futures:
                if future.done() and not future.cancelled():
                    thread_index = future.thread_index
                    time_msg = self.start_stop_watch(f'Thread-{thread_index}', start=False)
                    data = future.info / (1024 * 1024)

                    total_time += float(time_msg.split()[0])
                    total_data += data

                    if self.debug:
                        write_log(f"Thread {thread_index} completed in {time_msg}, "
                                  f"Processed {data:.2f} MB")

            if self.debug:
                write_log(f"{Icons.SUCCESS} Analysis complete. "
                          f"Total: {total_data:.2f} MB en {total_time:.2f}s")



    def set_file_format(self, file_format):
        """
        Corda file format recognized
        :param file_format: file format found at json config file
        :return:
        """
        self.logfile_format = file_format

    def get_file_format(self):
        """
        Return actual file format
        :return: String, this file format is actual label being set in json file
        """

        if self.logfile_format:
            return self.logfile_format
        else:
            return "UNKNOWN"

    def discover_file_format(self):
        """
        Analyse first self.scan_lines ( 25 by default) lines from given file to determine which Corda log format is
        This is done to be able to separate key components from lines like Time stamp, severity level, and log
        message
        :return:
        """
        versions = Configs.get_config_for("VERSION.IDENTITY_FORMAT")
        write_log(f'Please wait, reading file {self.filename} and searching for its structure.')
        try:
            with open(self.filename, "r") as hfile:
                for line, each_line in enumerate(hfile):
                    if not self.logfile_format and line <= self.scan_lines:
                        for each_version in versions:
                            try_version = versions[each_version]
                            check_version = re.search(try_version["EXPECT"], each_line)
                            if check_version:
                                self.logfile_format = each_version
                                self.log_line_regex = re.compile(try_version["EXPECT"])
                                write_log("Log file format recognized as: %s" % self.logfile_format)
                                break
        except IOError as io:
            write_log(f'Unable to open {self.filename} due to {io}')
        except UnicodeDecodeError as ue:
            write_log(f'Unable to read this file due to: {ue}', level="ERROR")
            return

class Party:
    """
    A class to represent parties on a log
    """
    party_list = []
    party_expected_role_list = {
        'notary': 'optional',
        'log_owner': 'mandatory'
    }

    def __init__(self, x500name=None):
        self.name = x500name
        self.reference_id = self.name
        self.role = ''
        self.type = 'Party'
        self.corda_role = []
        self.default_endpoint = None
        self.alternate_names = []
        self.original_string = x500name
        self.regex = re.compile(r"([CNSTLOU]{1,2}=[^\[\]^,]*)")
        self.attributes = self.extract_attributes()

    @staticmethod
    def assign_roles_manually(party_list):
        """
        Assign roles manually; this should be used only when there're expected roles to assign
        :return:
        """

        pending = Party.get_pending_roles()

        if pending:

            pass

    @staticmethod
    def normalize_x500(attributes):
        """
        Set a standard order for all x500 names
        :param attributes: list with all attributes that need to be normalized
        :return: a normalized list of attributes
        """

        #
        # TODO: Este metodo esta introduciendo un molesto bug, esta eliminando potenciales parties de la
        #  lista al tratar de normalizar los nombres; en una lista de atributos que contenga mas de un
        #  x500 name eliminara uno de ellos y se perdera de la lista.
        #  debo buscar una manera de preservar todos los nombres que se consiga, y organizarlos. Probablemente la
        #  normalizacion no sea bueno usarla al construir los atributos, sera mejor usarla antes de agregar el
        #  nuevo nombre a la lista

        attribute_order = Configs.get_config_for("CORDA_OBJECT_DEFINITIONS.OBJECTS.participant.RULES.X500-attributes-order.CONTENT")
        x5002normalize = {}
        normalized_attributes = []

        for each_att in attributes:
            key,value = each_att
            x5002normalize[key] = value

        for each_att in attribute_order:
            if each_att in x5002normalize:
                normalized_attributes.append((each_att,x5002normalize[each_att]))

        return normalized_attributes



    @staticmethod
    def define_custom_party(rules_set, assigned_role):
        """
        Create a new party that wasn't recognized automatically
        :type rules_set: set rules used to validate a x500 name
        :return: Party object with given name
        """
        write_log('Creating new party:')
        att_list = []
        for each_attribute in rules_set['RULES']['supported-attributes']:
            att = input(f'   * {each_attribute}=')
            if att:
                att_list.append(f"{each_attribute}={att}")

        new_party = ', '.join(att_list)

        party = Party(new_party)

        party.set_corda_role(assigned_role)

        write_log(f'New party to add: [{new_party}] with role [{assigned_role}]')
        return party



    @staticmethod
    def get_pending_roles():
        """
        Will return any missing expected role. these roles are required to do a proper tracing.
        log_owner role is mandatory, notary role is optional
        """
        if Party.party_expected_role_list:
            return Party.party_expected_role_list

        return None


    def set_name(self, name):
        """
        Set party name
        :param name: x500 party name
        :return: void
        """
        self.name = name
        self.reference_id = name

    def set_role(self, role):
        """
        Set party role for UML setup
        :param role: role
        :return: void
        """

        self.role = role

    def set_corda_role(self, corda_role):
        """
        Set party corda role
        :param corda_role: set actual corda role like participant, Notary, etc, a node may have more than a role
        for example if log is being produced by a Notary, then role should be "notary/log_owner"
        :return: void
        """

        if corda_role in self.corda_role:
            return

        if corda_role in Party.party_expected_role_list:
            # remove given party expected role from pending list
            if corda_role in Party.party_expected_role_list:
                Party.party_expected_role_list.pop(corda_role, None)

        self.corda_role.append(corda_role)

    def get_alternate_names(self):
        """
        Return all names that match with current main Name
        :return: list x500 names
        """
        return self.alternate_names

    def get_corda_role(self):
        """
        Return actual corda role assigned to this party, if multiple roles are will be separated by "/"
        :return: String
        """

        return "/".join(self.corda_role)

    def get_corda_roles_as_list(self):
        """
        Return a list of roles
        :return: list of string representing each assigned role
        """

        return self.corda_role

    def add_endpoint(self, endpoints, endpoint_type="source"):
        """
        Add endpoints for default destination / source
        :param endpoint_type: Destination / source
        :return:
        """

        if not self.default_endpoint:
            self.default_endpoint = {}

        self.default_endpoint[endpoint_type] = endpoints

    def remove_endpoint(self, endpoint, endpoint_type):
        """
        Remove an endpoint from this object

        :param endpoint: end point to remove
        :param endpoint_type: endpoint type, destination or source
        :return:
        """

        if endpoint_type in self.default_endpoint:
            dict.pop(self.default_endpoint[endpoint_type][endpoint], None)

    def add(self):
        """
        Add a new party
        :return: False if Party was already added, True if it is first time
        """
        self.name = self.name.replace('"','')
        # If party name was already registered do not add it.

        # # Verify if this UML object definition has a rule to accomplish
        # rules = Configs.get_config(uml_role, "RULES", "UML_DEFINITIONS")
        # if rules:
        #     uml_list = CordaObject.uml_apply_rules(incoming_uml_object, rules)
        # else:
        #     uml_list = [incoming_uml_object]

        for pty in Party.party_list:
            if self.name == pty.name:
                return False

        Party.party_list.append(self)
        return True

    def extract_attributes(self, name=None):
        """
        Try to extract actual attributes for given name
        Extract attributes from a given line using a regex.
        """

        if not name:
            name = self.original_string

        matches = self.regex.findall(name)
        # attributes = [match.split('=') for match in matches]
        attributes = matches
        return attributes

    def is_same_name(self, name_to_compare):
        """
        Will try to compare given name to actual x500 name to see if it is the same,
        x500 names can have their attributes shifted, but they are still same regardless to their order.
        this method will tell if given name is same
        :param name_to_compare: other x500 name to compare
        :return: true if it is same, false otherwise
        """

        other_attributes = self.extract_attributes(name_to_compare)

        if set(other_attributes) == set(self.attributes):
            return True

        return False

    def add_alternate_name(self, other_x500_name):
        """
        This will add a new alias for given name
        :param other_x500_name:
        :return:
        """

        # first check if alias is already here
        if other_x500_name == self.original_string:
            return

        if other_x500_name in self.alternate_names:
            return


        self.alternate_names.append(other_x500_name)

    def get_attributes(self):
        """
        Return all attributes
        :return:
        """

        return self.attributes

    def string(self):
        """
        Returns actual x500 name in string format
        :return:
        """

        return ', '.join(f"{k}" for k in self.attributes).strip()

    def has_alternate_names(self):
        """
        Will return wether current name has alternate names
        :return: true if it has, false otherwise
        """

        if self.alternate_names:
            return True

        return False


    @staticmethod
    def get_party(party_name):
        """
        Return Party object that match x500 name
        :param party_name: x500 name of party to look for
        :return: a party object
        """
        for each_party in Party.party_list:
            if each_party.name == party_name:
                return each_party

        return None

class X500NameParser:
    def __init__(self, rules):
        """
        Initialize the parser with rules for attribute validation.
        :param rules: Dictionary containing validation rules.
        """
        # self.rules = rules['RULES-D']['supported-attributes']
        self.rules = rules['supported-attributes']
        self.mandatory_attributes = [k for k, v in self.rules.items() if v.get('mandatory', False)]
        self.regex = re.compile(r"([CNSTLOU]{1,2}=[^\[\]^,={]*)")

    def extract_attributes(self, line):
        """
        Extract attributes from a given line using a regex.
        :param line: String containing potential X500 names.
        :return: List of tuples representing key-value pairs.
        """
        matches = self.regex.findall(line)
        attributes = []
        for each_match in matches:
            key, value = each_match.split('=')
            valid_value = value
            if key not in self.rules:
                pass
                # write_log(f'Invalid x500 attribute, not supported... {key}={value} ')
                # write_log(f"There're no rules to check {key}")
                # write_log('Unable to verify this x500 attribute')
            else:
                valid = re.search(self.rules[key]['expect'], each_match)
                if valid:
                    _,valid_value = valid.group(1).split('=')
                else:
                    pass
                    # write_log(f'Invalid x500 attribute, not supported... {key}={valid_value} ')
                    # write_log('Unable to verify this x500 attribute')
                    # write_log(f'Key/value do is not on expected format {key}={self.rules[key]["expect"]}')

            attributes.append((key, valid_value))

        return attributes

    @staticmethod
    def normalize_x500(x500namestr):
        """
        Set a standard order for all x500 names
        :param attributes: list with all attributes that need to be normalized
        :return: a normalized list of attributes
        """

        #
        # TODO: Este metodo esta introduciendo un molesto bug, esta eliminando potenciales parties de la
        #  lista al tratar de normalizar los nombres; en una lista de atributos que contenga mas de un
        #  x500 name eliminara uno de ellos y se perdera de la lista.
        #  debo buscar una manera de preservar todos los nombres que se consiga, y organizarlos. Probablemente la
        #  normalizacion no sea bueno usarla al construir los atributos, sera mejor usarla antes de agregar el
        #  nuevo nombre a la lista

        # I'm Assuming all x500namestr are wellformed x500 names
        attributes = x500namestr.split(',')

        attribute_order = Configs.get_config_for("CORDA_OBJECT_DEFINITIONS.OBJECTS.participant.RULES.X500-attributes-order.CONTENT")
        x5002normalize = {}
        normalized_attributes = []

        for each_att in attributes:
            key,value = each_att.split('=')
            x5002normalize[key.strip()] = value

        for each_att in attribute_order:
            if each_att in x5002normalize:
                normalized_attributes.append(f'{each_att}={x5002normalize[each_att]}')

        return ', '.join(f"{k}" for k in normalized_attributes).strip()


    def validate_x500_name(self, attributes):
        """
        Validate if a set of attributes constitutes a valid X500 name.
        :param attributes: List of key-value pairs.
        :return: Boolean indicating validity.
        """
        keys = {key for key, _ in attributes}
        for mandatory in self.mandatory_attributes:
            if mandatory not in keys:
                return False
        return True

    def parse_line(self, line,x500_list):
        """
        Parse a line to extract and validate X500 names.
        :param line: String containing potential X500 names.
        :param x500_list: provide an empty list, that will persist on each call, this will help to build final
        :list for all x500 names found, this is required to prevent "static" variables.
        :return: List of valid X500 names.
        """
        attributes = self.extract_attributes(line)
        x500_names = []
        rx500_names = []
        current_name = []

        for key, value in attributes:
            if any(key == k for k, _ in current_name):
                # Duplicate key means we likely have a new X500 name
                rname = ', '.join(f"{k}={v}" for k, v in current_name)
                if self.validate_x500_name(current_name):
                    if rname not in rx500_names:
                        rx500_names.append(rname)
                    x500_names.append(current_name)
                current_name = []

            current_name.append((key, value))

        # Add the last X500 name if valid
        if self.validate_x500_name(current_name):
            rname = ', '.join(f"{k}={v}" for k, v in current_name)
            if rname not in rx500_names:
                rx500_names.append(rname)
            x500_names.append(current_name)


        # Process all names found and convert them into a proper x500 name object

        if rx500_names:

            for rname in rx500_names:
                alternate_name_found = False
                # if name not in x500_name_list:
                # Before creating a proper party, first normalize x500 name to make sure it is standard in whole
                # analysis
                #
                norm_rname = X500NameParser.normalize_x500(rname)
                x500name = Party(norm_rname)
                if x500_list:
                    for each_xname in x500_list:
                        if each_xname.is_same_name(rname):
                            each_xname.add_alternate_name(rname)
                            alternate_name_found = True

                if not alternate_name_found:
                    x500_list.append(x500name)

        # return rx500_names
        return x500_list

    def identify_party_role(self, line, line_no=None):
        """
        This method will try to identify a specific party like a Notary or log producer (low_owner)
        :return:
        """

        get_role_definitions = Configs.get_config_for("UML_ENTITY.OBJECTS")
        for each_role in get_role_definitions:
            # expect = Configs.get_config_for(f"UML_ENTITY.OBJECTS.{each_role}.EXPECT")
            expect = get_role_definitions[each_role]['EXPECT']
            if not expect:
                continue

            # list of patterns from configuration *may* have macrovariables used to replace parties and
            # other stuff like "__notary__" or "__participant__" this need to be "expanded" into real one, to be
            # able to get correct regex patter to look for

            # Expand regex:
            # for each_expect in expect:
            # real_regex = RegexLib.build_regex(each_expect)

            check_pattern = RegexLib.regex_to_use(expect, line, line_no=line_no)

            if  check_pattern is None:
                # No role found for this entity
                continue
            real_regex = RegexLib.build_regex(expect[check_pattern])
            validate = re.search(real_regex, line)

            if validate:
                x500 = self.parse_line(line, [])
                pass

class Configs:
    config = {}
    count = 0
    compiled_regex = {}
    config_access_cache = {}

    config_variables = {
        "VERSION": {
            "default": "2.00-RC27",
            "description": "Version of program"
        },
        "PIXEL_RATIO": {
            "default": 10,
            "description": "This will be used to make a multiplication at the column headers of each table"
                           " basically to adjust better new table web representation"
        },
        "APP_URL": {
            "default": "http://omega-x:8080/support",
            "description": "Web server URL to connect to"
        },
        "UPLOAD_PATH": {
            "default": "/home/r3support/www/uploads/customers",
            "description": "This represent actual physical directory where all logs will reside"
        },
        "RULES_FILE": {
            "default": "/home/r3support/www/cgi-bin/support/conf/logwatcher_rules.json",
            "description": "Specify path and filename used for match rules"
        },
        "HTML_START_TABLE": {
            "default": {
                "GLOBAL_SETTING": "<table border=1 cellpadding=10 cellspacing=0>",
                "File information": "<table width=\"90%\" border=1 cellpadding=2 cellspacing=0>",
                "Details for": "<table class=\"details\" width=\"90%\" border=1 cellpadding=10 cellspacing=0>",
                "Actual alerts": "<table class=\"screenboard\" border=1 cellpadding=10 cellspacing=0>",
                "Log Viewer": "<table class=\"logviewer\" width=\"85%\" border=1 cellpadding=10 cellspacing=0>",
                "Log Summary for": "<table class=\"logsummary\" id=\"logsummary\" width=\"85%\" border=1 cellpadding=10 cellspacing=0>"
            },
            "description": "This variable is used to apply modifications to tables, GLOBAL_SETTING affect all tables,"
                           " setting up table name, and settings will only apply to that table, "
                           "overriding GLOBAL_SETTINGS, this will force program to start table with specified settings"
        },
        "DASHBOARD": {
            "default": {
                "SHOW": [
                    "Production", "unknown", None
                ]
            },
            "description": "This variable will instruct program to show at the dashboard view errors with"
                           " that specified location"
        },
        "QUEUE_WORKERS": {
            "default": {
                "WORKER_COOPERATION_ALLOWED": True,
                "WORKER_COOPERATIVE_THREADS": 4,
                "WORKER_THRESHOLD_COOPERATION": 1000000,
                "WORKER_RESPONSE_TIMEOUT": 600,
                "WORKER_CHECK": 5,
                "WORKER_RGX_OPTIMIZATION_TEST": True,
                "WORKER_PROCESSING_ORDER": [
                    "SIMPLE(ASC)",
                    "COOPERATIVE(ASC)"
                ],
                "MAX_ADMIN_WORKERS": 4,
                "MAX_ANALYSIS_PROCESSES": 24,
                "MAX_WORKERS_PER_CUSTOMER": 4,
                "SHOW_WORKER_STATUS": False,
                "ANALYSIS_WORKER_CONSTRAINT": "customer"
            },
            "description": "Here you can modify behavior of workers for analysis, "
                           "WORKER_COOPERATION_ALLOWED: This will instruct program to use more workers to analyse. "
                           "WORKER_COOPERATIVE_THREADS: Maximum number of workers on the same analysis. "
                           "WORKER_THRESHOLD_COOPERATION: Number of lines that logfile must exceed to launch "
                           "cooperative workers. "
                           "WORKER_RESPONSE_TIMEOUT: Number of seconds Queue Manager program will wait to mark a worker"
                           "as 'STALLED' and kill it... or spanw a new one if is required. "
                           "WORKER_CHECK: This represents number of seconds that a worker will wait to report back. "
                           "WORKER_RGX_OPTIMIZATION_TEST: new analysis engine. "
                           "WORKER_PROCESSING_ORDER: [not implemented yet] will govern how analysis will be done,"
                           "starting with SIMPLE logfiles in ascendant mode(smaller first), then continue with"
                           "COOPERATIVE logs(bigger ones) also starting on ascendant mode. "
                           "MAX_ADMIN_WORKERS: number of ADMIN workers allowed, these workers will do admin task like"
                           " delete old logs. "
                           "MAX_ANALYSIS_PROCESSES: The maximum number of workers all the time, "
                           "including ADMIN workers. "
                           "MAX_WORKERS_PER_CUSTOMER: number of maximum workers that can work in a single "
                           "customer logs. "
                           "SHOW_WORKER_STATUS: This will show a small table a the top of page with worker statuses. "
                           "ANALYSIS_WORKER_CONSTRAINT: [not implemented] this will indicate what is the constraint "
                           "that will be used to limit number of workers on a specific customer"

        },
        "DATABASE": {
            "default": {
                "BATCH_COMMIT_EVERY": 1000,
                "BATCH_DELETE_ROWS": 10000,
                "LOGFILE_STORAGE_EXPIRE": 1,
                "STORE_FILES_ON_DB": True,
                "SEARCH_THRESHOLD": 500
            }
        },
        "ALERT_FILE": "/home/larry/workspace/metrix/alerts.json",
        "JIRA_ALERT_FILE": "/home/larry/IdeaProjects/metrix/jira_alerts.json",
        "FILE_FORMATS": {
            "gzip compressed data": "UNPACK",
            "tar": "UNPACK",
            "Zip archive data": "UNPACK",
            "7-zip archive data": "UNPACK",
            "ASCII text": "ANALYSE",
            "UTF-8 Unicode": "ANALYSE"
        },
        "HIDE_FROM_INFO_DETAILS": [
            "errors",
            "summary",
            "error_filename",
            "FILTERS"
        ],
        "ALERT_TYPE_LIST": [
            "info",
            "warning",
            "error",
            "ignore"
        ],
        "SHOW_ERROR_MAX_LINES": 50,
        "MAX_PAGES_TABS": 20,
        "TABLE_AUTO_NUMBERING_CONFIG": {
            "No": [
                5,
                "^",
                "^"
            ]
        },
        "TABLE_CONFIG": {
            "File information": {
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 200,
                    "COLUMNS": 175,
                    "ROWS": 10
                }
            },
            "Log Viewer": {
                "HIGHLIGHT": {
                    "Line": {
                        "--": "#ffa500"
                    },
                    "Severity": {
                        "INFO": "#3cb371",
                        "WARN": "#ffa500",
                        "ERROR": "#ff0000/#ffffff"
                    }
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 154,
                    "ROWS": 6
                },
                "LINE_DETAILS": {
                    "SHOW": True,
                    "COLOR_SCHEME": 1,
                    "COLUMN_DETAILS": [
                        "Message"
                    ],
                    "CHECK_OPTIONS": {
                        "Number of suspends": "SHOW_ONLY"
                    },
                    "CHECK": {
                        "Number of suspends": [
                            "numberOfSuspends=(\\d+)"
                        ],
                        "Session id": [
                            "session_id=([a-zA-Z0-9-]+)",
                            "sessionId=([a-zA-Z0-9-]+)"
                        ],
                        "Flow id": [
                            "flow-id=([a-zA-Z0-9-]+)",
                            "[Ff]low \\[([a-zA-Z0-9-]+)\\]",
                            "PersistCheckpoint\\(id=\\[([a-zA-Z0-9-]+)\\]",
                            "Flow with id ([a-zA-Z0-9-]+) has been waiting ",
                            "flowId=\\[([a-zA-Z0-9-]+)",
                            "flowId=([a-zA-Z0-9-]+)",
                            "Affected flow ids: ([a-zA-Z0-9- ,]+)"
                        ],
                        "TX id": [
                            "tx_id=([a-zA-Z0-9-]+)",
                            "NotaryException: Unable to notarise transaction ([a-zA-Z0-9-]+) :",
                            "hashOfTransactionId=([a-zA-Z0-9-]+)",
                            "([0-9A-Z]+)\\([0-9]+\\)\\s+->\\sStateConsumptionDetails\\(hashOfTransactionId=[0-9A-Z]+",
                            "The duplicate key value is\\s*\\(([A-Z0-9]+)\\)",
                            "hashOfTransactionId=([A-Z0-9]+)",
                            "ref=([a-zA-Z0-9-]+)",
                            "Tx \\[([a-zA-Z0-9-]+)\\]",
                            "Transaction \\[([a-zA-Z0-9-]+)\\]"
                        ],
                        "Owner id": [
                            "actor_owning_identity=CN=([0-9A-Za-z- .]+),",
                            "actor_owningIdentity=O=([0-9A-Za-z- .]+),"
                        ],
                        "Thread id": [
                            "thread-id=(\\d+)"
                        ],
                        "Party-Anonymous": [
                            "party=Anonymous\\(([a-zA-Z-0-9]+)\\)"
                        ],
                        "Message id": [
                            "id=[A-Z-]{4}([0-9-]{39})[0-9-]{2,};"
                        ]
                    },
                    "HIDE_DATAX": {
                        "HIDING_PASSWORD": "[Pp]assword\\s*=\\s*\\\"?([a-z0-9A-Z-@%+_\\?\\|\\/\\(\\)\\[\\]]*)\\\"?"
                    }
                },
                "TABLE_RENDER_ENGINE": {
                    "REQUEST_ON_TOP": 25,
                    "REQUEST_ON_BOTTOM": 80,
                    "BATCH_ROW_REQUEST": 100,
                    "IGNORE_COLUMN_SIZE": ["Message"],
                    "FORCE_HEADER_PREFIX": {
                        "Line": "header",
                        "Timestamp": "header",
                        "Severity": "header",
                        "Message": "header"
                    }
                }
            },
            "Temporal-LogViewer": {
                "COMMENTS": "This table is created to support Log Viewer scrolling",
                "HIGHLIGHT": {
                    "Line": {
                        "--": "#ffa500"
                    },
                    "Severity": {
                        "INFO": "#3cb371",
                        "WARN": "#ffa500",
                        "ERROR": "#ff0000/#ffffff"
                    }
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 154,
                    "ROWS": 6
                },
                "LINE_DETAILS": {
                    "SHOW": True,
                    "COLOR_SCHEME": 1,
                    "COLUMN_DETAILS": [
                        "Message"
                    ],
                    "CHECK_OPTIONS": {
                        "Number of suspends": "SHOW_ONLY"
                    },
                    "CHECK": {
                        "Number of suspends": [
                            "numberOfSuspends=(\\d+)"
                        ],
                        "Session id": [
                            "session_id=([a-zA-Z0-9-]+)",
                            "sessionId=([a-zA-Z0-9-]+)"
                        ],
                        "Flow id": [
                            "flow-id=([a-zA-Z0-9-]+)",
                            "[Ff]low \\[([a-zA-Z0-9-]+)\\]",
                            "PersistCheckpoint\\(id=\\[([a-zA-Z0-9-]+)\\]",
                            "Flow with id ([a-zA-Z0-9-]+) has been waiting ",
                            "flowId=\\[([a-zA-Z0-9-]+)",
                            "flowId=([a-zA-Z0-9-]+)",
                            "Affected flow ids: ([a-zA-Z0-9- ,]+)"
                        ],
                        "TX id": [
                            "tx_id=([a-zA-Z0-9-]+)",
                            "NotaryException: Unable to notarise transaction ([a-zA-Z0-9-]+) :",
                            "hashOfTransactionId=([a-zA-Z0-9-]+)",
                            "([0-9A-Z]+)\\([0-9]+\\)\\s+->\\sStateConsumptionDetails\\(hashOfTransactionId=[0-9A-Z]+",
                            "The duplicate key value is\\s*\\(([A-Z0-9]+)\\)",
                            "ref=([a-zA-Z0-9-]+)",
                            "Tx \\[([a-zA-Z0-9-]+)\\]",
                            "Transaction \\[([a-zA-Z0-9-]+)\\]"
                        ],
                        "Owner id": [
                            "actor_owning_identity=CN=([0-9A-Za-z- .]+),",
                            "actor_owningIdentity=O=([0-9A-Za-z- .]+),"
                        ],
                        "Thread id": [
                            "thread-id=(\\d+)"
                        ],
                        "Party-Anonymous": [
                            "party=Anonymous\\(([a-zA-Z-0-9]+)\\)"
                        ],
                        "Message id": [
                            "id=[A-Z-]{4}([0-9-]{39})[0-9-]{2,};"
                        ]
                    },
                    "HIDE_DATAX": {
                        "HIDING_PASSWORD": "[Pp]assword\\s*=\\s*\\\"?([a-z0-9A-Z-_\\?\\|\\/\\(\\)\\[\\]]*)\\\"?"
                    }
                }
            },
            "Jira Alerts": {
                "HIGHLIGHT": {
                    "Severity": {
                        "SEV1": "#ff0000/#ffffff",
                        "SEV2": "#ffa500"
                    }
                },
                "OPTIONS": {
                    "CLASS": "screenboard"
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 155,
                    "ROWS": 4
                }
            },
            "Customer logs": {
                "ORDER_ON": [
                    "Name",
                    "Number logs Loaded"
                ]
            },
            "Details for": {
                "HIGHLIGHT": {
                    "Error message Level": {
                        "INFO": "#3cb371",
                        "WARN": "#ffa500",
                        "ERROR": "#ff0000/#ffffff"
                    },
                    "Alert Level DataDog": {
                        "info": "#3cb371",
                        "warning": "#ffa500",
                        "error": "#ff0000/#ffffff"
                    },
                    "Alert Level (DataDog)_DropDown": {
                        "selected>info": "#3cb371",
                        "selected>warning": "#ffa500",
                        "selected>error": "#ff0000"
                    }
                },
                "ORDER_ON": [
                    "No",
                    "Line",
                    "Error type",
                    "Error message Level"
                ],
                "FILTER_ON": {
                    "Error message Level": {
                        "OPTIONS_SOURCE": "TABLE"
                    }
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 500,
                    "COLUMNS": 150,
                    "ROWS": 10
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            },
            "Log Summary": {
                "HIGHLIGHT": {
                    "File Analysis status": {
                        "Complete": "#669900",
                        "Processing": "#cc9900",
                        "Pending": "#0066ff",
                        "Error": "#ff6666",
                        "*Not Started*": "#cc6699",
                        "On-Hold": "#9900cc/#ffffff",
                        "Cancelled": "#acac86",
                        "Preparing": "#99ceff",
                        "Delete": "#cc3300",
                        "Deleting": "#cc3300",
                        "Setting up": "#6699ff",
                        "Failed": "#acac86"
                    }
                },
                "FILTER_ON": {
                    "Jira Ticket": {
                        "OPTIONS_SOURCE": "DATABASE",
                        "TABLE_FIELD_NAME": "ticket_number"
                    },
                    "Corda Version": {
                        "OPTIONS_SOURCE": "DATABASE",
                        "TABLE_FIELD_NAME": "corda_version"
                    },
                    "File Analysis status": {
                        "OPTIONS_SOURCE": "DATABASE",
                        "TABLE_FIELD_NAME": "status"
                    }
                },
                "ORDER_ON": [
                    "Log",
                    "Uploaded on",
                    "Jira Ticket",
                    "Starting Date",
                    "Ending Date",
                    "File Name",
                    "Corda Version",
                    "Line count",
                    "Errors found",
                    "File Analysis status"
                ],
                "PAGINATION": {
                    "MAX_ITEMS_PER_PAGE": 50,
                    "MAX_TABS_PER_PAGE": 10
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 500,
                    "COLUMNS": 150,
                    "ROWS": 10
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            },
            "Actual alerts": {
                "HIGHLIGHT": {
                    "Alert Level": {
                        "info": "#3cb371",
                        "warning": "#ffa500",
                        "error": "#ff0000/#ffffff"
                    }
                },
                "SORTING": {
                    "BY_COLUMN": "Time",
                    "DIRECTION": "reverse"
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 155,
                    "ROWS": 4
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            },
            "Actual alerts_dropDown": {
                "HIGHLIGHT": {
                    "Alert Level": {
                        "selected>info": "#3cb371",
                        "selected>warning": "#ffa500",
                        "selected>error": "#ff0000"
                    }
                },
                "SORTING": {
                    "BY_COLUMN": "Time",
                    "DIRECTION": "reverse"
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 155,
                    "ROWS": 4
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            }
        }
    }

    @staticmethod
    def add_config_cache(variable_to_get, value):
        """
        Create a dictionary of frequently accessed variables.
        :param variable_to_get: actual variable to get
        :param value: value to store
        :return: None
        """

        Configs.config_access_cache[variable_to_get] = value

    @staticmethod
    def get_config_cached_variable(variable_to_get):
        """
        Access variable saved in memory
        :param variable_to_get: actual variable required
        :return: value contained
        """

        if variable_to_get in Configs.config_access_cache:
            return Configs.config_access_cache[variable_to_get]

        return None


    @staticmethod
    def load_config():
        """
        Cargar todas las definiciones y configuraciones,
        esto tambien carga las reglas y definicion de objetos todo en un solo metodo
        :return:
        """

        file = "%s/conf/support.json" % (os.path.dirname(os.path.abspath(__file__)),)
        rule_file = "%s/conf/logwatcher_rules.json" % (os.path.dirname(os.path.abspath(__file__)),)

        try:
            with open(file, "r") as fconfig:
                # Configs.config = json.load(fconfig)["CONFIG"]
                Configs.config = json.load(fconfig)
            write_log("Configuration loaded...")

            with open(rule_file, "r") as fconfig:
                rule_file =  json.load(fconfig)

            for each_process in rule_file["WATCH_FOR"]:
                for each_rule in rule_file["WATCH_FOR"][each_process]:
                    rule = Rules()
                    rule.add("process", each_process)
                    rule.add("name", each_rule)
                    for each_attribute in rule_file["WATCH_FOR"][each_process][each_rule]:
                        rule.add(each_attribute, rule_file["WATCH_FOR"][each_process][each_rule][each_attribute])

                    rule.register()

                    config = rule_file['UML_SETUP']
                    Configs.set_config(config_value=config["CORDA_OBJECTS"], section="CORDA_OBJECTS")
                    Configs.set_config(config_value=config["CORDA_OBJECT_DEFINITIONS"], section="CORDA_OBJECT_DEFINITIONS")
                    Configs.set_config(config_value=config["UML_DEFINITIONS"], section="UML_DEFINITIONS")
                    Configs.set_config(config_value=config["UML_ENTITY"], section="UML_ENTITY")
                    Configs.set_config(config_value=config["UML_CONFIG"], section="UML_CONFIG")
                    Configs.set_config(config_value=config["UML_HIGHLIGHT"], section="UML_HIGHLIGHT")
                    Configs.set_config(config_value=rule_file['VERSION'], section="VERSION")
                    Configs.set_config(config_value=rule_file["BLOCK_COLLECTION"], section="BLOCK_COLLECTION")
                    Configs.set_config(config_value=rule_file["FILE_SETUP"], section="FILE_SETUP")
                    Configs.set_config(config_value=rule_file['WATCH_FOR'], section='WATCH_FOR')
            write_log("Object definition and rules loaded")

        except IOError as io:
            write_log("ERROR loading config file: %s" % io)

            exit(1)
        except ValueError as ve:
            write_log("ERROR corrupted config file: %s" % ve)

            exit(1)

    @staticmethod
    def regex_expression(regex):
        """
        Expect a regex expresion, and will return compiled version if is stored,
        compile, store new compiled regex, and return compiled version
        :param regex: human readable regex string
        :return: compiled regex expression
        """

        regex_code = generate_hash(regex)

        if regex_code in Configs.compiled_regex:
            return Configs.compiled_regex[regex_code]

        compile_regex = re.compile(regex)

        Configs.compiled_regex[regex_code] = compile_regex

        return compile_regex

    @staticmethod
    def __init__(config_loaded, section="CONFIG"):

        Configs.config[section] = config_loaded

    @classmethod
    def get_config(cls, param=None, sub_param=None, section="CONFIG", similar=False):
        """
        Return requested parameter from config files.
        :param param: represents section at config file to look at
        :param sub_param: Represents a sub-section at the config file
        :param similar: it will indicate to do a similar search; as given sub_param is not exactly same as config, it
        is probably a sub-string of real subparameter.
        :return:
        """
        global app_path_support
        if not Configs.config:
            Configs.load_config()

        if not param and section in Configs.config:
            return Configs.config[section]

        if param not in Configs.config[section]:
            return None

        # If a similar search is being requested then do a reverse search, compare all sub_params from param
        # with the given sub_parameter
        #
        if similar:
            for each_subparam in Configs.config[section][param]:
                found_match = re.search(each_subparam, sub_param)
                if found_match:
                    return Configs.config[section][param][each_subparam]

            return None

        if not sub_param and param in Configs.config[section]:
            return Configs.config[section][param]

        if param and sub_param:
            if param in Configs.config[section] and sub_param in Configs.config[section][param]:
                return Configs.config[section][param][sub_param]
            else:
                return None

        if param in Configs.config[section]:
            return Configs.config[section][param]
        else:
            write_log("[CONFIGURATION] %s parameter do not exist under %s section" % (sub_param, param))
            return None

    @classmethod
    def set_config(cls, config_attribute=None, config_value=None, section="CONFIG"):
        """
        Set a value temporarly into config settings in memory, anything that is being set here will not be persistent on
        restarts
        :param config_attribute: attribute name to setup, if no attributte name is given, then method will expect a
        tree of values (a dictionary) to be attached to given section directly
        :param config_value: attribute value
        :param section: root section name for this attribute, all by default will be set under "CONFIG" branch section
        :return:
        """

        if config_attribute and config_value:
            Configs.config[section][config_attribute] = config_value

        if not config_attribute and config_value:
            Configs.config[section] = config_value

    @staticmethod
    def get_config_from(path_value):
        """

        :param path_value:
        :return:
        """
        configs = Configs.config
        variables = path_value.split(":")

        for each_variable in variables:
            if each_variable in configs:
                configs = configs[each_variable]
            else:
                return None

        return configs

    @staticmethod
    def get_config_for(path_value):
        """
        A simplified method to get access to a final variable
        :param path_value: dot noted version for variable to access
        :return: value of such variable, or None otherwise
        """
        value = Configs.get_config_cached_variable(path_value)
        if value:
            return value

        _,access = generate_internal_access(Configs.config, path_value)
        Configs.add_config_cache(path_value,access)

        return access

class Rules:
    rule_list = {}

    def __init__(self):
        self.attributes = {}

    def add(self, attribute, value):
        self.attributes[attribute] = value

    def get(self, attribute):
        if attribute not in self.attributes:
            return None

        return self.attributes[attribute]

    def get_section(self, section, attribute):
        if section in self.attributes and attribute in self.attributes[section]:
            return self.attributes[section][attribute]

    def add_results(self, error_id, result, location):
        if "results" not in self.attributes:
            self.attributes["results"] = {}
        if location not in self.attributes["results"]:
            self.attributes["results"][location] = {}

        self.attributes["results"][location][error_id] = result

    def get_results(self, location=None):
        """
        Will return a list of results from this accordingly with the trigger conditions
        :param location: if location is being specified and exist, will return all results
        for such location, if no location is being specified will return all current stored results
        :return:
        """
        if "results" in self.attributes:
            if not location:
                return self.attributes["results"]
            else:
                if location in self.attributes["results"]:
                    return self.attributes["results"][location]

        return None

    def get_triggers(self, condition=None):
        """
        Will return a dictionary of current triggering actions for this rule, or the
        trigger statement for given condition
        :return:
        """
        triggers = {}

        if 'trigger' in self.attributes:
            if not condition:
                for each_trigger in self.attributes["trigger"]:
                    triggers[each_trigger] = self.attributes["trigger"][each_trigger]
            else:
                if condition in self.attributes['trigger']:
                    return self.attributes['trigger'][condition]
                else:
                    return None
        else:
            return None

        return triggers

    def get_parsed_trigger(self, condition=None):
        """
        Will return a dictionary of current triggering actions for this rule, or the
        trigger statement for given condition
        :return:
        """
        triggers = {}

        if 'parsed_trigger' in self.attributes:
            if not condition:
                for each_trigger in self.attributes["parsed_trigger"]:
                    triggers[each_trigger] = self.attributes["parsed_trigger"][each_trigger]
            else:
                if condition in self.attributes['parsed_trigger']:
                    return self.attributes['parsed_trigger'][condition]
                else:
                    return None
        else:
            return None

        return triggers

    def validate(self, error):
        error_id = error.get("error_id")

        if not error_id:
            return None

        results = None
        if not self.get_parsed_trigger():
            return None

        for each_condition in self.get_parsed_trigger():
            rule_actions = self.get_parsed_trigger(each_condition)

            if not rule_actions:
                return None

            if "location" in rule_actions:
                if rule_actions["location"] == "at same":
                    results = self.get_results(error.get("location"))
                if rule_actions["location"] == "at different":
                    results = self.get_results()

            if results and "occurrence" in rule_actions:
                if len(results) >= int(rule_actions["occurrence"]):
                    return results
                else:
                    # Given error do not pass the condition; then return a empty list
                    return {error.get("error_type"): {}}
            else:
                # Given error do not have
                return None

    def register(self):
        """
        Register a new rule
        :return:
        """
        self.parse_triggers()
        Rules.rule_list[self.get("name")] = self

    def parse_triggers(self):
        """
        Method to convert english text into parsed actions for current rule
        :return: a dictionary with parsed rules
        """
        action = {}
        rule_rgx = {
            "alert_on_occurrence": r"(\d+) time. (within) (\d+)[mhs] (at same|at different) (\w+)"
        }

        if self.get_triggers():
            for each_trigger in self.get_triggers():
                for rtrigger in self.get_triggers():
                    rtrigger_rgx = re.search(rule_rgx[each_trigger],
                                             self.get_triggers(rtrigger))
                    if rtrigger_rgx:
                        action[rtrigger] = {
                            "occurrence": rtrigger_rgx.group(1),
                            "within": int(rtrigger_rgx.group(3)),
                            "location": rtrigger_rgx.group(4),
                            "variable": rtrigger_rgx.group(5)
                        }
                        self.add("parsed_trigger", action)
        pass

    def get_attributes(self):
        return list(self.attributes)

    @staticmethod
    def get_rule(rule_name):
        if rule_name in Rules.rule_list:
            return Rules.rule_list[rule_name]

    @staticmethod
    def load():
        """
        Load all defined rules
        :return:
        """
        app_path = os.path.dirname(os.path.abspath(__file__))
        with open('%s/conf/logwatcher_rules.json' % (app_path,), 'r') as fregex_strings:
            rule_file = json.load(fregex_strings)

        for each_process in rule_file["WATCH_FOR"]:

            for each_rule in rule_file["WATCH_FOR"][each_process]:
                rule = Rules()
                rule.add("process", each_process)
                rule.add("name", each_rule)
                for each_attribute in rule_file["WATCH_FOR"][each_process][each_rule]:
                    rule.add(each_attribute, rule_file["WATCH_FOR"][each_process][each_rule][each_attribute])

                rule.register()
        config = rule_file['UML_SETUP']
        Configs.set_config(config_value=config["CORDA_OBJECTS"], section="CORDA_OBJECTS")
        Configs.set_config(config_value=config["CORDA_OBJECT_DEFINITIONS"], section="CORDA_OBJECT_DEFINITIONS")
        Configs.set_config(config_value=config["UML_DEFINITIONS"], section="UML_DEFINITIONS")
        Configs.set_config(config_value=config["UML_ENTITY"], section="UML_ENTITY")
        Configs.set_config(config_value=config["UML_CONFIG"], section="UML_CONFIG")

class RegexLib:
    """
    Keep a cache of compiled regex, to be able to re-use them.
    """

    compiled_regex_cache = {}
    check_variable = re.compile(r"__([a-zA-Z0-9-_]+)__")
    most_used_regex = {}


    @staticmethod
    def use(rx_expression):
        """
        Will try to keep a cached compiled version of which regex are most used so it will not need to re-compile them
        again.
        :param rx_expression: regex expression to search for
        :return: compiled version of given regex
        """

        signature = generate_hash(rx_expression)

        if signature not in RegexLib.compiled_regex_cache:
            RegexLib.compiled_regex_cache[signature] = re.compile(rx_expression)
            return RegexLib.compiled_regex_cache[signature]

        return RegexLib.compiled_regex_cache[signature]

    @staticmethod
    def regex_to_use(regex_list, message_line, force_groups=False,line_no=None, timeout=25000):
        """
        Given a regex_list, which will contain all regex; and the line to find out which regex
        can be applied into it
        :param regex_list: a regex list with all possible regex to try
        :param message_line: the actual message that need to be parsed
        :param force_groups: if given list of regex has no groups on it, this method will fail as it depends on
        groups defined withing regex expression
        :return: regex index to be used or None if there're no possible regex matches.
        """

        if force_groups:
            rgx_list = []
            for item in regex_list:
                rgx_list.append(f'({item})')
            regex_list = rgx_list

        #
        # In order to join all regex into one, I need to remove any group names as it can make conflicts
        no_group_names = clear_groupnames(regex_list)
        #
        # I need to get actual group references for the concatenated regex. this will help to
        # identify correct regex to use
        concatenated_idx_groups = RegexLib.set_concatenated_index_groups(no_group_names)
        # Join all regex into one

        all_expects = '|'.join(no_group_names)

        group_idx_match = None
        start_time = time.time()
        try:
            # Check if given line has a valid regex to be applied
            expression = RegexLib.use(all_expects)

            # with TimeoutError.Timeout(second=0.5):
            if timeout:
                check_match = expression.findall(message_line, timeout=timeout)
            else:
                check_match = expression.findall(message_line)
            elapsed = time.time() - start_time
            if elapsed*1000 > 10000:  # Más de 500ms
                if line_no:
                    write_log(f"⚠️ Line:{line_no:<6} -- Slow regex ({elapsed*1000:.2f}ms) line contains {len(message_line)} chars",
                              level="WARN")
                else:
                    write_log(f"⚠️ Slow regex ({elapsed*1000:.2f}ms) line contains {len(message_line)} chars",
                              level="WARN")
            # check_match = re.findall(all_expects, message_line)
            #
            # Using result from findall; search which group was valid
            #
            if not check_match:
                return None
            match_expression_index = next(a for a, b in enumerate(check_match[0]) if b)
            # I've found a good group save it for reference
            group_idx_match = match_expression_index

        except BaseException as be:
            # No regex has a match with given line
            return None
        except TimeoutError:
            pass


        # If we don't match any regex for this line, then doesn't make sense to continue with it... return None
        if group_idx_match is None:
            return None

        expect_to_use = concatenated_idx_groups[group_idx_match]

        # A matching regex was found, return actual index that will work:

        return expect_to_use

    @staticmethod
    def set_concatenated_index_groups(regex_list):
        """
        This method will create an array with list of regex indexes, this will help to locate the proper regex,
        when they are concatenated

        :param regex_list: List of regex expressions to scan
        :return: list of reference indexes for groups
        """
        group_pos = 0
        index_grp = []
        # group_data = {}

        for index, each_string in enumerate(regex_list, start=0):
            try:
                rexp = re.compile(each_string)
                no_groups = rexp.groups

            except re.error as ree:
                write_log(f"ERROR: Detected malformed pattern: {each_string} ")
                write_log("from processing list: %s" % regex_list)
                continue

            # group_data[index] = {
            #     "groups": [grp+group_pos for grp in range(1, no_groups + 1)]
            # }

            for grp_no in range(group_pos, group_pos + no_groups):
                index_grp.append(index)

            group_pos += no_groups

        return index_grp


    @staticmethod
    def build_regex(regex, nogroup_name=False):
        """
        This method will scan given regex to check if a "macro"(regex inside a regex) was included, if so will look for that
        and replace it with its value; then will return complete regex expression
        :param regex: regex to examine
        :param nogroup_name: this will cause returning pattern to avoid setting up group name within regex pattern
        :return: complete regex expression if a variable needs to be replaced, original regex expression otherwise
        """
        return_regex = regex

        if regex in RegexLib.most_used_regex:
            return RegexLib.most_used_regex[regex]

        if not Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS"):
            return return_regex

        check_variable = RegexLib.check_variable.findall(regex)

        if check_variable:
            org_regex = regex
            for each_variable in check_variable:
                # Search where this variable could be applicable to then extract the proper regex replacement for such
                # variable
                #
                for each_object in Configs.get_config_for("CORDA_OBJECT_DEFINITIONS.OBJECTS").keys():
                # for each_object in Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS").keys():
                    apply_to = None
                    # cfg_setup = Configs.get_config_for(f"CORDA_OBJECT_DEFINITIONS.OBJECTS.{each_object}")
                    # if "APPLY_TO" in cfg_setup:
                    #     apply_to = cfg_setup["APPLY_TO"]
                    if "APPLY_TO" in Configs.get_config(section="CORDA_OBJECT_DEFINITIONS",
                                                        param="OBJECTS", sub_param=each_object):
                        apply_to = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS",
                                                      param="OBJECTS",
                                                      sub_param=each_object)["APPLY_TO"]
                    else:
                        write_log("Warning: %s has no 'APPLY_TO' parameter,"
                              " so I'm not able to identify the match for this label..." %
                              (each_object,))
                    #
                    # if apply_to list has a content, and check_variable appear in such list, then proceed to do replacement
                    if apply_to and each_variable in apply_to:
                        list_expects = "|".join(Configs.get_config(
                            section="CORDA_OBJECT_DEFINITIONS",
                            param="OBJECTS",
                            sub_param=each_object
                        )["EXPECT"])

                        if nogroup_name:
                            regex_replace = "(%s)" % (list_expects,)
                        else:
                            regex_replace = "(?P<%s>%s)" % (
                                each_variable,
                                list_expects
                            )
                        return_regex = regex.replace("__%s__" % each_variable, regex_replace)

                        # if more than one variable is being found make sure to keep previous change before replacing
                        # following variable

                        regex = return_regex
            # Store this regex combination it is possible will be used later
            RegexLib.most_used_regex[org_regex] = return_regex
        else:
            # If I do not find the macro variable in the form of "__macro-variable__" then I will need to do a reverse
            # search, to find the actual object... because what I'm sending then is probably a raw Object  definition
            object_definition = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS")
            for each_object in object_definition:
                if regex in object_definition[each_object]['EXPECT']:
                    if nogroup_name:
                        regex_replace = "(%s)" % (regex,)
                    else:
                        regex_replace = "(?P<%s>%s)" % (
                            each_object,
                            regex
                        )
                    return_regex = regex_replace

        return return_regex

    class Search:
        # def __init__(self, pattern, string, flags=re.MULTILINE):
        #     """
        #     An emulation to what re.search commands does, but I will add more support for it as I need the command to
        #     search on the whole string and extract all matches with the format of what "re.search" does.
        #
        #     :param pattern: pattern to match
        #     :param string: string to search pattern
        #     :param flags: on re
        #     :return: re.search class
        #     """
        #     # Extract all values for this match
        #     self.match_found = re.findall(pattern, string, flags)
        #     # A plain list to track duplicated values
        #     tpaux = []
        #     # Extract all labels/group names for this specific regex pattern
        #     #
        #     group_name = re.findall(r"\?P\<([a-z-_]+)\>", pattern)
        #
        #     # Group assignation must be done in appearance order
        #     value_position = 0
        #     if self.match_found:
        #         self.tp = []
        #         for each_match in self.match_found:
        #             # Ignore first match as it represent whole original line to scan
        #             #
        #             if type(each_match) == tuple:
        #                 for each_item in each_match:
        #                     if value_position > 0:
        #                         if each_item not in tpaux:
        #                             self.tp.append({group_name[value_position-1]: each_item})
        #                             tpaux.append(each_item)
        #                     value_position += 1
        #             else:
        #                 self.tp.append({group_name[value_position]: each_match})
        #                 tpaux.append(each_match)

        def __init__(self, pattern, string, flags=re.MULTILINE, timeout=None):
            if timeout:
                matches = re.finditer(pattern, string, flags, timeout=timeout)
            else:
                matches = re.finditer(pattern, string, flags)

            self.tp = ()
            for matchNum, match in enumerate(matches, start=1):
                #
                # write_log("Match {matchNum} was found at {start}-{end}:
                # {match}".format(matchNum=matchNum, start=match.start(),
                # end=match.end(), match=match.group()))

                for groupName in match.groupdict():
                    # write_log("Group {groupName}: {group}".format(groupName=groupName,
                    #                                           group=match.group(groupName)))
                    self.tp += ({groupName: match.group(groupName)},)

        def groupdict(self):
            """
            Will return a list of dictionaries containing, grouped key
            :return: a list of dictionaries
            """
            return self.tp

        def groupdictkeys(self):
            """
            Return all keys contained on list of dictionaries
            :return: a list of keys
            """
            keys = []
            for each_dict in self.tp:
                for each_key in each_dict:
                    keys.append(each_key)

            return keys

        def groups(self):
            """
            Will respond with a tuple list containing all values found
            :return: tuple
            """
            values = ()
            for each_dict in self.tp:
                for each_key in each_dict:
                    values += (each_dict[each_key],)

            return values

        def group(self, group=None):
            """
            Will return desired group, will return all groups if no-one is specified will return all groups
            :param group: requested group
            :return: required group or all group if none is specified
            """
            ltr = []
            if not group:
                return [tpx for tpx in self.tp if tpx.values()]

            if type(group) == str:

                for each_dict in self.tp:
                    for each_item in each_dict:
                        if each_item == group:
                            ltr.append(each_dict)

            return ltr

class BlockItems:
    """
    Items that conform a block of useful collected data
    """

    def __init__(self):
        """
        Represents a block of related log lines, such as a flow transition or a stack trace error.
        """
        self.timestamp: Optional[str] = None
        self.line_number: Optional[int] = None
        self.reference: Optional[str] = None
        self.content: List[str] = []
        self.type: Optional[str] = None
        # self.block_collection_type = Configs.get_config_for('BLOCK_COLLECTION.COLLECT')

    def __str__(self):
        return f"[{self.type} @ line {self.line_number}] {len(self.content)} lines"

    def get_content(self, idx=None):

        if not idx:
            return self.content

        if idx > len(self.content):
            return None

        if 0 <= idx < len(self.content):
            return self.content[idx]


class BlockExtractor:
    """
    Extracts structured blocks from a log file, driven by regex patterns defined in a config dictionary.
    """
    def __init__(self, file_mgm: FileManagement, config: Dict):
        self.file_path = file_mgm.filename
        self.config = config
        # self.collected_blocks: Dict[str, List[BlockItems]] = {}
        self.collected_blocks = {}
        self.log_line_start_regex = file_mgm.log_line_regex

        # Parse and compile block patterns from config
        self.block_types = config.get("BLOCK_COLLECTION", {}).get("COLLECT", {})
        self.compiled_patterns = {
            block_name: {
                "start": [re.compile(RegexLib.build_regex(p)) for p in block_def["START"]["EXPECT"]],
                "end": [re.compile(RegexLib.build_regex(p)) for p in block_def.get("END", {}).get("EXPECT", [])]
            }
            for block_name, block_def in self.block_types.items()
        }

        # Extract reference keys (e.g., flow_id) from config
        self.references = {}
        for each_type in self.block_types:
            if "REFERENCE_ID" in self.block_types[each_type]:
                rreference = []
                for each_reference in self.block_types[each_type]['REFERENCE_ID']:
                    rreference.append(re.compile(RegexLib.build_regex(each_reference)))

                self.references[each_type] = rreference

    def _is_log_line_start(self, line: str) -> bool:
        if self.log_line_start_regex:
            return bool(self.log_line_start_regex.match(line))
        return line.startswith("[")

    def extract(self):
        """
        Parses the file and extracts blocks based on the configured patterns.
        """
        write_log("Analysis of blocks...")
        current_blocks: Dict[str, BlockItems] = {}
        in_block: Dict[str, bool] = {key: False for key in self.block_types}
        line_check = 0 # check how many lines were taking in account after a block indentification...
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:

                for line_number, line in enumerate(f, 1):
                    for block_name, patterns in self.compiled_patterns.items():
                        # Start match with access to match object

                        for p in patterns["start"]:
                            match = p.match(line)
                            if match:
                                reference_key = self.references.get(block_name)
                                blk = BlockItems()
                                blk.line_number = line_number
                                blk.type = block_name
                                blk.reference = None
                                # Check if given line has a matching reference
                                # TODO: refactor this...

                                if not blk.reference:
                                    blk.reference = self._look_for_reference_id(block_name, line)

                                # if reference_key and reference_key in match.groupdict():
                                #     blk.reference = match.group(reference_key)
                                # # if there're no explicit reference to pick up, let's assign line number as reference.
                                # if not reference_key:
                                #     blk.reference = f"{line_number}"

                                if line not in blk.content:
                                    blk.content.append(line)

                                if in_block.get(block_name) and current_blocks.get(block_name):
                                    self._store_block(block_name, current_blocks[block_name])

                                current_blocks[block_name] = blk
                                in_block[block_name] = True
                                break  # Stop checking further patterns for this line

                        # End match (optional)
                        if in_block.get(block_name) and patterns["end"]:
                            if any(p.match(line) for p in patterns["end"]):
                                current_blocks[block_name].content.append(line)
                                self._store_block(block_name, current_blocks[block_name])
                                in_block[block_name] = False
                                continue

                        # Inside block logic
                        if in_block.get(block_name):
                            if not self._is_log_line_start(line):
                                if line not in current_blocks[block_name].content:
                                    current_blocks[block_name].content.append(line)
                                continue
                            else:
                                # Force collection, actual block contents has not stacktrace, or any other
                                # information, so get next line...
                                if len(current_blocks[block_name].content) < 2 and line_check == 0:
                                    line_check += 1
                                    continue

                                # Found a new log line while in a block: close current block first
                                self._store_block(block_name, current_blocks[block_name])
                                in_block[block_name] = False
                                line_check = 0
                                # Do NOT continue: this line may start another block

                        # Implicit end of block
                        if in_block.get(block_name):
                            self._store_block(block_name, current_blocks[block_name])
                            in_block[block_name] = False
        except IOError as io:
            write_log(f'Sorry unable to open {self.file_path} due to: {io}')
            return
        except UnicodeDecodeError as ue:
            write_log(f'Sorry unable to open {self.file_path} due to: {ue}')
            return

        # Store remaining open blocks
        for block_name, blk in current_blocks.items():
            if in_block.get(block_name) and blk.content:
                self._store_block(block_name, blk)

        pass

    def _look_for_reference_id(self, block_type, line):
        """
        Look for references Id's defined at configuration; for now it will return
        very first one that makes a match...
        :param line: log line to check
        :return: reference that match with configured regex...
        """

        for each_reference in self.references[block_type]:
            match = each_reference.search(line)
            if match:
                return match.group(1)

        return None


    def _store_block(self, block_type: str, blk: BlockItems):
        """
        Store blocks found
        :param block_type: type of block to store
        :param blk: block items to store
        :return: None
        """
        if block_type not in self.collected_blocks:
            self.collected_blocks[block_type] = {}

        if not blk.reference:
            # If not reference was found will use line number...
            blk.reference = blk.line_number

        if blk.reference not in self.collected_blocks[block_type]:
            self.collected_blocks[block_type][blk.reference] = []

        self.collected_blocks[block_type][blk.reference].append(blk)


    def get_blocks(self, block_type: str) -> List[BlockItems]:
        return self.collected_blocks.get(block_type, [])

    def summary(self):
        for block_type, blocks in self.collected_blocks.items():
            write_log(f"{block_type}: {len(blocks)} blocks collected.")

    def get_reference(self, reference_id=None, block_type=None):
        """
        Look for given reference and return what is found
        :param reference_id: to look for
        :param block_type: block to get reference from; or a list of all blocks types found
        :return: a dictionary specifying which block type reference id was found, None otherwise
        """

        results = {}
        if reference_id:
            # Returns a dictionary with blocks where given reference was found.
            if not block_type:
                for each_type in self.collected_blocks:
                    if reference_id in self.collected_blocks[each_type]:
                        results[each_type] = self.collected_blocks[each_type][reference_id]

                return results
            else:
                if block_type in self.collected_blocks:
                    if reference_id:
                        if reference_id in self.collected_blocks[block_type]:
                            # return {block_type: self.collected_blocks[block_type][reference_id]}
                            return self.collected_blocks[block_type][reference_id]
                        else:
                            return None
                    else:
                        return self.collected_blocks[block_type]

            return None

        if not reference_id and not block_type:
            # Return a dictionary with all blocks found
            for each_type in self.collected_blocks:
                results[each_type] = self.collected_blocks[each_type]

            return results

        if not reference_id and block_type and block_type in self.collected_blocks:
            # return a list of references for given block_type
            return self.collected_blocks[block_type]

        return None

    def get_collected_block_types(self, block_type=None, only_list=False):
        """
        Return all block types found on analyzed log
        :return: a dictionary with all collected types including number of items on each case
        """

        types = None
        if self.collected_blocks:
            if only_list:
                # Return only a list of keys no counts
                return list(self.collected_blocks.keys())

            types = {}
            if not block_type:
                for each_type in self.collected_blocks.keys():
                    types[each_type] = len(self.collected_blocks[each_type])
            else:
                if block_type in self.collected_blocks:
                    types[block_type] = len(self.collected_blocks[block_type])
                else:
                    return None

        return types

    def get_defined_block_types(self):
        """
        Return a list of defined block types
        :return:
        """

        if self.block_types:
            return list(self.block_types.keys())

        return None

    def get_all_content(self):
        """
        Return all content as text to be able to serialize it
        :return:
        """

        return_content = {}

        for each_type in self.get_reference():
            return_content[each_type] = {}
            for each_content in self.get_reference(None, each_type):
                return_content[each_type][each_content] = each_content.get_content()

class Error:
    """
    A class that represents an error
    """

    def __init__(self):
        """

        """
        self.reference_id = None
        self.timestamp = None
        self.log_line = None
        self.line_number = None
        self.type = None
        self.category = None

class KnownErrors:
    """
    Object class that contain known errors
    """

    errors = {}
    configs: Configs = None


    def __init__(self):
        """

        :param config:
        """

        self.category = None
        self.name = None
        self.error_strings = None
        self.alert_type = None
        self.report_only_to = None

    @classmethod
    def get_categories(cls):
        """
        Return a list of actual loaded error categories
        :return: list of strings
        """

        return list(cls.errors.keys())

    @classmethod
    def get(cls, category=None, name=None):
        """
        Return given error
        :param category: return all errors known under given category
        :param name: return all errors with given name
        :return: a dictionary
        """

        result = {}

        if category and not name and category in KnownErrors.errors:
            return KnownErrors.errors[category]

        if not category and name:
            for each_category in KnownErrors.errors:
                for each_error in KnownErrors.errors[each_category]:
                    if each_error.name == name:
                        result[each_category][each_error.name] = each_error

        if category and name:
            if category in KnownErrors.errors and name in KnownErrors.errors[category]:
                return KnownErrors.errors[category][name]

        return None

    @classmethod
    def initialize(cls):
        """
        Initialize class to load all known errors
        :return:
        """

        for each_category in cls.configs.get_config_for('WATCH_FOR'):
            for each_error in cls.configs.get_config_for(f'WATCH_FOR.{each_category}'):
                known_error = KnownErrors()
                known_error.category = each_category
                known_error.name = each_error
                known_error.error_strings = []
                for each_regex in cls.configs.get_config_for(f'WATCH_FOR.{each_category}.{each_error}.error_strings'):
                    compiled = re.compile(each_regex)
                    known_error.error_strings.append(compiled)

                known_error.alert_type = cls.configs.get_config_for(f'WATCH_FOR.{each_category}.{each_error}.alert_types')
                known_error.report_only_to = cls.configs.get_config_for(f'WATCH_FOR.{each_category}.{each_error}.report_only_to')
                known_error.add()



    def add(self):
        """
        Add this into error list
        :return:
        """

        if self.category not in KnownErrors.errors:
            KnownErrors.errors[self.category] = {}

        KnownErrors.errors[self.category][self.name] = self

class LogAnalysis:
    """
    A class that analyse log to search for known errors
    """

    def __init__(self, file: FileManagement, config: Configs):
        """

        :param file:
        """

        self.file = file
        self.config = config
        self.found_errors = {}


    def parse(self, line, current_line):
        """
        Parsing line searching for known errors
        :param line: log line to parse
        :return:
        """
        found_errors = []
        for each_category in KnownErrors.get_categories():
            for each_error in KnownErrors.get(category=each_category):
                for rgx in KnownErrors.get(each_category,each_error).error_strings:
                    match = rgx.findall(line)
                    if match:
                        error = Error()
                        error.category = each_category
                        error.name = each_error
                        error.log_line = line
                        error.reference_id = line
                        error.line_number = current_line
                        error.timestamp = None
                        # if each_category not in found_errors:
                        #     found_errors[each_category] = {}
                        #
                        # if each_error not in found_errors[each_category]:
                        #     found_errors[each_category][each_error] = []
                        #
                        # found_errors[each_category][each_error].append(error)
                        found_errors.append(error)

        return found_errors

class TimeoutError(Exception):
    """Excepción personalizada para el timeout."""
    pass


    @staticmethod
    @contextmanager
    def Timeout(seconds):
        """
        Context manager que genera un TimeoutError si el código dentro
        tarda más de 'seconds' segundos en ejecutarse.

        Uso:
            with timeout_context(0.5):
                # Código que puede tardar
                pass
        """
        def timeout_handler(signum, frame):
            raise write_log(TimeoutError(f"La operación excedió el tiempo límite de {seconds} segundos"))

        # Establecer la señal de alarma
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))  # alarm requiere segundos enteros

        try:
            yield
        finally:
            # Cancelar la alarma y restaurar el manejador original
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def get_not_null(list_or_tuple, start=0):
    """
    Returns List of  not null object within a tuple or list
    :param list_or_tuple: list or tuple object to check
    :param start: it will indicate how this routine will start from, normally a list start in 0 but in some cases
    (like sending tuple list from re.groups() this should start in 1
    :return: int or None
    """

    # try:
    #     index = next(i for i, value in enumerate(list_or_tuple) if value is not None)
    #     return index + start
    #
    # except StopIteration:
    #     return None

    indices = [i + start for i, value in enumerate(list_or_tuple) if value is not None]
    return indices

def generate_internal_access(variable_dict, variable_to_get):
    """
    This method generates internal access to a given variable in a nested dictionary.
    :param variable_dict: The dictionary object to access.
    :param variable_to_get: Dot-separated string representing the path to the variable.
    :return: A tuple containing the access representation and the value of the variable.
    """
    if not variable_to_get:
        return None, None  # No variable to get

    keys = variable_to_get.split('.')
    current_level = variable_dict
    access_representation = []

    try:
        for key in keys:
            if key:  # Ignorar claves vacías (por ejemplo, por puntos consecutivos)
                access_representation.append(f"['{key}']")
                current_level = current_level[key]
    except KeyError:
        # Si alguna clave no existe, retornar None
        return None, None

    # Construir la representación de acceso
    access_string = ''.join(access_representation)
    return access_string, current_level

def generate_hash(stringData):
    hashstring = ""
    try:
        hashstring = hashlib.sha1(stringData.encode('utf8')).hexdigest()
    except UnicodeDecodeError as be:
        write_log("Error: %s" % be)
    return hashstring

def clear_groupnames(regex_list):
    """
    Clear given list of regex of any group name, returning same regex expression without any groupname
    This is useful to combine all the regex into a single expression to match a line, and check if within expression
    we have a possible candidate for analysis
    :param regex_list: of regex expression with group names
    :return: a list of regex expressions without any group name
    """

    return CordaObject.get_clear_group_list(regex_list)

def saving_tracing_ref_data(data, log_file):
    """
    Will save actual collected reference data to be able to load it quickly
    :param data:
    :return:
    """

    logdir = os.path.dirname(log_file)
    filename = os.path.basename(log_file)

    tracer_cache = f'{logdir}/cache'

    if not os.path.exists(tracer_cache):
        os.mkdir(tracer_cache)
    try:
        with open(f"{tracer_cache}/{filename}_references.json", 'w') as fh_references:
            json.dump(data, fh_references, indent=4)
    except IOError as io:
        write_log(f'Unable to create cache file {tracer_cache}/references.json due to: {io}')

    return

def get_log_format(line, file: FileManagement):
    """
    Will return log format found on the file
    :param line: log line to check
    :param recheck: if log_fileformat has been defined already, do not check again return previous
    :return:
    """
    if file.logfile_format:
        return file.logfile_format

    file.logfile_format = None
    check_versions = Configs.get_config(section="VERSION")
    for each_version in check_versions:
        check_format = re.search(check_versions[each_version]["EXPECT"], line)
        if check_format:
            file.logfile_format = each_version
            file.log_line_regex = re.compile(check_versions[each_version]["EXPECT"])
            break

    return file.logfile_format

def get_fields_from_log(line, log_version, file):
    """
    Will extract fields results from given log_version on given line
    :param line: Line to extract information from
    :param log_version: Version of log format to extract information
    :return: A dictionary with fields and values
    """

    result = {}

    if Configs.get_config("DETECT_LOG_VERSION_EACH_LINE"):
        # it will re-check file format for each line regardless what version has been asked to check
        file.logfile_format = get_log_format(line, recheck=True)

    # if not format has been found by default, and it has been explicitly set, will use that
    if log_version and not file.logfile_format:
        file.logfile_format = log_version

    # if there not format at all, stop process
    if not file.logfile_format:
        write_log("I'm not able to recognize log format, in this case I will not be able to pull correct information", level="ERROR")
        write_log("I was unable to find a version template for this file, please create one under VERSION->IDENTITY_FORMAT", level="ERROR")
        return None

    extract_fields = Configs.get_config_for(f"VERSION.IDENTITY_FORMAT.{file.logfile_format}")

    if not extract_fields:
        write_log("No logfile definitions to check please define at least one (at the section 'VERSION')", level="ERROR")
        return None

    fields = re.search(extract_fields["EXPECT"], line)
    if not fields:
        write_log(f"I was not able to extract any fields from line:\n{line}", level="WARN")
        write_log(f"Possible error or incomplete EXPECT for {file.logfile_format}", level="WARN")
        return None

    if fields:
        if len(fields.groups()) == len(extract_fields["FIELDS"]):
            for each_field in extract_fields["FIELDS"]:
                result[each_field] = fields.group(extract_fields["FIELDS"].index(each_field) + 1)
        else:
            write_log("Unable to parse log file properly using %s, expecting %s fields got %s fields from extraction" %
                  (file.logfile_format, len(extract_fields["FIELDS"]), len(fields.groups())), level="WARN")

    return result