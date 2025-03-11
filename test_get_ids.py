import cProfile
# Program to test extraction and validation of X500 names.

import os
import argparse
from get_refIds import GetRefIds
from object_class import Configs, X500NameParser, FileManagement, UMLEntity
from object_class import CordaObject,saving_tracing_ref_data
# from tracer_id import TracerId
from get_parties import GetParties
from tracer_id import TracerId


# import cProfile
# from line_profiler import LineProfiler

def get_configs():
    return Configs


def test_refids(log_file):
    ref_ids = GetRefIds(get_configs())
    file = FileManagement(log_file, block_size_in_mb=15, debug=True)
    # Analyse first 100 (by default) lines from given file to determine which Corda log format is
    # This is done to be able to separate key components from lines like Time stamp, severity level, and log
    # message
    file.discover_file_format()
    ref_ids.set_file(file)
    with open(file.filename, "r") as fh_log_file:
        for each_line in fh_log_file:
            co = ref_ids.get_ref_ids(each_line)


    if CordaObject.list:
        print('-------------')
        total_ids = 0
        for each_type in CordaObject.list:
            print(f'* Found {len(CordaObject.list[each_type])} {each_type}(S)')
            total_ids += len(CordaObject.list[each_type])
        print(f'Total ids: {total_ids}')
        # saving_tracing_ref_data(CordaObject.get_all_objects(), log_file=args.log_file)
    # trace_id(args.log_file)

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


    # in this case I'm removing initial branch 'UML_SETUP' because final config is a collection of configuration settings
    # that removes this.

    if not args.log_file:
        print('You must provide a log file to scan')
        exit(0)
    else:
        log_file = args.log_file

    if log_file:
        file = FileManagement(log_file, block_size_in_mb=15, debug=True)
        # Analyse first 15 (by default) lines from given file to determine which Corda log format is
        # This is done to be able to separate key components from lines like Time stamp, severity level, and log
        # message
        file.discover_file_format()
        #
        # Setup party collection
        #
        # Set actual configuration to use
        collect_parties = GetParties(Configs)
        # Set file that will be used to extract information from
        collect_parties.set_file(file)
        # Set specific type we are going to collect
        collect_parties.set_element_type('Party')
        #
        # Setting up collection of other data like Flows and Transactions
        #
        # Setup corresponding Config to use
        collect_refIds = GetRefIds(Configs)
        # Set actual file that will be used to pull data from
        collect_refIds.set_file(file)
        # Set specific type of element we are going to extract
        collect_refIds.set_element_type('Flows&Transactions')
        # Now setting up analysis to get associated UML step for this line (if it exists)
        collect_uml_steps = TracerId(Configs)
        #
        # Pre-analyse the file to figure out how to read it, if file is bigger than blocksize then file will be
        # Divided by chunks and will be created a thread for each one of them to read it
        file.pre_analysis() # Calculate on fly proper chunk sizes to accommodate lines correctly
        #
        # Add proper methods to handle each collection
        #
        file.add_process_to_execute(collect_parties)
        file.add_process_to_execute(collect_refIds)
        # start a time watch
        file.start_stop_watch('Main-search', True)
        # Start all threads required
        file.parallel_processing()
        # Stopping timewatch process and get time spent
        time_msg = file.start_stop_watch('Main-search', False)

        if file.result_has_element('Party'):
            print('Setting up roles automatically...')
            file.assign_roles()
            print("\n X500 names found: ")
            print_parties()

            party = list(file.get_all_unique_results('Party'))[0]
            pending_roles = party.get_pending_roles()
            pselection = None
            if pending_roles:
                print('\nI was not able to find all roles, following roles were not assigned, please assign them manually:')
                print('   [0] -- None')
                while True:
                    if len(pending_roles) == 0:
                        break
                    for index, each_pending in enumerate(pending_roles):
                        print(f'   [{index+1}] -- {each_pending} which is {pending_roles[each_pending]} to assign...')
                    role_to_assign = input(f'Please choose role to assign [0-{len(pending_roles)}]:')
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
                                    new_party=party.define_custom_party(rules_set=file.rules, assigned_role=selected_role)
                                    validation_list = file.parser.parse_line(new_party.name, [])
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
                                select_party = input(f'Which party do you want to delete [1-{len(party_list)}]:')
                                if select_party.isdigit():
                                    iselect_party = int(select_party)
                                    if iselect_party>len(party_list):
                                        print('Invalid selection')
                                        continue
                                    FileManagement.delete_element('Party', party_list[iselect_party-1])

        if file.result_has_element('Flows&Transactions'):
            print("\nThese total of other objects found:")
            results = collect_refIds.classify_results(FileManagement.get_all_unique_results('Flows&Transactions'))
            for each_result_type in results:
                print(f'  * {each_result_type}: {len(results[each_result_type])}')

        print(f'Elapsed time {time_msg}.')
        return file


if __name__ == "__main__":
    # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
    # -l/home/larry/IdeaProjects/logtracer/client-logs/Grow-super/CS-3873/logsinsurance/corda-node-cordaprimary-prod-growadmin-i-0bb90aaa48c7b6b88.dlta.internal.2024-12-02-7.log
    # Office
    # -l
    # /Users/larry.castro/IdeaProjects/logtracer/client-logs/Grow-super/logsinsurance/corda-node-cordaprimary-prod-growadmin-i-0bb90aaa48c7b6b88.dlta.internal.2024-12-02-23.log
    # Small size and have all roles:
    # -l
    # /Users/larry.castro/IdeaProjects/logtracer/client-logs/Finteum/CS-3462/notary-issue/node-bull-759dc59895-j7rmw.log
    # ===
    # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
    # -l "/home/r3support/www/uploads/customers/Grow Super/CS-3992/20250225103248_pack"/corda-node-dev0-ri-hes-admin-node.2025-02-19-1.log

    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                            help='Give actual log file to analyse')
    args = parserargs.parse_args()

    file = main()
    tracer = TracerId(file, get_configs())
    #
    tracer.tracer(file)

    # cProfile.run("main()")#, 'profile-results.prof')
