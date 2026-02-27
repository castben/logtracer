from object_class import LogAnalysis, CordaObject


class ErrorAnalysis:
    def __init__(self, get_configs):
        self.Configs = get_configs
        self.collected_errors = None
        self.file = None
        self.type = None
        self.log_analysis = None
        self.category_list = {}

    def set_file(self, file):
        """
        
        :param file: 
        :return: 
        """
        self.file = file
        self.log_analysis = LogAnalysis(file, self.Configs)
        
        
    def clear(self):
        """
        Delete all collected party information
        :return:
        """

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


    def execute(self, each_line, current_line=None):
        """
        Process that need to be executed in parallel
        :param each_line: line from log file
        :return: a list x500 name found
        """

        return  self.log_analysis.parse(each_line, current_line)


    def get_all_content(self):
        """
        Return all content as text to be able to serialize it
        :return:
        """

        if not self.category_list:
            self._classify_errors()

        return_content = {}

        for each_category in self.category_list:
            if each_category not in return_content:
                return_content[each_category] = {}
            for error_type in self.category_list[each_category]:
                if error_type not in return_content[each_category]:
                    return_content[each_category][error_type] = []
                for each_error in self.category_list[each_category][error_type]:
                    error = {
                        "line_number": each_error.line_number,
                        "log_line": each_error.log_line,
                        "timestamp": each_error.timestamp,
                        "level": each_error.level,
                        "type": each_error.type
                    }
                    return_content[each_category][error_type].append(error)

        return return_content

    def _classify_errors(self):
        """
        Will interact through all errors found and will classify them by category.
        :return:
        """

        for each_error in self.collected_errors:
            if each_error.category not in self.category_list:
                self.category_list[each_error.category] = {}
            if each_error.type not in self.category_list[each_error.category]:
                self.category_list[each_error.category][each_error.type] = []

            self.category_list[each_error.category][each_error.type].append(each_error)

        return  self.category_list

    def get_error_category(self, category=None):
        """
        Return a dictionary of errors
        :return:
        """

        if not self.category_list:
            self._classify_errors()

        if category:
            if category in self.category_list:
                return self.category_list[category]
            else:
                return None

        return self.category_list

    def get_error_summary(self):
        """
        Return a dictionary with all summary for all errors by category
        :return:
        """

        return_list = {}

        if not self.category_list:
            self._classify_errors()

        for each_category in self.category_list:
            if each_category not in return_list:
                return_list[each_category] = {}
            for each_error_type in self.category_list[each_category]:
                return_list[each_category][each_error_type] = len(self.category_list[each_category][each_error_type])


        return return_list




