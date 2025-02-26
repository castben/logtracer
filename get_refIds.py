import object_class
from object_class import CordaObject, get_fields_from_log, FileManagement
from object_class import RegexLib

import re

class GetRefIds:
    def __init__(self, get_configs):
        self.Configs = get_configs
        self.file = None
        self.x500list = []
        self.type = None

    def get_element_type(self):
        """
        Return element type for this item; element type could be "Party" which represents party element, or
        'Flows&Txns' which represents all tx and flows found.
        """
        return self.type

    def set_element_type(self, element_type):
        """
        Set actual type of element being processed
        :return: None
        """
        self.type = element_type

    def set_file(self, file):
        """
        Setting actual file to work with
        :param file: a FileManager object type
        :return:
        """
        self.file = file

    def get_ref_ids(self,each_line, current_line):
        """
        Search for all identifiable ids on a log, it also will keep a record of current line number
        where this id was found.

        :return:
        """

        corda_objects = self.Configs.get_config(section='CORDA_OBJECTS')
        corda_object_detection = None
        # Complete list of corda object regex definition
        all_regex = []
        # A helper list to give the type and avoid to do a second search on the config to gather object type
        all_regex_type = []
        if not corda_objects:
            print("No definition for corda objects found, please setup CORDA_OBJECT section on config")
            exit(0)
        else:
            # Collect from "CORDA_OBJECTS" all object definitions:
            corda_objects = self.Configs.get_config(section="CORDA_OBJECTS")

            for each_type in corda_objects:
                if "EXPECT" in self.Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]:
                    regex_list = self.Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]["EXPECT"]
                    for each_rgx in regex_list:
                        # Before adding it into list, will replace any macrovariable within (like __txid__ or __participant__ etc...)
                        all_regex.append(RegexLib.build_regex(each_rgx, nogroup_name=True))
                        all_regex_type.append(each_type)

            # Prepare full regex for quick detection (combine all "forms" of references ID's defined)
            corda_object_detection = "|".join(all_regex)

        try:
            co = None
            # This will try to match given line with all possible patterns for required ID's these patterns came
            # from definition file at CORDA_OBJECT in there you will see all definitions program is looking for to
            # identify a CORDA_OBJECT

            cordaobject_id_match = re.finditer(corda_object_detection, each_line)

            if cordaobject_id_match:
                group_count = 0
                co = None
                for matchNum, match in enumerate(cordaobject_id_match, start=1):
                    # for groupNum in range(0, len(match.groups())):
                    # groupNum = groupNum + 1
                    groupNum = object_class.get_first_not_null(match.groups(), start=1)
                    each_group = match.group(groupNum)
                    if each_group:
                        if each_group in CordaObject.id_ref:
                            # Store this  line involving current reference
                            cob = CordaObject.get_object(each_group)
                            cob.add_data('references', current_line)
                            continue #org_cordaobject = CordaObject
                        else:
                            # print("id {group} identified as {type}".format(
                            #     group=match.group(groupNum),
                            #     type=all_regex_type[groupNum-1]
                            # ))

                            # Add a new reference found into the list
                            CordaObject.id_ref.append(each_group)
                            #
                            # Also create this object to be identified later:
                            # first extract line features (timestamp, severity, etc)
                            log_line_fields = get_fields_from_log(each_line, self.file.logfile_format, self.file)
                            # Create object:
                            co = CordaObject()
                            # TODO: Hay un bug que ocurre cuando el programa detecta un corda_object que esta
                            #  en una linea que esta fuera (tiene retorno de carro) de la linea principal del
                            #  log lo que provoca que el objeto no sea creado... por los momentos voy a
                            #  ignorar estas referencias...
                            if log_line_fields:
                                if not 'error_level' in log_line_fields:
                                    log_line_fields['error_level'] = 'INFO'
                                # Create object
                                co.add_data("id_ref", each_group)
                                co.add_data("Original line", each_line)
                                co.add_data("error_level", log_line_fields["error_level"])
                                co.add_data("timestamp", log_line_fields["timestamp"])
                                co.add_data("type", all_regex_type[groupNum-1])
                                co.add_data("line_number", current_line)
                                co.set_type(all_regex_type[groupNum-1])
                                co.add_object()

            if not self.file.logfile_format:
                print("Sorry I can't find a proper log template to parse this log terminating program")
                exit(0)
            if co:
                return co
            else:
                return None

        except IOError as io:
            print('Sorry unable to open %s due to %s' % (self.file.logfile_format, io))
        except BaseException as be:
            print(f'Sorry unable to process, due to {be}')


    def execute(self, each_line, current_line):
        """
        Process that need to be executed in parallel
        :param each_line: line from log file
        :param current_line: line from log file
        :return: a list x500 name found
        """

        # self.get_ref_ids(each_line)
        parsed_objects = self.get_ref_ids(each_line, current_line)

        return parsed_objects

    @staticmethod
    def classify_results(results):
        """
        From result, classify each object found
        :return:
        """
        classified_results = {}
        for each_item in results:
            if each_item.type not in classified_results:
                classified_results[each_item.type] = {}

            classified_results[each_item.type][each_item.reference_id] = each_item

        return classified_results
