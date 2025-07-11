from ahocorapy.keywordtree import KeywordTree
from object_class import CordaObject, Configs, FileManagement, get_fields_from_log
from uml import UMLEntityEndPoints, UMLEntity, UMLStepSetup, UMLCommand


class TracerId:
    """
    Trace a particular corda object over all logs
    :return:
    """
    uml_definitions = None
    def __init__(self, get_configs):
        """
        class initialization getting file object which is a FileManager object...
        """
        self.Configs = get_configs
        self.file = None
        TracerId.uml_definitions = Configs.get_config(section="UML_DEFINITIONS")
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

    # def tracerx(self):
    #     """
    #     start actual id tracking
    #     :return:
    #     """
    #
    #     global log_file, logfile_format
    #     # SEL SGG 58J
    #     if logfile:
    #         log_file = logfile
    #     # Create keyword search tree
    #     kwtree = KeywordTree(case_insensitive=True)
    #     for id_ref in CordaObject.id_ref:
    #         kwtree.add(id_ref)
    #     kwtree.finalize()
    #
    #     # if not args.transaction_details:
    #     #     print('\n%s' % flow,)
    #     start = False
    #     end = False
    #     print("Phase *2* Analysing... searching references for transactions and flows")
    #
    #     if log_file:
    #         # If a file is being specified...
    #         with open(log_file, 'r') as ftrack_log:
    #             line_count = 0
    #             for each_line in ftrack_log:
    #                 line_count += 1
    #                 CordaObject.check_default_uml_references(each_line)
    #                 logfile_fields = get_fields_from_log(each_line, logfile_format)
    #
    #                 if not logfile_fields:
    #                     # print("UNABLE TO PARSE:\n%s" % each_line)
    #                     continue
    #
    #                 # Search on the tree...
    #                 results = kwtree.search_all(logfile_fields["message"])
    #                 if results:
    #                     for each_result in results:
    #                         ref_found = each_result[0]
    #                         corda_object = CordaObject.get_object(ref_found)
    #                         if corda_object:
    #                             corda_object.add_reference(line_count, logfile_fields)
    #     else:
    #         # Search on DB
    #         pass
    #
    #     lcount = 0
    #     selection = ""
    #     participant_list = None
    #     if CordaObject.uml_init:
    #         if Party.party_expected_role_list:
    #             counter = 0
    #             print("\n-----------------------------------------------------------------------------------")
    #             print("I was not able to identify following roles by myself:")
    #             for each_crole in Party.party_expected_role_list:
    #                 print(f"  * {each_crole}")
    #             role_setup = len(Party.party_expected_role_list)
    #             while role_setup>0:
    #                 participant_list = []
    #                 for each_crole in Party.party_expected_role_list:
    #                     print(f"For role of {each_crole} please can you choose it from below...\n")
    #                     counter = 0
    #                     for each_item in CordaObject.uml_init:
    #                         # if "uml_object" in each_item:
    #                         # counter += 1
    #                         #     party = each_item.replace("uml_object", "").replace('"', '').strip()
    #                         if "participant" in each_item:
    #                             counter += 1
    #                             party = clear_participant_str(each_item)
    #                             print("[%s] %s" % (counter, party))
    #                             participant_list.append(party)
    #                     counter += 1
    #                     print(f"[{counter}] - Need to define new party for this role")
    #                     print("Enter None, to do not setup this role: ")
    #                     while True:
    #                         selection = input(f"Please let me know which one is {each_crole} of this log file [1-{counter}]:")
    #                         if selection.isalpha():
    #                             if selection == 'NONE':
    #                                 role_setup -= 1
    #                                 break
    #                             print('Please select a valid number')
    #                         if selection.isdigit() and 0 < int(selection) <= len(participant_list):
    #                             break
    #                         else:
    #                             print('Please select a valid number')
    #                     if selection.isdigit():
    #                         CordaObject.set_participant_role(participant_list[int(selection)-1], role=each_crole, attach_usages=True)
    #                         role_setup -= 1
    #
    #             if int(selection) == counter:
    #                 party_roles = [
    #                     "Notary",
    #                     "Party"
    #                 ]
    #                 while True:
    #                     print("Please specify a valid x500 name for this party:")
    #                     party_name = input("> ")
    #                     if not party_name:
    #                         break
    #                     print("Please specify role for this party:")
    #                     for idx, each_role in enumerate(party_roles):
    #                         print(f"{idx} - {each_role}")
    #                     party_irole = -1
    #                     while int(party_irole) < 0 or int(party_irole) > len(party_roles):
    #                         party_irole = input("> ")
    #
    #                     party_role = party_roles[int(party_irole)]
    #
    #                     CordaObject.add_uml_object(party_name, "participant")
    #                     participant_list.append(party_name)
    #                     add_participant(party_name, party_role)
    #                     party_object = Party.get_element(party_name)
    #                     if party_object:
    #                         party_object.set_corda_role(party_role)
    #
    #                     CordaObject.set_participant_role(participant_list[int(selection) - 1],
    #                                                      role="log_owner", attach_usages=True)
    #
    #         print("Party elements found:")
    #
    #         for each_item in CordaObject.uml_init:
    #             # if "uml_object" in each_item:
    #             if "participant" in each_item:
    #                 # party = each_item.replace("uml_object", "").replace('"', '').strip()
    #                 party = clear_participant_str(each_item)
    #                 if CordaObject.get_log_owner() and party == CordaObject.get_log_owner():
    #                     cparty = Party.get_element(party)
    #                     note = cparty.get_corda_role()
    #                 else:
    #                     if party in CordaObject.default_uml_endpoints and \
    #                             "ROLE" in CordaObject.default_uml_endpoints[party]:
    #                         note = "[ %s ]" % CordaObject.default_uml_endpoints[party]["ROLE"]
    #                     else:
    #                         note = ""
    #
    #                 print(" * %s %s" % (party, note))
    #     pause = input("\n\n[PRESS ENTER TO CONTINUE]...")
    #     for each_type in CordaObject.list:
    #         for each_object in CordaObject.list[each_type]:
    #             corda_o = CordaObject.list[each_type][each_object]
    #             title = "Tracer for %s: %s" % (corda_o.type, corda_o.data["id_ref"])
    #             operations = Table(table_name=title)
    #             operations.add_header("Time Stamp", 30, "^", "^")
    #             operations.add_header("Log Line #", 10, "^", "^")
    #             #
    #             if CordaObject.additional_table_fields:
    #                 for each_field in CordaObject.additional_table_fields:
    #                     operations.add_header(each_field, 70, "^", "<")
    #             else:
    #                 # Add mere line that held reference...
    #                 operations.add_header("Reference",60,"^","<")
    #
    #             operations.add_header("UML", 10, "^", "^")
    #             for each_reference in corda_o.references:
    #                 corda_or = corda_o.references[each_reference]
    #                 operations.add_cell(corda_or["timestamp"])
    #                 operations.add_cell("%s" % (each_reference,))
    #
    #                 if CordaObject.additional_table_fields:
    #                     for each_field in CordaObject.additional_table_fields:
    #                         if each_field in corda_or:
    #                             operations.add_cell(corda_or[each_field])
    #                         else:
    #                             operations.add_cell("[*NO MATCH RULE*]: %s" % corda_or["message"])
    #                 else:
    #                     operations.add_cell(corda_or['message'])
    #
    #                 if "uml" in corda_or:
    #                     operations.add_cell(list(corda_or["uml"][0].keys())[0])
    #                 else:
    #                     operations.add_cell("*NO DATA*")
    #                 lcount += 1
    #
    #             operations.print_table_ascii()
    #             # Check if we have a default
    #             script = build_uml_script(corda_o)
    #             draw_results("%s-%s" % (corda_o.type, corda_o.data["id_ref"]), script, log_file)
    #             print("===============================")

    def tracer(self, file):
        """
        Do tracking for each flow and TX found.
        :param file:
        :return:
        """

        # TODO: Load all uml entities which will give to me what to look for
        # TODO: loop over all items in "Flows&Transactions" type


        # Load uml entities:
        uml_entity = UMLEntity()
        uml_commands = UMLCommand(self.Configs)
        uml_entity.initialize(self.Configs)

        # uml_entities_list = Configs.get_config_for('UML_ENTITY.OBJECTS')
        # entity_list = {}
        # for each_entity in uml_entities_list:
        #     uml_entity = UMLEntity(Configs)
        #     uml_entity_att_list = uml_entities_list[each_entity]
        #     for each_entity_att in uml_entity_att_list:
        #         uml_entity.set(each_entity_att, uml_entity_att_list[each_entity_att])
        #
        #     entity_list[each_entity] = uml_entity

        # Load UML objects/commands

        # Get all transactions
        flows_n_txs = self.file.get_all_unique_results('Flows&Transactions')
        # Get list of all parties involved
        parties = self.file.get_all_unique_results('Party')

        # Generate participant UML list

        if parties:
            for each_party in parties:
                print(each_party.name)
                CordaObject.add_uml_object(each_party.name, each_party.role)

        for each_item in flows_n_txs:
            pass

    @staticmethod
    def execute(each_line, current_line):
        """
        Analyse given line and determine UML step to represent it if it is found
        :param each_line: log line to analyse
        :param current_line: line number from log file
        :return:
        """

        uml_step = CordaObject.analyse(each_line,TracerId.uml_definitions)

        return uml_step


