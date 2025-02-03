from object_class import CordaObject, get_fields_from_log, FileManagement
from object_class import RegexLib

import re

class GetParties:
    def __init__(self, get_configs):
        self.Configs = get_configs
        self.file = None
        self.x500list = []
        self.type = None

    def get_element_type(self):
        """
        Return element type for this item; element type could be "Party" which represents party element, or
        'Flows&Transactions' which represents all tx and flows found.
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

    def execute(self, each_line, current_line=None):
        """
        Process that need to be executed in parallel
        :param each_line: line from log file
        :return: a list x500 name found
        """

        # self.get_ref_ids(each_line)

        parsed_names = self.file.parser.parse_line(each_line, self.x500list)

        # for each_name in parsed_names:
        #     each_name.identify_party_role(each_line)
        # self.file.identify_party_role(each_line)

        return parsed_names
