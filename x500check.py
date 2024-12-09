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
#
# ("CN=ACTIONSTEP, OU=ACTIONSTEP, O=ACTIONSTEP OPERATIONS UK LIMITED, L=High Wycombe, C=GB, CN=DEZREZLEGAL,"
#              "OU=DEZREZLEGAL, O=DEZREZLEGAL LIMITED, L=Swansea, CN=Conveyancer, OU=Preproduction_node_2, "
#              "O=Coadjute Limited, L=London, CN=INSIGHTLEGAL, OU=INSIGHTLEGAL, O=INSIGHT LEGAL SOFTWARE LTD, L=Reading, "
#              "CN=PREMIUM, OU=PREMIUM, O=COADJUTE LIMITED, CN=PMPL, OU=PMPL, O=PM LAW LIMITED, L=Sheffield, CN=DezRez, "
#              "OU=Preproduction_node_1, O=DEZREZ SERVICES LIMITED, CN=Home, OU=Home1, O=CUMBRIA CAPITAL LTD, "
#              "CN=Osprey, O=PRACCTICE LIMITED, L=Malvern, CN=ASAP, OU=ASAP, "
#              "O=ASSURED SALE AND PROGRESSION LIMITED, L=Pontefract, C=GB, CN=ACTIONSTEP, OU=ACTIONSTEP, "
#              "O=ACTIONSTEP OPERATIONS UK LIMITED, L=High Wycombe, C=GB, CN=REX, OU=REX, O=REX LABS LIMITED, L=London, "
#              "CN=DEZREZLEGAL, OU=DEZREZLEGAL, O=DEZREZLEGAL LIMITED, L=Swansea, "
#              "CN=VTUK, OU=VTUK, O=VISION TEKNOLOGY UK LIMITED, L=Witney, CN=Conveyancer, OU=Preproduction_node_2, "
#              "O=Coadjute Limited, CN=INSIGHTLEGAL, OU=INSIGHTLEGAL, O=INSIGHT LEGAL SOFTWARE LTD, L=Reading, "
#              "CN=PREMIUM, OU=PREMIUM, O=COADJUTE LIMITED, CN=AVRillo, OU=Preproduction_node_1, O=Avrillo LLP,"
#              " L=Enfield, CN=PMPL, OU=PMPL, O=PM LAW LIMITED, L=Sheffield, CN=DezRez, O=DEZREZ SERVICES LIMITED, "
#              "CN=Home, OU=Home1, O=CUMBRIA CAPITAL LTD, CN=Osprey, O=PRACCTICE LIMITED, L=Malvern, CN=ASAP, OU=ASAP, "
#              "O=ASSURED SALE AND PROGRESSION LIMITED, L=Pontefract, C=GB")

# "([OLUNCST]{1,2}=[a-zA-Z0-9- &._,=]+)"

def openAIX500():
    import re
    list_entities = []
    # String proporcionado
    x500_string = "CN=ACTIONSTEP, OU=ACTIONSTEP, O=ACTIONSTEP OPERATIONS UK LIMITED, L=High Wycombe, C=GB, CN=DEZREZLEGAL, OU=DEZREZLEGAL, O=DEZREZLEGAL LIMITED, L=Swansea, CN=Conveyancer, OU=Preproduction_node_2, O=Coadjute Limited, L=London, CN=INSIGHTLEGAL, OU=INSIGHTLEGAL, O=INSIGHT LEGAL SOFTWARE LTD, L=Reading, CN=PREMIUM, OU=PREMIUM, O=COADJUTE LIMITED, CN=PMPL, OU=PMPL, O=PM LAW LIMITED, L=Sheffield, CN=DezRez, OU=Preproduction_node_1, O=DEZREZ SERVICES LIMITED, CN=Home, OU=Home1, O=CUMBRIA CAPITAL LTD, CN=Osprey, O=PRACCTICE LIMITED, L=Malvern, CN=ASAP, OU=ASAP, O=ASSURED SALE AND PROGRESSION LIMITED, L=Pontefract, C=GB"

    x500_patterns = [
        r'(?:CN=[^,]+, )?OU=[^,]+, O=[^,]+, L=[^,]+, C=[^,]{2}',
        r'OU=[^,]+,(?:CN=[^,]+, )?O=[^,]+, L=[^,]+, C=[^,]{2}'
    ]

    for each_record in list_x500:
        x500_string = each_record
        # Expresión regular para encontrar cada entidad X500
        for each_pattern in x500_patterns:

            # pattern = r'(?:CN=[^,]+, )?OU=[^,]+, O=[^,]+, L=[^,]+, C=[^,]{2}'

            # Buscar todas las coincidencias en el string
            matches = re.findall(each_pattern, x500_string)

            # Imprimir cada entidad encontrada
            if matches:
                for match in matches:
                    # print(match)
                    if match not in list_entities:
                        list_entities.append(match)

    for each in list_entities:
        print(each)

