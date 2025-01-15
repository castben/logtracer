#
# Module to extract x500 names from log files, this method also extract any alternate name
# x500 name can have; it identifies same x500 name in any order it is found. this will help to do better tracing.
#
#
import argparse
import json

from logtracer import Rules
import re

# "([OLUNCST]{1,2}=[a-zA-Z0-9- &._,=]+)"

def uml_apply_rules(original_line, rules):
    """

    :param original_line:
    :param rules:
    :return:
    """
    global participant_build

    parser = X500NameParser(rules)
    parsed_names = parser.parse_line(original_line, participant_build)

    return parsed_names

class X500Name:
    """
    This represents x500 names
    """

    def __init__(self, x500name):
        """
        This represents an actual x500 valid name
        """

        self.alternate_names = []
        self.original_string = x500name
        self.regex = re.compile(r"([CNSTLOU]{1,2}=[^\[\]^,]*)")
        self.attributes = self.extract_attributes()

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

    def compare_name(self, name_to_compare):
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

    def get_alternate_names(self):
        """
        Return all aliases found for this name
        :return:
        """

        return self.alternate_names

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

class X500NameParser:
    def __init__(self, rules):
        """
        Initialize the parser with rules for attribute validation.
        :param rules: Dictionary containing validation rules.
        """
        self.rules = rules['RULES-D']['supported-attributes']
        self.mandatory_attributes = [k for k, v in self.rules.items() if v.get('mandatory', False)]
        self.regex = re.compile(r"([CNSTLOU]{1,2}=[^\[\]^,=]*)")

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
                print(f'Invalid x500 attribute, not supported... {key}={value} ')
                print(f"There're no rules to check {key}")
                print('Unable to verify this x500 attribute')
            else:
                valid = re.search(self.rules[key]['expect'], each_match)
                if valid:
                    _,valid_value = valid.group(1).split('=')
                else:
                    print(f'Invalid x500 attribute, not supported... {key}={valid_value} ')
                    print('Unable to verify this x500 attribute')
                    print(f'Key/value do is not on expected format {key}={self.rules[key]["expect"]}')

            attributes.append((key, valid_value))


        return attributes

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
                x500name = X500Name(rname)
                if x500_list:
                    for each_xname in x500_list:
                        if each_xname.compare_name(rname):
                            each_xname.add_alternate_name(rname)
                            alternate_name_found = True

                if not alternate_name_found:
                    x500_list.append(x500name)

        # return rx500_names
        return x500_list


if __name__ == "__main__":
    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                        help='Give actual log file to pre-format')
    participant_build = []
    with open("./conf/logwatcher_rules.json") as h_rules:
        config = json.load(h_rules)
    alternate_name_found = False
    # x500_list = []
    test_list = []
    rules = config['UML_SETUP']['UML_DEFINITIONS']["participant"]
    parser = X500NameParser(rules)

    args = parserargs.parse_args()

    if args.log_file:
        # with open("/Users/larry.castro/IdeaProjects/logtracer/client-logs/ChainThat/Dev Party001 - Conflicting states Logs", "r") as h_x500:
        #"/Users/larry.castro/IdeaProjects/logtracer/client-logs/NTT Data/CS-3392/node-ascorda_Bank08425_01.2024-02-07-1.log"
        try:
            with open(args.log_file, "r") as h_x500:
                for each_line in h_x500:
                    parsed_names = parser.parse_line(each_line, test_list)

                print("Parsed X500 Names:")

                for each_name in parsed_names:
                    print(f"* {each_name.string()}")
                    if each_name.has_alternate_names():
                        for each_alternatename in each_name.get_alternate_names():
                            print(f'   Alternate Name: {each_alternatename}')

        except IOError as io:
            print(f'Unable to open {args.log_name} due to: {io}')
