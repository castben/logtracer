import json
from core import  DataInfo, CoreApi
from drivers.yaml_driver import YamlDataDriver
from object_class import FileManagement, Configs, CordaObject
from uml import UMLStepSetup


# Tests:
# pull a list of:
# Transactions    [DONE]
# Flows           [DONE]
# Parties         [DONE]
# Errors found    [DONE]
# UML steps       [PENDING]
# TODO: everytime it ran it "forgets" about what was analysed, this will prevent analysis of specific flows or tx
#       I need to include a method to "save" what was collected so program has something to look at

def test_analysis(analysis):
    """
    Saving test
    :return:
    """

    #result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/NCR/CS-4189/2026-03-10-11-prd-api-service.log",
    # result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/tests-logs/insuree.log",
    # result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/ChainThat/CS-4002/mnp-dev-party005-cordanode-7.log",
    analysis.analyze_corda_log()
    #result = analyze_corda_log("client-logs/ChainThat/CS-4002/party005-dev-corda-logs.txt")
    #save_analysis(result, CordaObject.Type.ERROR_ANALYSIS)
    return analysis
    # analysis.save_analysis()
    #print(json.dumps(analysis.get_results(), indent=2))

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
    data = customer_data.load_ticket_details()
    data_check = YamlDataDriver()
    data_check.connect(data_dir=f'data/storage/{data["customer"]}/{data["ticket"]}/{logid}')

    data_analysis = data_check.load_data()

    #

    return data_analysis

def trace_reference(datainfo, logid, refid):
    """
    Trace test
    :param datainfo:
    :param refid:
    :return:
    """
    customer_data = CoreApi(datainfo)
    customer_data.load_ticket_details()
    # data_check = YamlDataDriver()
    # data_check.connect(data_dir=f'data/storage/{data["customer"]}/{data["ticket"]}/{logid}')
    # data_analysis = data_check.load_data()

    customer_data.trace_analysis(logfile_id=logid, reference_id=refid)

    return customer_data
if __name__ == "__main__":
    analysis_test = None
    Configs.load_config()
    if False:
        # Add test
        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
        datainfo.set(DataInfo.Attribute.TICKET, "TS-0001")
        datainfo.set(DataInfo.Attribute.CORDA_VERSION, "4.11.5")
        datainfo.set(datainfo.Attribute.ENVIRONMENT, "UAT")
        datainfo.set(datainfo.Attribute.ISSUE, "Test logs")
        datainfo.set(datainfo.Attribute.DESCRIPTION, "Testing log analysis")
        #test_analysis(datainfo, "/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/HQLAx/CS-4163/hqlx.log")

        analysis = CoreApi(datainfo)
        # analysis.add_log_file("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/ChainThat/CS-4002/02-10-2025/Corda-Start-logs.log")
        # analysis.add_log_file("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/ChainThat/CS-4002/02-10-2025/Success-Transaction-logs.log")
        analysis.add_log_file("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/test-customer/observer.log")
        analysis.add_log_file("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/test-customer/solutioneng.log")
        analysis_test = test_analysis(analysis)

    if False:

        # save test

        if analysis_test:
            analysis_test.save_analysis()

    if True:
        # List saved data
        list_test()

    if False:
        # Test:
        # * Load Data

        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
        datainfo.set(DataInfo.Attribute.TICKET, "TS-0001")

        load_data=test_load(datainfo,logid='05c4d0b116fa664e')



        pass
        # '3b9bef7e-57da-4790-b30b-9931cd87395e'

    if True:
        # * trace for specific reference ID (like a flow) on a specific log file

        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
        datainfo.set(DataInfo.Attribute.TICKET, "TS-0001")
        trace_refid = trace_reference(datainfo,logid='05c4d0b116fa664e', refid='11b1776e-f894-4afd-a2c7-a87dc4d983bb')