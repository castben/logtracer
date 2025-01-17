import os

from logtracer import Configs, build_regex, CordaObject, get_fields_from_log, load_corda_object_definition, load_rules, \
    saving_tracing_ref_data, trace_id
from x500check import X500NameParser
import re
import argparse

def get_ref_ids(each_line):
    """
    Search for all identifiable ids on a log

    :return:
    """
    global logfile_format
    #TODO: transformar esta rutina para que trabaje con una sola linea antes lo hacia haciendo un bucle

    co = None
    corda_objects = Configs.get_config(section='CORDA_OBJECTS')
    corda_object_detection = None
    # Complete list of corda object regex definition
    all_regex = []
    # A helper list to give the type and avoid to do a second search on the config to gather object type
    all_regex_type = []
    if not corda_objects:
        print("No definition for corda objects found, please setup CORDA_OBJECT section on config")
        exit(0)
    else:
        # Collect from "CORDA_OBJECTS" all object definitions:
        corda_objects = Configs.get_config(section="CORDA_OBJECTS")

        for each_type in corda_objects:
            if "EXPECT" in Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]:
                regex_list = Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]["EXPECT"]
                for each_rgx in regex_list:
                    all_regex.append(build_regex(each_rgx, nogroup_name=True))
                    all_regex_type.append(each_type)

        # Prepare full regex for quick detection (combine all "forms" of references ID's defined)
        corda_object_detection = "|".join(all_regex)

    try:
        if not logfile_format:
            for each_version in Configs.get_config(section="VERSION"):
                try_version = Configs.get_config(section="VERSION", param=each_version)
                check_version = re.search(try_version["EXPECT"], each_line)
                if check_version:
                    logfile_format = each_version
                    print("Log file format recognized as: %s" % logfile_format)
                    break

        # This will try to match given line with all possible patterns for required ID's these patterns came
        # from definition file at CORDA_OBJECT in there you will see all definitions program is looking for to
        # identify a CORDA_OBJECT

        cordaobject_id_match = re.finditer(corda_object_detection, each_line)

        if cordaobject_id_match:
            group_count = 0
            for matchNum, match in enumerate(cordaobject_id_match, start=1):
                for groupNum in range(0, len(match.groups())):
                    groupNum = groupNum + 1
                    each_group = match.group(groupNum)
                    if each_group and each_group not in CordaObject.id_ref:
                        # print("id {group} identified as {type}".format(
                        #     group=match.group(groupNum),
                        #     type=all_regex_type[groupNum-1]
                        # ))

                        # Add a new reference found into the list
                        CordaObject.id_ref.append(each_group)
                        #
                        # Also create this object to be identified later:
                        # first extract line features (timestamp, severity, etc)
                        log_line_fields = get_fields_from_log(each_line, logfile_format)
                        # Create object:
                        co = CordaObject()
                        # TODO: Hay un bug que ocurre cuando el programa detecta un corda_object que esta
                        #  en una linea que esta fuera (tiene retorno de carro) de la linea principal del
                        #  log lo que provoca que el objeto no sea creado... por los momentos voy a
                        #  ignorar estas referencias...
                        if log_line_fields:
                            if not 'error_level' in log_line_fields:
                                log_line_fields['error_level'] = 'INFO'
                            # Create object
                            co.add_data("id_ref", each_group)
                            co.add_data("Original line", each_line)
                            co.add_data("error_level", log_line_fields["error_level"])
                            co.add_data("timestamp", log_line_fields["timestamp"])
                            co.add_data("type", all_regex_type[groupNum-1])
                            co.set_type(all_regex_type[groupNum-1])
                            co.add_object()


        # print("Summary:")
        # for each_type in CordaObject.list:
        #     print(" * %s %s(S) identified." % (len(CordaObject.list[each_type]), each_type))

        if not logfile_format:
            print("Sorry I can't find a proper log template to parse this log terminating program")
            exit(0)

        return co

        # if len(CordaObject.id_ref) > 0:
        #     print('%s file contains %s ids' % (log_file, len(CordaObject.id_ref)))
        #
        # if len(CordaObject.id_ref) > 50 and not args.web_style:
        #     print('**WARNING** this may take long time to complete...')
        #     print('Do you want to track all id\'s in %s file ?' % (log_file,))
        #
        #     response = input('> ')
        #     if response != 'y':
        #         exit(0)

        # Flows.flow_summary()

        # print('Finished.')
    except IOError as io:
        print('Sorry unable to open %s due to %s' % (log_file, io))


if __name__ == "__main__":
    log_file = None
    app_path = os.path.dirname(os.path.abspath(__file__))
    app_path_support = app_path
    logfile_format = None
    parserargs = argparse.ArgumentParser()
    parserargs.add_argument('-l', '--log-file',
                            help='Give actual log file to pre-format')

    args = parserargs.parse_args()
    # load_corda_object_definition('%s/conf/logwatcher_rules.json' % (app_path,))
    Configs.load_config()
    load_rules()

    alternate_name_found = False
    # x500_list = []
    test_list = []
    # in this case I'm removing initial branch 'UML_SETUP' because final config is a collection of configuration settings
    # that removes this.
    rules = Configs.get_config_for('UML_DEFINITIONS.participant')
    parser = X500NameParser(rules)

    if not args.log_file:
        print('You must provide a log file to scan')
        exit(0)
    else:
        log_file = args.log_file

    if log_file:
        with open(log_file, "r") as fh_log_file:
            for each_line in fh_log_file:
               co = get_ref_ids(each_line)
               parsed_names = parser.parse_line(each_line, test_list)

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

            trace_id()

    pass


