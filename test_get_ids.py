#!./system/bin/python
import cProfile
# Program to test extraction and validation of X500 names.

import os
import argparse
from get_refIds import GetRefIds
from object_class import Configs, X500NameParser, FileManagement
from object_class import CordaObject,saving_tracing_ref_data
# from tracer_id import TracerId
from get_parties import GetParties
from uml import UMLEntityEndPoints, UMLEntity, UMLStepSetup, CreateUML
from tracer_id import TracerId


# import cProfile
# from line_profiler import LineProfiler

def get_configs():
    return Configs

# def analyse(file_object):
#     """
#     FileObject contains all information required
#     :param file_object: container with all information required
#     :return:
#     """
#     #
#     # Store all steps where flow/transaction has beeb "seen", this dictionary will have a reference_id
#     # representing either a tx id or flow id; and a list of umlsteps where this reference has been seen.
#     # uml_steps={}
#     #
#     # Interact through all transaction and flow list
#     #
#     for each_item in file_object.get_all_unique_results(CordaObject.Type.FLOW_AND_TRANSACTIONS):
#         # If this each_item, has references, which means flow/transaction was found in other lines,
#         # then lest compile all UML steps for this item.
#         #
#         # Take very first line and search for its uml_step; and add it into stack
#         first_step = file_object.get_element(CordaObject.Type.UML_STEPS, each_item.line_number)
#         if first_step:
#             first_step.set(UMLStep.Attribute.TYPE, each_item.type)
#             first_step.set(UMLStep.Attribute.ID, each_item.reference_id)
#             first_step.add()
#             # uml_steps[each_item.reference_id] = []
#             # uml_steps[each_item.reference_id].append(first_step)
#
#         if each_item.references:
#             for each_reference in each_item.references:
#                 if each_reference in file_object.get_all_unique_results(CordaObject.Type.UML_STEPS, False):
#                     # Get next uml_step from all references
#                     uml_step = file_object.get_element(CordaObject.Type.UML_STEPS, each_reference)
#                     if isinstance(uml_step, list):
#
#                         for each_step in uml_step:
#                             if not each_step.get(UMLStep.Attribute.TYPE) and not each_step.get(UMLStep.Attribute.ID):
#                                 each_step.set(UMLStep.Attribute.TYPE, each_item.type)
#                                 each_step.set(UMLStep.Attribute.ID, each_item.reference_id)
#
#                         UMLStep.set_direct_list(each_reference, uml_step)
#                         continue
#                     else:
#                         uml_step.set(UMLStep.Attribute.TYPE, each_item.type)
#                         uml_step.set(UMLStep.Attribute.ID, each_item.reference_id)
#
#                     uml_step.add()
#
#         # with all steps collected for each object;



def print_parties():

    for index,each_id in enumerate(FileManagement.get_all_unique_results('Party')):
        if each_id.get_corda_role():
            role = f'{each_id.get_corda_role()}'
        else:
            role = 'party'
        print(f"[{index+1:>3}] [{role:^11}] {each_id.name}")
        if each_id.has_alternate_names():
            for each_alternate_name in each_id.get_alternate_names():
                print(f"              `-->  {each_alternate_name}")

