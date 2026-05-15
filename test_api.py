import json

from core import  DataInfo, CoreApi
from drivers.yaml_driver import YamlDataDriver
from log_handler import start_log_consumer, stop_log_consumer
from object_class import FileManagement, Configs, CordaObject
import log_handler


# Tests:
# pull a list of:
# Transactions    [DONE]
# Flows           [DONE]
# Parties         [DONE]
# Errors found    [DONE]
# UML steps       [PENDING]
# TODO: everytime it ran it "forgets" about what was analysed, this will prevent analysis of specific flows or tx
#       I need to include a method to "save" what was collected so program has something to look at



def test_analysis():
    """
    Saving test
    :return:
    """

    analysis = CoreApi(datainfo)
    analysis.analyze_corda_log()

    return analysis


def list_test(customer=None, ticket=None):
    """
    testing loading data
    :return:
    """
    datainfo = DataInfo()
    if customer:
        datainfo.set(DataInfo.Attribute.CUSTOMER, customer)
    if ticket:
        datainfo.set(DataInfo.Attribute.TICKET, ticket)
    check_logs = CoreApi(datainfo)

    response = check_logs.list_current_logs()

    print(json.dumps(response, indent=2))


def test_load(datainfo, logid):
    """
    Load test
    :param datainfo: data info related to customer to load
    :return: a dictionary containing all customer analysis data.
    """

    customer_data = CoreApi(datainfo)
    loaded_data=customer_data.load_data(logid)

    payload = loaded_data.get_payload()

    return payload

def trace_reference(datainfo, logid, refid):
    """
    Trace test
    :param datainfo:
    :param refid:
    :return:
    """
    customer_data = CoreApi(datainfo)
    customer_data.load_ticket_details()

    customer_data.trace_analysis(logfile_id=logid, reference_id=refid)

    return customer_data

if __name__ == "__main__":
    start_log_consumer(log_file="./api.log")
    analysis = None
    trace_refid = None
    Configs.load_config()
    action = ['xcreate',
              'xanalysis',
              'xsave',
              'xlist',
              'xload',
              'trace',
              'save-trace']

    if 'create' in action:
        # Add test
        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
        datainfo.set(DataInfo.Attribute.TICKET, "TS-0001")
        datainfo.set(DataInfo.Attribute.CORDA_VERSION, "4.11.5")
        datainfo.set(datainfo.Attribute.ENVIRONMENT, "UAT")
        datainfo.set(datainfo.Attribute.ISSUE, "Test logs")
        datainfo.set(datainfo.Attribute.DESCRIPTION, "Testing log analysis")

        create_log = CoreApi(datainfo)
        # analysis.add_log_file("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/ChainThat/CS-4002/02-10-2025/Corda-Start-logs.log")
        # analysis.add_log_file("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/ChainThat/CS-4002/02-10-2025/Success-Transaction-logs.log")
        create_log.add_log_file("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/test-customer/devrel.log")

        create_log.create_structure()

        pass

    if 'analysis' in action:
        # analysis test
        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
        datainfo.set(DataInfo.Attribute.TICKET, "TS-0001")

        analysis = test_analysis()

    if 'save' in action:
        # save test

        if analysis:
            analysis.save_analysis()

    if 'list' in action:
        # List saved data
        list_test()

    if 'load' in action:
        # Test:
        # * Load Data

        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
        datainfo.set(DataInfo.Attribute.TICKET, "TS-0001")

        load_data=test_load(datainfo, '57e41eac0b897e9a')

        pass
        # '3b9bef7e-57da-4790-b30b-9931cd87395e'

    if 'trace' in action:
        # * trace for specific reference ID (like a flow) on a specific log file

        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
        datainfo.set(DataInfo.Attribute.TICKET, "TS-0001")
        trace_refid = trace_reference(datainfo,logid='57e41eac0b897e9a', refid='2c5fae67-cbc6-4a87-b987-70af14fd3ec7')


    if 'save-trace' in action:
        if trace_refid:
            trace_refid.save_analysis(object_type=CordaObject.Type.FLOW_AND_TRANSACTIONS)

    stop_log_consumer()