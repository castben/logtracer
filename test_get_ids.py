
# Program to test extraction and validation of X500 names.

import os
import argparse
from object_class import Party


from sqlalchemy.sql.visitors import iterate
from object_class import Configs, X500NameParser, FileManagement
from object_class import CordaObject,saving_tracing_ref_data
from tracer_id import TracerId
from get_ids import GetRefIds

def get_configs():
    return Configs



if __name__ == "__main__":
    log_file = None
    Configs.load_config()
    app_path = os.path.dirname(os.path.abspath(__file__))
    app_path_support = app_path
    logfile_format = None

    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                            help='Give actual log file to pre-format')

    args = parserargs.parse_args()
    # load_corda_object_definition('%s/conf/logwatcher_rules.json' % (app_path,))


    alternate_name_found = False
    # x500_list = []
    test_list = []
    # in this case I'm removing initial branch 'UML_SETUP' because final config is a collection of configuration settings
    # that removes this.
    rules = Configs.get_config_for('UML_DEFINITIONS.participant')
    parser = X500NameParser(rules['RULES-D'])

    if not args.log_file:
        print('You must provide a log file to scan')
        exit(0)
    else:
        log_file = args.log_file

    if log_file:
        # -l /home/larry/IdeaProjects/logtracer/c4-logs/node-Omega-X-SolutionEng.log
        file = FileManagement(log_file, block_size_in_mb=5, debug=True)
        # Analyse first 100 (by default) lines from given file to determine which Corda log format is
        # This is done to be able to separate key components from lines like Time stamp, severity level, and log
        # message
        file.discover_file_format()
        ref_ids = GetRefIds(Configs)
        ref_ids.set_file(file)
        file.pre_analysis() # Calculate on fly proper chunk sizes to accommodate lines correctly
        file.set_process_to_execute('ID_Refs',ref_ids)
        file.start_stop_watch('Main-search', True)
        file.parallel_processing()
        time_msg = file.start_stop_watch('Main-search', False)
        file.assign_roles()

        # with open(file.filename, "r") as fh_log_file:
        #     for each_line in fh_log_file:
        #         co = ref_ids.get_ref_ids(each_line)
        #         parsed_names = parser.parse_line(each_line, test_list)
        #         for each_name in parsed_names:
        #             each_name.identify_party_role(each_line)
        #
        #     print("-------------\nParsed X500 Names:")
        #     print(f"I've found {len(parsed_names)} name(s)...")
        #     for num,each_name in enumerate(parsed_names):
        #         print(f"{num+1:>3} -- {each_name.string()}")
        #         if each_name.has_alternate_names():
        #             for each_alternatename in each_name.get_alternate_names():
        #                 print(f'   Alternate Name: {each_alternatename}')
        #
        # if CordaObject.list:
        #     print('-------------')
        #     total_ids = 0
        #     for each_type in CordaObject.list:
        #         print(f'* Found {len(CordaObject.list[each_type])} {each_type}(S)')
        #         total_ids += len(CordaObject.list[each_type])
        #     print(f'Total ids: {total_ids}')
        #     saving_tracing_ref_data(CordaObject.get_all_objects(), log_file=file.filename)


            # trace_id(args.log_file)

        print("\n X500 names found: ")
        for each_id in FileManagement.get_all_unique_results():
            if each_id.get_corda_role():
                role = f'{each_id.get_corda_role()}'
            else:
                role = 'party'
            print(f" [{role:^8}] {each_id.name}")
            if each_id.has_alternate_names():
                for each_alternate_name in each_id.get_alternate_names():
                    print(f"     `--> {each_alternate_name}")

        print(f'Elapsed time {time_msg}.')
        pass