#
#
import json

from logtracer import Rules
import re


list_x500 = [
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB))",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB for transaction :: C05C3689307BCE6CFAF307E49408EA5354AE13ECEF875E2FAF245153FB207CBA to observers :: [CN=ACTIONSTEP",
    "CN=DEZREZLEGAL, OU=DEZREZLEGAL, O=DEZREZLEGAL LIMITED, L=Swansea, C=GB",
    "CN=Conveyancer, OU=Preproduction_node_2, O=Coadjute Limited, L=London, C=GB",
    "CN=INSIGHTLEGAL, OU=INSIGHTLEGAL, O=INSIGHT LEGAL SOFTWARE LTD, L=Reading, C=GB",
    "CN=PREMIUM, OU=PREMIUM, O=COADJUTE LIMITED, L=London, C=GB",
    "CN=PMPL, OU=PMPL, O=PM LAW LIMITED, L=Sheffield, C=GB",
    "CN=DezRez, OU=Preproduction_node_1, O=DEZREZ SERVICES LIMITED, L=Swansea, C=GB",
    "CN=Home, OU=Home1, O=CUMBRIA CAPITAL LTD, L=London, C=GB",
    "CN=Osprey, OU=Preproduction_node_1, O=PRACCTICE LIMITED, L=Malvern, C=GB",
    "CN=ASAP, OU=ASAP, O=ASSURED SALE AND PROGRESSION LIMITED, L=Pontefract, C=GB]] <no value> {",
    "CN=ASAP, OU=ASAP, O=ASSURED SALE AND PROGRESSION LIMITED, L=Pontefract, C=GB]] <no value> {, CN=LEVI, CN=LEVI",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB for transaction :: 1DA3D0E2180B3EAE6B6E556E4D92970472CA01161FF4E017C527CF89EA26A461 to observers :: [CN=ACTIONSTEP",
    "CN=REX, OU=REX, O=REX LABS LIMITED, L=London, C=GB",
    "CN=VTUK, OU=VTUK, O=VISION TEKNOLOGY UK LIMITED, L=Witney, C=GB",
    "CN=AVRillo, OU=Preproduction_node_1, O=Avrillo LLP, L=Enfield, C=GB",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB filename=null <no value> {",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB for transaction :: 19EA406811E202496B0B2ED2835AC29783F00D299E7112C3EC470DFA4D7CFADB to observers :: [CN=ACTIONSTEP",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB. <no value> {",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB])] <no value> {",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB)",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB filename=null <no value> {, CN=ReapIT, CN=ReapIT",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB filename=null <no value> {, CN=LEVI, CN=LEVI",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB])] <no value> {, CN=LEVI, CN=LEVI",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB. <no value> {, CN=ReapIT, CN=ReapIT",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB] Received tx from [CN=ReapIT",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB. <no value> {, CN=LEVI, CN=LEVI",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB for transaction :: 6864EECFDDE711AFC1B1A566E49BFD8E89F3DFEDD3FE2DEDE6D8D97E67A9CE4C to observers :: [CN=ACTIONSTEP",
    "CN=TALBOTS LAW, OU=TALBOTS LAW, O=TALBOTS LAW LTD, L=Stourbridge, C=GB",
    "OU=TALBOTS LAW, O=TALBOTS LAW LTD, L=Stourbridge, C=GB",
    "CN=EstateAgent, OU=Preproduction_node_1, O=Coadjute Limited, L=London, C=GB",
    "CN=MAB, OU=MAB, O=MORTGAGE ADVICE BUREAU LIMITED, L=Derby, C=GB",
    "CN=TAYLOR ROSE MW, OU=TAYLOR ROSE MW, O=TAYLOR ROSE TTKW LIMITED, L=London, C=GB",
    "CN=Redbrick, OU=Preproduction_node_1, O=Redbrick Solutions (UK) Limited, L=Oakham, C=GB",
    "CN=VAULTEA, OU=VAULTEA, O=CLIENTVAULT UK PTY LTD, L=Surrey, C=GB]] <no value> {",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB for transaction :: 22442D0947350E2E228BC93E51C291A6D876959989446D9D916383F3AE6FDDEF to observers :: [CN=ReapIT",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB found exact employee match for email coadjute@levisolicitors.co.uk] <no value> {",
    "CN=Coadjute, OU=Preproduction_notary, O=Coadjute Limited, L=London, C=GB). <no value> {",
    "CN=Coadjute, OU=Preproduction_notary, O=Coadjute Limited, L=London, C=GB. <no value> {",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB]]",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB]]}] <no value> {, CN=ReapIT, CN=ReapIT",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB synchronising employee coadjute@levisolicitors.co.uk with state EmployeeState(invitedBy=",
    "CN=CompaniesHouse, OU=CompaniesHouse, O=Companies House, L=Cardiff, C=GB] <no value> {",
    "CN=Coadjute, OU=Preproduction_notary, O=Coadjute Limited, L=London, C=GB. <no value> {, CN=ReapIT, CN=ReapIT",
    "CN=CompaniesHouse, OU=CompaniesHouse, O=Companies House, L=Cardiff, C=GB]]] <no value> {, CN=LEVI, CN=LEVI",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB for transaction :: C018B60C731744FA6F1D3219BD0FB046CA3D5F6FCFE628C5B4DE2BE69156176A to observers :: [CN=ReapIT",
    "CN=ACTIONSTEP, OU=ACTIONSTEP, O=ACTIONSTEP OPERATIONS UK LIMITED, L=High Wycombe, C=GB",
    "CN=CompaniesHouse, OU=CompaniesHouse, O=Companies House, L=Cardiff, C=GB]]}] <no value> {",
    "OU=CompaniesHouse, CN=CompaniesHouse, O=Companies House, L=Cardiff, C=GB]]}] <no value> {",
    "CN=CompaniesHouse, OU=CompaniesHouse, O=Companies House, L=Cardiff, C=GB]]}] <no value> {, CN=ReapIT, CN=ReapIT",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB] [state=OrgUnitState]] <no value> {",
    "CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB synchronising org unit cf424123-5d2e-4725-af6d-baaf761aa9a5] <no value> {, CN=LEVI, CN=LEVI",
    "CN=LEVI, OU=LEVI, O=LEVI SOLICITORS LLP, L=Leeds, C=GB for transaction :: DAEF7878DD876EC4F1A4229870B2A6E6CF3547C1D50945DAD3F9678FC4FE7282 to observers :: [CN=ACTIONSTEP",
    "CN=VAULTEA, OU=VAULTEA, O=CLIENTVAULT UK PTY LTD, L=Surrey, C=GB]] <no value> {, CN=LEVI, CN=LEVI"
]

uml_object = "CN=ACTIONSTEP, OU=ACTIONSTEP, O=ACTIONSTEP OPERATIONS UK LIMITED, L=High Wycombe, C=GB, CN=ReapIT, OU=Preproduction_node_1, O=Reapit limited, L=London, C=GB, CN=TALBOTS LAW, OU=TALBOTS LAW, O=TALBOTS LAW LTD, L=Stourbridge, C=GB, CN=REX, OU=REX, O=REX LABS LIMITED, L=London, C=GB, CN=DEZREZLEGAL, OU=DEZREZLEGAL, O=DEZREZLEGAL LIMITED, L=Swansea, C=GB, CN=EstateAgent, OU=Preproduction_node_1, O=Coadjute Limited, L=London, C=GB, CN=VTUK, OU=VTUK, O=VISION TEKNOLOGY UK LIMITED, L=Witney, C=GB, CN=Conveyancer, OU=Preproduction_node_2, O=Coadjute Limited, L=London, C=GB, CN=INSIGHTLEGAL, OU=INSIGHTLEGAL, O=INSIGHT LEGAL SOFTWARE LTD, L=Reading, C=GB, CN=PREMIUM, OU=PREMIUM, O=COADJUTE LIMITED, L=London, C=GB, CN=MAB, OU=MAB, O=MORTGAGE ADVICE BUREAU LIMITED, L=Derby, C=GB, CN=AVRillo, OU=Preproduction_node_1, O=Avrillo LLP, L=Enfield, C=GB, CN=PMPL, OU=PMPL, O=PM LAW LIMITED, L=Sheffield, C=GB, CN=DezRez, OU=Preproduction_node_1, O=DEZREZ SERVICES LIMITED, L=Swansea, C=GB, CN=Home, OU=Home1, O=CUMBRIA CAPITAL LTD, L=London, C=GB, CN=Osprey, OU=Preproduction_node_1, O=PRACCTICE LIMITED, L=Malvern, C=GB, CN=ASAP, OU=ASAP, O=ASSURED SALE AND PROGRESSION LIMITED, L=Pontefract, C=GB, CN=TAYLOR ROSE MW, OU=TAYLOR ROSE MW, O=TAYLOR ROSE TTKW LIMITED, L=London, C=GB, CN=Redbrick, OU=Preproduction_node_1, O=Redbrick Solutions"

# "([OLUNCST]{1,2}=[a-zA-Z0-9- &._,=]+)"


def uml_apply_rulesx(original_line, rules):
    """
    Apply given rule to this object, this method will only respect x500 names that are 100% compatible
    with corda platform. Please refer to rules to check this out
    :return:
    """
    global participant_build
    participant_build_counter = 0
    line_to_process = []
    x500_key_count = {}
    x500_build = ""
    rules_details = rules['RULES-D']['supported-attributes']
    force_x500_split = False
    occurrences_count = 0
    occurrences_operator = ''
    def check_has_all_mandatory_attributes(x500name):
        """
        Check if given x500 name has all mandatory attributes to be a standalone x500 name...
        TODO: This method raise an issue, if there're optional attributes like 'OU', 'S', 'ST' they will be ignored!
        TODO: need to fix this!
        :param x500name:
        :return:
        """

        for each_mandatory in list(rules_details.keys()):
            if rules_details[each_mandatory]['mandatory']:
                if not f'{each_mandatory}=' in x500name:
                    return False

        return True

    # Check if there's handling for special cases:
    # if we hit such case I will split this into two lines so I can pick up correct tokens
    #
    if 'special-cases' in rules['RULES-D']:
        for each_case in rules['RULES-D']['special-cases']:
            expect = rules['RULES-D']['special-cases'][each_case]['expect']
            case_result = re.search(expect, original_line)

            if case_result:
                for each_group in case_result.groups():
                    line_to_process.append(each_group)

    if original_line and not line_to_process:
        line_to_process.append(original_line)

    for uml_object in line_to_process:

        #
        # Split the x500 name in sections, using ","
        # then apply rule to each section.
        #
        # now will check every item against rules and build x500 name.

        allowed_keys = "".join(sorted(sorted(set("".join(rules_details.keys())))))
        allowed_keys_list = list(rules_details.keys())
        # search for proper formed x500 keys on given string...
        # following line will extract all keys from given string

        x500_keys = re.findall(r"([%s]{1,2}=[^=\n\!\@\#\$\^\*\(\)~\?\>\<\&\/\\\,\.\",]*)" % allowed_keys, uml_object)

        # Check if given line has a potential x500 name to be verified
        if not x500_keys:
            return None

        x500_key_counter = 0
        # Incoming line is not cleaned up, it will have x500 name within, so I will split line using as
        # delimiter "," and re-build names...

        line_separated = uml_object.split(',')
        token_count = len(x500_keys)
        token = 0
        for each_item in x500_keys:
            token += 1
            each_x500_key, attribute_value = each_item.split('=')
            if each_x500_key in allowed_keys_list:
                # Apply corresponding attribute rule
                check_attribute = re.search(rules_details[each_x500_key]['expect'], each_item)

                # Interpret how many occurrences are allowed to this specific attribute
                if not check_attribute:
                    print(f"Unable to parse {each_item} into x500 attribute")
                    continue
                #
                # Interpret how many occurrences are allowed to this specific attribute
                if not 'occurrences' in rules_details[each_x500_key]:
                    occurrences_count = 1
                    occurrences_operator = '='
                else:
                    occurrences = re.search(r'([<>]?)(\d+)', rules_details[each_x500_key]['occurrences'])

                    if occurrences:
                        if not occurrences.group(1):
                            occurrences_operator = '='
                        else:
                            occurrences_operator = occurrences.group(1)

                        if not occurrences.group(2):
                            occurrences_count = 1
                        else:
                            occurrences_count = int(occurrences.group(2))

                # count how many times given attribute appears

                if each_x500_key not in x500_key_count:
                    x500_build += "%s, " % check_attribute.group(1)
                    x500_key_count[each_x500_key] = 1
                else:
                    x500_key_count[each_x500_key] += 1
                    x500_key_counter += 1

                # Check how many occurrences are at the moment for this attribute

                if occurrences_operator == '>':
                    if x500_key_count[each_x500_key] > occurrences_count:
                        pass
                else:
                    if occurrences_operator == '=':
                        if x500_key_count[each_x500_key] > occurrences_count:
                            # this means actual number of attributes are more than expected, which probably because
                            # there's more than 1 x500 name on same line
                            force_x500_split = True

                if force_x500_split:
                    # Remove last "," from this participant build:
                    x500_build = x500_build.strip(", ")
                    # Store this name, first let's check if
                    # if check_has_all_mandatory_attributes(x500_build):
                    if x500_build not in participant_build and check_has_all_mandatory_attributes(x500_build):
                        print(uml_object)
                        print(f"  X500 name: {x500_build} [Re-Build from split]")
                        print('-'*200)

                    # if check_has_all_mandatory_attributes(x500_build):
                    participant_build.append(x500_build)
                    # else:
                    #     x500_build += "%s, " % check_attribute.group(1)
                    #     continue

                    x500_build = "%s, " % check_attribute.group(1)
                    # Reset rule key count for all to start from this x500 name (previous name was already stored)
                    for each_rd in x500_key_count:
                        x500_key_count[each_rd] = 0

                    # Update to 1 only actual processed key
                    x500_key_count[each_x500_key] = 1
                    # Reset required fields again for the next name
                    allowed_keys_list = list(rules_details.keys())

                try:

                    if check_attribute.group(1) not in x500_build:
                        # If x500 key is not in the actual x500 name add it...
                        x500_build += "%s, " % check_attribute.group(1)


                except BaseException as be:
                    print(be)

    return participant_build


def uml_apply_rules(original_line, rules):
    """

    :param original_line:
    :param rules:
    :return:
    """
    global participant_build

    parser = X500NameParser(rules)
    parsed_names = parser.parse_line(each_line, participant_build)

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

        # attributes = [match.split('=') for match in matches]
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

    # def xparse_line(self, line):
    #     """
    #     Parse a line to extract and validate X500 names.
    #     :param line: String containing potential X500 names.
    #     :return: List of valid X500 names.
    #     """
    #     attributes = self.extract_attributes(line)
    #     x500_names = []
    #     current_name = []
    #
    #     for key, value in attributes:
    #         if any(key == k for k, _ in current_name):
    #             # Duplicate key means we likely have a new X500 name
    #             if self.validate_x500_name(current_name):
    #                 x500_names.append(current_name)
    #             current_name = []
    #
    #         current_name.append((key, value))
    #
    #     # Add the last X500 name if valid
    #     if self.validate_x500_name(current_name):
    #         x500_names.append(current_name)
    #
    #     # Rebuild names into canonical string format
    #     return [', '.join(f"{k}={v}" for k, v in name) for name in x500_names]

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
    participant_build = []
    with open("./conf/logwatcher_rules.json") as h_rules:
        config = json.load(h_rules)
    alternate_name_found = False
    # x500_list = []
    test_list = []
    rules = config['UML_SETUP']['UML_DEFINITIONS']["participant"]
    parser = X500NameParser(rules)

    # with open("/Users/larry.castro/IdeaProjects/logtracer/client-logs/ChainThat/Dev Party001 - Conflicting states Logs", "r") as h_x500:
    with open("/Users/larry.castro/IdeaProjects/logtracer/client-logs/NTT Data/CS-3392/node-ascorda_Bank08425_01.2024-02-07-1.log", "r") as h_x500:
        for each_line in h_x500:
            parsed_names = parser.parse_line(each_line, test_list)

    print("Parsed X500 Names:")

    for each_name in parsed_names:
        print(f"* {each_name.string()}")
        if each_name.has_alternate_names():
            for each_alternatename in each_name.get_alternate_names():
                print(f'   Alternate Name: {each_alternatename}')