def x5001():

    Rules.load()
    participant_build = []
    rules = {'C': '1:=:M', 'CN': '1:=:O', 'L': '1:=:M', 'O': '1:=:M', 'OU': '1:=:O', 'S': '1:=:O', 'ST': '1:=:O'}
    participant_build_counter = 0
    x500_key_count = {}
    x500_build = ""
    rules_details = {}
    force_x500_split = False
    # This will read rules, and expand them to more detailed object
    for each_rule in rules:
        rl = re.search(r"(\d+):([=>]):([OM])", rules[each_rule])
        if not rl:
            print("Warning malformed rule for %s key found at configuration file" % each_rule)
            continue

        rules_details[each_rule] = {
            "occurrences": int(rl.group(1)),
            "operator": rl.group(2),
            "type": rl.group(3)
        }

    #
    # Split the x500 name in sections, using ","
    # then apply rule to each section.
    #

    allowed_keys = "".join(sorted(sorted(set("".join(rules.keys())))))
    allowed_keys_list = list(rules.keys())
    # search for proper formed x500 keys on given string...
    # following line will extract all keys from given string
    x500_keys = re.findall('([%s]{1,2}=[^\n",]*)' % allowed_keys, uml_object)
    number_of_keys = len(x500_keys)
    x500_key_counter = 0
    for each_x500_key in x500_keys:
        x500_key_counter += 1

        # Extract proper key, and it's value; will use re.search to manage re groups
        #
        x500_key_check = re.search('([%s]{1,2})=([^\n,"]*)' % allowed_keys, each_x500_key)

        # count how many times given key appears

        if x500_key_check.group(1) not in x500_key_count:
            x500_key_count[x500_key_check.group(1)] = 1
        else:
            x500_key_count[x500_key_check.group(1)] += 1

        # Check if given key it is found at the rules.
        #
        if x500_key_check.group(1) not in rules:
            print("Warning, %s x500 keyword not fully supported on corda's x500 names" % x500_key_check.group(0))
            print("There's no proper rule to manage it, will be added anyway and ignored...")
            x500_key_check += x500_key_check.group(0) + ","
            participant_build[participant_build_counter] += x500_key_check.group(0) + ","
        else:
            # Check if x500 name is complete:
            mandatory_key = False
            force_x500_split = False
            for each_key in allowed_keys_list:
                if ":M" in rules[each_key]:
                    mandatory_key = True
                    # if I found at least 1 mandatory rule, break
                    break
            # Check if actual key break actual amount of keys allowed on a single x500 name

            if rules_details[x500_key_check.group(1)]["operator"] == "=":
                if x500_key_count[x500_key_check.group(1)] > rules_details[x500_key_check.group(1)]["occurrences"]:
                    # print("Warning Found a merged x500 name:\n %s\nattempting to split it" % uml_object)
                    force_x500_split = True
                else:
                    force_x500_split = False

            # if:
            # There no more keys on allowed_keys_ist  - or -
            # Given key is not mandatory (it may be do not appear on expected keys) - or -
            # we are checking last key from x500 name - or -
            # any field key is seeing more times that allowed by the rule
            # if x500_key_count[x500_key_check.group(1)] > rules
            #

            if force_x500_split:
                # Remove last "," from this participant build:
                x500_build = x500_build.strip(", ")
                # Store this name
                if x500_build not in participant_build:
                    if not allowed_keys_list and not mandatory_key:
                        print(f"  X500 name: {x500_build} [Re-Build from split]")
                        participant_build.append(x500_build)
                x500_build = x500_build + ", %s, " % x500_key_check.group(0)
                # Reset rule key count for all to start from this x500 name (previous name was already stored)
                for each_rd in x500_key_count:
                    x500_key_count[each_rd] = 0

                # Update to 1 only actual processed key
                x500_key_count[x500_key_check.group(1)] = 1
                # Reset required fields again for the next name
                allowed_keys_list = list(rules.keys())
                # Remove recently added field at x500_build from allowed_keys_list
                allowed_keys_list.remove(x500_key_check.group(1))

            if len(x500_keys) - x500_key_counter == 0:
                # X500 name seems to be complete; store it
                x500_build += "%s, " % x500_key_check.group(0)
                # Remove last "," from this participant build:
                x500_build = x500_build.strip(", ")
                # Store this name
                if x500_build not in participant_build:
                    print(f" * X500 name: {x500_build}")
                    participant_build.append(x500_build)

                # Remove current keyword from expected list
                if x500_key_check.group(1) in allowed_keys_list:
                    allowed_keys_list.remove(x500_key_check.group(1))
                # if actual keyword is "S" or "ST remove it
                if x500_key_check.group(1) == "ST":
                    allowed_keys_list.remove("S")
                if x500_key_check.group(1) == "S":
                    allowed_keys_list.remove("ST")
                break

            if ((not allowed_keys_list or not mandatory_key) and not force_x500_split and
                len(x500_keys) - x500_key_counter) != 0:
                # X500 name seems to be complete; store it
                # Remove last "," from this participant build:
                x500_build = x500_build.strip(", ")
                # Reset required fields again for the next name
                allowed_keys_list = list(rules.keys())
                # Store this name
                if x500_build not in participant_build:
                    print(f"  X500 name: {x500_build}")
                    participant_build.append(x500_build)
                # Clear build variable for next name
                x500_build = ""
            else:
                try:

                    if x500_key_check.group(0) not in x500_build:
                        # If x500 key is not in the actual x500 name add it...
                        x500_build += "%s, " % x500_key_check.group(0)
                        # x500_key_check += x500_key_check.group(0) + ","
                        # participant_build[participant_build_counter] += "%s, " % x500_key_check.group(0)

                        # Remove current keyword from expected list
                        if x500_key_check.group(1) in allowed_keys_list:
                            allowed_keys_list.remove(x500_key_check.group(1))
                        # if actual keyword is "S" or "ST remove it
                        if x500_key_check.group(1) == "ST":
                            allowed_keys_list.remove("S")
                        if x500_key_check.group(1) == "S":
                            allowed_keys_list.remove("ST")

                except BaseException as be:
                    print(be)

    # Check if any mandatory field is missing
    if allowed_keys_list:
        for each_rule_key in allowed_keys_list:
            # check if this field is mandatory:
            if ":M" in rules[each_rule_key]:
                print("WARNING: this participant name '%s' is missing a mandatory key: %s" % (uml_object,
                                                                                              each_rule_key))


