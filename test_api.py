import json
from core import analyze_corda_log, DataInfo, save_analysis



# Tests:
# pull a list of:
# Transactions    [DONE]
# Flows           [DONE]
# Parties         [DONE]
# Errors found    [DONE]
# UML steps       [PENDING]
# TODO: everytime it ran it "forgets" about what was analysed, this will prevent analysis of specific flows or tx
#       I need to include a method to "save" what was collected so program has something to look at


if __name__ == "__main__":
    datainfo = DataInfo()
    datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
    datainfo.set(DataInfo.Attribute.TICKET, "TST-0000")
    datainfo.set(DataInfo.Attribute.CORDA_VERSION, "4.9")
    datainfo.set(datainfo.Attribute.ENVIRONMENT, "UAT")
    datainfo.set(datainfo.Attribute.ISSUE, "Testing logs")
    datainfo.set(datainfo.Attribute.DESCRIPTION, "This is just for logs testing API")

    #result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/NCR/CS-4189/2026-03-10-11-prd-api-service.log",
    # result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/tests-logs/insuree.log",
    # result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/ChainThat/CS-4002/mnp-dev-party005-cordanode-7.log",
    result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/HQLAx/CS-4163/hqlx.log",
                               datainfo=datainfo)
    #result = analyze_corda_log("client-logs/ChainThat/CS-4002/party005-dev-corda-logs.txt")
    #save_analysis(result, CordaObject.Type.ERROR_ANALYSIS)
    save_analysis(result)
    print(json.dumps(result, indent=2))
