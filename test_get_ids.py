
# Program to test extraction and validation of X500 names.

import os
import argparse
from get_refIds import GetRefIds
from object_class import Configs, X500NameParser, FileManagement
from object_class import CordaObject,saving_tracing_ref_data
# from tracer_id import TracerId
from get_parties import GetParties

import cProfile
from line_profiler import LineProfiler

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
def main():
    log_file = None
    Configs.load_config()
    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                            help='Give actual log file to pre-format')
    args = parserargs.parse_args()

    # in this case I'm removing initial branch 'UML_SETUP' because final config is a collection of configuration settings
    # that removes this.

    if not args.log_file:
        print('You must provide a log file to scan')
        exit(0)
    else:
        log_file = args.log_file

    if log_file:
        # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
        # -l/home/larry/IdeaProjects/logtracer/client-logs/Grow-super/CS-3873/logsinsurance/corda-node-cordaprimary-prod-growadmin-i-0bb90aaa48c7b6b88.dlta.internal.2024-12-02-7.log
        file = FileManagement(log_file, block_size_in_mb=15, debug=True)
        # Analyse first 100 (by default) lines from given file to determine which Corda log format is
        # This is done to be able to separate key components from lines like Time stamp, severity level, and log
        # message
        file.discover_file_format()
        collect_parties = GetParties(Configs)
        collect_parties.set_file(file)
        collect_parties.set_element_type('Party')
        collect_refIds = GetRefIds(Configs)
        collect_refIds.set_file(file)
        collect_refIds.set_element_type('Flows&Transactions')

        file.pre_analysis() # Calculate on fly proper chunk sizes to accommodate lines correctly
        # Add proper methods to collect info
        file.add_process_to_execute(collect_parties)
        file.add_process_to_execute(collect_refIds)

        file.start_stop_watch('Main-search', True)
        file.parallel_processing()
        time_msg = file.start_stop_watch('Main-search', False)

        if file.result_has_element('Party'):
            file.assign_roles()
            print("\n X500 names found: ")
            for index,each_id in enumerate(FileManagement.get_all_unique_results('Party')):
                if each_id.get_corda_role():
                    role = f'{each_id.get_corda_role()}'
                else:
                    role = 'party'
                print(f"[{index+1:>3}] [{role:^11}] {each_id.name}")
                if each_id.has_alternate_names():
                    for each_alternate_name in each_id.get_alternate_names():
                        print(f"              `--> {each_alternate_name}")

        if file.result_has_element('Flows&Transactions'):
            print("\nThese total of other objects found:")
            results = collect_refIds.classify_results(FileManagement.get_all_unique_results('Flows&Transactions'))
            for each_result_type in results:
                print(f'  * {each_result_type}: {len(results[each_result_type])}')

        print(f'Elapsed time {time_msg}.')
        pass

if __name__ == "__main__":
    main()
    # cProfile.run("main()", 'profile-results.prof')