def main():
    log_file = None
    Configs.load_config()

    # Define default entity object endpoints...
    UMLEntityEndPoints.load_default_endpoints()

    # in this case I'm removing initial branch 'UML_SETUP' because final config is a collection of configuration settings
    # that removes this.

    if not args.log_file:
        print('You must provide a log file to scan')
        exit(0)
    else:
        log_file = args.log_file

    if log_file:
        # Create file_to_analyse object containing file_to_analyse that will be analysed, starting with a block-size of 15 Mbytes
        file_to_analyse = FileManagement(log_file, block_size_in_mb=15, debug=True)
        # Analyse first 50 (by default) lines from given file_to_analyse to determine which Corda log format is
        # This is done to be able to separate key components from lines like Time stamp, severity level, and log
        # message
        file_to_analyse.discover_file_format()
        #
        # Setup party collection
        #
        # Set actual configuration to use, and create object that will manage "Parties"
        collect_parties = GetParties(Configs)
        # Set file_to_analyse that will be used to extract information from
        collect_parties.set_file(file_to_analyse)
        # Set specific type we are going to collect
        collect_parties.set_element_type(CordaObject.Type.PARTY)
        #
        # Setting up collection of other data like Flows and Transactions
        #
        # Setup corresponding Config to use, and create object that will manage "RefIds" (Flows and transactions)
        collect_refIds = GetRefIds(Configs)
        # Set actual file_to_analyse that will be used to pull data from
        collect_refIds.set_file(file_to_analyse)
        # Set specific type of element we are going to extract
        collect_refIds.set_element_type(CordaObject.Type.FLOW_AND_TRANSACTIONS)
        # Now setting up analysis to check if current line is candidate for UML steps
        # collect_uml_steps = UMLStepSetup(Configs)
        #
        # Set element type for this task:
        # collect_uml_steps.set_element_type(CordaObject.Type.UML_STEPS)
        # Pre-analyse the file_to_analyse to figure out how to read it, if file_to_analyse is bigger than blocksize then file_to_analyse will be
        # Divided by chunks and will be created a thread for each one of them to read it
        file_to_analyse.pre_analysis() # Calculate on fly proper chunk sizes to accommodate lines correctly
        #
        # Add proper methods to handle each collection
        #
        file_to_analyse.add_process_to_execute(collect_parties)
        file_to_analyse.add_process_to_execute(collect_refIds)

        # start a time watch
        file_to_analyse.start_stop_watch('Main-search', True)
        # Start all threads required
        file_to_analyse.parallel_processing()
        # Prepare new execution
        # Clean up old processes:
        file_to_analyse.remove_process_to_execute(CordaObject.Type.PARTY)
        file_to_analyse.remove_process_to_execute(CordaObject.Type.FLOW_AND_TRANSACTIONS)
        # Setup new process to run
        # file_to_analyse.add_process_to_execute(collect_uml_steps)
        # file_to_analyse.parallel_processing()
        # Stopping timewatch process and get time spent
        time_msg = file_to_analyse.start_stop_watch('Main-search', False)
        # file_to_analyse.remove_process_to_execute(collect_uml_steps)

        if file_to_analyse.result_has_element(CordaObject.Type.PARTY):
            print('Setting up roles automatically...')
            file_to_analyse.assign_roles()
            print("\n X500 names found: ")
            print_parties()

            party = list(file_to_analyse.get_all_unique_results('Party'))[0]
            pending_roles = party.get_pending_roles()
            pselection = None
            if pending_roles:
                print('\nI was not able to find all roles, following roles were not assigned, please assign them manually:')
                print('   [0] -- Exit')
                while True:
                    if len(pending_roles) == 0:
                        break
                    for index, each_pending in enumerate(pending_roles):
                        print(f'   [{index+1}] -- {each_pending} which is {pending_roles[each_pending]} to assign...')
                    role_to_assign = input(f'Please choose role to assign [0-{len(pending_roles)}]:')
                    if not role_to_assign:
                        break
                    if role_to_assign.isdigit():
                        selection = int(role_to_assign)
                        if selection > len(pending_roles):
                            continue
                        if selection == -1:
                            break

                        role_list = list(pending_roles)
                        print(f'Please select party for {role_list[selection-1]}:')
                        if selection > len(pending_roles):
                            continue
                        selected_role = list(pending_roles)[selection - 1]
                        party_list = list(FileManagement.get_all_unique_results('Party'))
                        print('[ -1] [    None   ]')
                        print('[  0] [           ] Define a party not listed here')

                        print_parties()
                        while True:
                            party_selection = input(f'Select party [0-{len(party_list)}]:')
                            if party_selection.isdigit():
                                pselection = int(party_selection)

                                if pselection == 0:
                                    new_party=party.define_custom_party(rules_set=file_to_analyse.rules, assigned_role=selected_role)
                                    validation_list = file_to_analyse.parser.parse_line(new_party.name, [])
                                    if validation_list:
                                        validation = validation_list[0]
                                    else:
                                        validation = None
                                    if not validation or not validation.is_same_name(new_party.name):
                                        print('Invalid party name')
                                        continue

                                    if new_party:
                                        FileManagement.add_element('Party', new_party)
                                        break

                                if pselection > len(party_list):
                                    print('Invalid selection')
                                    continue

                                selected_party = party_list[pselection - 1]
                                selected_party.set_corda_role(selected_role)
                                break


                    if party.get_pending_roles():
                        continue
            if pselection:
                print('\n Party final assignation:')
                print_parties()

            response = input('Do you want to use this list for final analysis ([Y]es/[N]o/[M]odify) [Yes]: ')
            if response:
                if response == 'M':
                    response1 = input('What do you want to do? [D]elete / [M]odify a party:')
                    if response1:
                        if response1 == 'D':
                            while True:
                                print_parties()
                                party_list = list(FileManagement.get_all_unique_results('Party'))
                                select_party = input(f'Which party do you want to delete [1-{len(party_list)}] or just enter to exit:')
                                if select_party.isdigit():
                                    iselect_party = int(select_party)
                                    if iselect_party>len(party_list):
                                        print('Invalid selection')
                                        continue
                                    FileManagement.delete_element('Party', party_list[iselect_party-1])
                                if not select_party:
                                    break


        if file_to_analyse.result_has_element('Flows&Transactions'):
            print("\nThese total of other objects found:")
            results = collect_refIds.classify_results(FileManagement.get_all_unique_results('Flows&Transactions'))
            for each_result_type in results:
                item_count = 0
                print(f'  * {each_result_type}: {len(results[each_result_type])}')

                if len(results[each_result_type])> max_number_items_fNtx:
                    item_limit = max_number_items_fNtx
                else:
                    item_limit = len(results[each_result_type])

                for each_item in results[each_result_type]:
                    print(f"    `---> ({item_count+1:>4}) {each_item}")
                    item_count = item_count + 1
                    if item_count >= item_limit and (len(results[each_result_type])-item_limit > 0):
                        print(f"    ... there are {len(results[each_result_type])-item_limit} more...")
                        break

        print(f'Elapsed time {time_msg}.')
        ##
        # Testing
        ## -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
        # 1231B1D70E2CF011021F6379E3A802DF04E32D89784F61940A83A596EF99D1CF
        # a26f97bb-3ad3-40ac-8b6b-257bdd9bcba4
        # -l /home/larry/IdeaProjects/logtracer/client-logs/DLT-Service/CS-4010/DLT_suspendMembership.txt
        # 9888363EC1AAF0AAD8B64911D4202EA9ACE288D530B509020ADE326443B305E4
        # 49cea758-40d9-48d2-a4eb-9ce770c307fd
        co = CordaObject.get_object(args.reference)
        test = UMLStepSetup(get_configs(), co)
        test.file = file_to_analyse
        test.parallel_process(co)
        c_uml = CreateUML(co, file_to_analyse)
        script = c_uml.generate_uml_pages()
        print("\n".join(script))
        ##########################
        return file_to_analyse
    return None


