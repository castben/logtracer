import json

import drivers.yaml_driver
from core import analyze_corda_log, DataInfo
from drivers.yaml_driver import YamlDataDriver
from object_class import CordaObject

# Tests:
# pull a list of:
# Transactions
# Flows
# Parties
# Errors found
# TODO: everytime it ran it "forgets" about what was analysed, this will prevent analysis of specific flows or tx
#       I need to include a method to "save" what was collected so program has something to look at

datainfo = DataInfo()
datainfo.set(DataInfo.Attribute.CUSTOMER, "test-customer")
datainfo.set(DataInfo.Attribute.TICKET, "TST-0000")

#result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/client-logs/NCR/CS-4189/2026-03-10-11-prd-api-service.log",
result = analyze_corda_log("/home/larry/IdeaProjects/logtracer/c4-logs/tests-logs/insuree.log",
                           [CordaObject.Type.ERROR_ANALYSIS, CordaObject.Type.FLOW_AND_TRANSACTIONS, CordaObject.Type.PARTY],
                           datainfo)
#result = analyze_corda_log("client-logs/ChainThat/CS-4002/party005-dev-corda-logs.txt")


def save_analysis(result, object_type=None):
    """
    Store analysis.
    :param object_type:
    :return:
    """

    if not object_type:
        object_type = [
            CordaObject.Type.FLOW_AND_TRANSACTIONS,
            CordaObject.Type.PARTY,
            CordaObject.Type.ERROR_ANALYSIS,
        ]

    for each_object in object_type:
        storage = YamlDataDriver()

        customer = datainfo.get(DataInfo.Attribute.CUSTOMER)
        ticket = datainfo.get(DataInfo.Attribute.TICKET)

        if each_object == CordaObject.Type.ERROR_ANALYSIS:
            config = {
               'data_dir': f"./data/storage/{customer}/{ticket}",
               'cache_enabled': True
            }

            storage.connect(config)

            for each_item in result["result"][each_object]:









    pass






print(json.dumps(result, indent=2))
