from object_class import CordaObject

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
        if isinstance(element_type, CordaObject.Type):
            selement_type = element_type.value
            element_type = selement_type
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

        return parsed_names