if __name__ == "__main__":
    max_number_items_fNtx = 15
    # Small file with all roles
    # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
    # -l/home/larry/IdeaProjects/logtracer/client-logs/Grow-super/CS-3873/logsinsurance/corda-node-cordaprimary-prod-growadmin-i-0bb90aaa48c7b6b88.dlta.internal.2024-12-02-7.log
    # Very small one to test UML
    # -l /home/larry/IdeaProjects/logtracer/checks/log-test.log
    # Office
    # -l
    # /Users/larry.castro/IdeaProjects/logtracer/client-logs/Grow-super/logsinsurance/corda-node-cordaprimary-prod-growadmin-i-0bb90aaa48c7b6b88.dlta.internal.2024-12-02-23.log
    # Small size and have all roles:
    # -l
    # /Users/larry.castro/IdeaProjects/logtracer/client-logs/Finteum/CS-3462/notary-issue/node-bull-759dc59895-j7rmw.log
    # ===
    # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
    # -l "/home/r3support/www/uploads/customers/Grow Super/CS-3992/20250225103248_pack"/corda-node-dev0-ri-hes-admin-node.2025-02-19-1.log
    #
    # Huge files:
    # -l /home/larry/IdeaProjects/logtracer/client-logs/ChainThat/CS-4002/Success-Transaction-logs.log
    # -l /home/larry/IdeaProjects/investigations/lab-constructor/investigation/ChainThat/CS-4002/client-logs/mnp-dev-party005-cordanode.log
    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                            help='Give actual log file to analyse')
    parserargs.add_argument('-r', '--reference',
                            help='Reference ID to trace flow-id or tx-id')

    args = parserargs.parse_args()

    file = main()

    pass
    # tracer = TracerId(get_configs())
    # #
    # tracer.tracer(file)

    # cProfile.run("main()")#, 'profile-results.prof')
