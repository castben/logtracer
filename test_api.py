import json
from core import  DataInfo, CoreApi

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


def test_load(datainfo):
    """
    Load test
    :param datainfo: data info related to customer to load
    :return: a dictionary containing all customer analysis data.
    """

    customer_data = CoreApi(datainfo)
    customer_data.load_analysis()




if __name__ == "__main__":
    analysis_test = None
    if True:
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

    if True:
        if analysis_test:
            analysis_test.save_analysis()

    if False:
        list_test()

    if False:
        datainfo = DataInfo()
        datainfo.set(DataInfo.Attribute.CUSTOMER, "ChainThat")
        datainfo.set(DataInfo.Attribute.TICKET, "CS-4002")

        test_load(datainfo)

