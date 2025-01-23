
# Program to test extraction and validation of X500 names.

import os
import argparse

from logtracer import get_ref_ids
from object_class import Configs, X500NameParser, FileManagement
from object_class import CordaObject,saving_tracing_ref_data



def get_configs():
    return Configs
from get_ids import GetRefIds


if __name__ == "__main__":
    log_file = None
    Configs.load_config()
    app_path = os.path.dirname(os.path.abspath(__file__))
    app_path_support = app_path
    logfile_format = None
    file = FileManagement(log_file, block_size=0)
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
        ref_ids = GetRefIds(Configs)
        with open(log_file, "r") as fh_log_file:
            for each_line in fh_log_file:
                co = ref_ids.get_ref_ids(each_line,file)
                parsed_names = parser.parse_line(each_line, test_list)
                for each_name in parsed_names:
                    each_name.identify_party_role(each_line)

            print("-------------\nParsed X500 Names:")

            for each_name in parsed_names:
                print(f"* {each_name.string()}")
                if each_name.has_alternate_names():
                    for each_alternatename in each_name.get_alternate_names():
                        print(f'   Alternate Name: {each_alternatename}')

        if CordaObject.list:
            print('-------------')
            for each_type in CordaObject.list:
                print(f'* Found {len(CordaObject.list[each_type])} {each_type}(S)')

            saving_tracing_ref_data(CordaObject.get_all_objects(), log_file=args.log_file)

            # trace_id(args.log_file)

    pass