def x500test(line):
    """

    :param line:
    :return:
    """
    x500_pattern = r"(?:(C=[^,]+|L=[^,]+|O=[^,]+|OU=[^,\"]+),?\s?)+"
    # Buscar todas las coincidencias válidas
    matches = re.finditer(x500_pattern, line)

    # Filtrar resultados para eliminar cadenas irrelevantes
    x500_names = []
    for match in matches:
        x500_candidate = match.group().strip(", ")
        # Validar que el candidato tenga al menos dos atributos típicos de un X.500 name
        if len(re.findall(r"(C=[^,]+|L=[^,]+|O=[^,]+|OU=[^,]+)", x500_candidate)) >= 2:
            x500_names.append(x500_candidate)

    # Mostrar resultados
    for i, name in enumerate(x500_names, start=1):
        print(f"X.500 Name {i}: {name}")

def uml_apply_rules(original_line, rules):
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
        x500_keys = re.findall(r"([%s]{1,2}=[^\n\!\@\#\$\^\*\(\)~\?\>\<\&\/\\\,\.\",]*)" % allowed_keys, uml_object)

        # Check if given line has a potential x500 name to be verified
        if not x500_keys:
            return None

        number_of_keys = len(x500_keys)
        x500_key_counter = 0
        # Incoming line is not cleaned up, it will have x500 name within, so I will split line using as
        # delimiter "," and re-build names...

        line_separated = uml_object.split(',')
        token_count = len(line_separated)
        token = 0
        for each_item in line_separated:
            token += 1
            for each_x500_key in allowed_keys_list:
                # Extract proper key, and it's value; will use re.search to manage re groups
                #
                x500_key_check = re.search(f"{rules_details[each_x500_key]['expect']}", each_item)

                if not x500_key_check:
                    # This attribute do not exist here
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

                # count how many times given key appears

                if each_x500_key not in x500_key_count:
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
                    if check_has_all_mandatory_attributes(x500_build):
                        if x500_build not in participant_build:
                            print(f"  X500 name: {x500_build} [Re-Build from split]")
                            participant_build.append(x500_build)

                    x500_build = "%s, " % x500_key_check.group(0)
                    # Reset rule key count for all to start from this x500 name (previous name was already stored)
                    for each_rd in x500_key_count:
                        x500_key_count[each_rd] = 0

                    # Update to 1 only actual processed key
                    x500_key_count[each_x500_key] = 1
                    # Reset required fields again for the next name
                    allowed_keys_list = list(rules_details.keys())

                try:

                    if x500_key_check.group(0) not in x500_build:
                        # If x500 key is not in the actual x500 name add it...
                        x500_build += "%s, " % x500_key_check.group(0)


                except BaseException as be:
                    print(be)

    return participant_build


if __name__ == "__main__":
    participant_build = []
    with open("./conf/logwatcher_rules.json") as h_rules:
        config = json.load(h_rules)

    rules = config['UML_SETUP']['UML_DEFINITIONS']["participant"]

    with open("/home/larry/IdeaProjects/logtracer/client-logs/Finteum/CS-3462/notary-issue/node-bull-759dc59895-j7rmw.log", "r") as h_x500:
        for each_line in h_x500:
            uml_apply_rules(each_line, rules)
            #x500test(each_line)



# openAIX500()