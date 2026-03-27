import json

import drivers.yaml_driver
from core import analyze_corda_log, DataInfo
from drivers.yaml_driver import YamlDataDriver
from object_class import CordaObject, Error, Party


# Tests:
# pull a list of:
# Transactions
# Flows
# Parties
# Errors found
# TODO: everytime it ran it "forgets" about what was analysed, this will prevent analysis of specific flows or tx
#       I need to include a method to "save" what was collected so program has something to look at




def save_analysis(result, object_type=None):
    """
    Store analysis.
    :param object_type: What to persist from API response...
    :return:
    """

    if not object_type:
        object_type = [
            CordaObject.Type.FLOW_AND_TRANSACTIONS,
            CordaObject.Type.PARTY,
            CordaObject.Type.ERROR_ANALYSIS,
            CordaObject.Type.SPECIAL_BLOCKS
        ]

    if not isinstance(object_type, list):
       object_type = [object_type]

    customer = datainfo.get(DataInfo.Attribute.CUSTOMER)
    ticket = datainfo.get(DataInfo.Attribute.TICKET)
    storage = YamlDataDriver()
    summary = {
        "analysis": result["summary"]
    }
    storage.connect(data_dir= f"./data/storage/{customer}/{ticket}", summary=summary)

    for each_object in object_type:
        if each_object == CordaObject.Type.ERROR_ANALYSIS and each_object.value in result["results"]:
            category = result["results"][each_object.value]
            for each_item_category in category:
                for each_error in category[each_item_category]:
                    error_list = category[each_item_category][each_error]
                    for each_item in error_list:
                        # error = Error()
                        # error.category = each_item_category
                        # error.type = each_item["type"]
                        # error.level = each_item["level"]
                        # error.line_number = each_item['line_number']
                        # error.timestamp = each_item['timestamp']
                        # error.reference_id = each_item['line_number']
                        # error.log_line = each_item["log_line"]
                        if 'category' not in each_item:
                            each_item['category'] = each_item_category
                        if 'reference_id' not in each_item:
                            each_item['reference_id'] = each_item['line_number']

                        storage.save_error(each_item)

        if each_object == CordaObject.Type.PARTY and each_object.value in result["results"]:
            for each_party in result['results'][each_object.value]:
                party = Party(each_party['name'])
                party.set_corda_role('/'.join(each_party['roles']))
                # storage.save_party(each_party)
                storage.save_party(party)

        if each_object == CordaObject.Type.FLOW_AND_TRANSACTIONS and each_object.value in result["results"]:
            object_list = result['results'][each_object.value]
            for each_item in object_list:
                # co = CordaObject()
                # co.from_dict(object_list[each_item])
                storage.save_corda_object(object_list[each_item])

        if each_object == CordaObject.Type.SPECIAL_BLOCKS and each_object.value in result["results"]:
            block_type_list = result['results'][CordaObject.Type.SPECIAL_BLOCKS.value]['collected_blocktypes']
            for each_block_type in block_type_list:
                for each_block in block_type_list[each_block_type]:
                    storage.save_block_item(block_type_list[each_block_type][each_block])
    storage.disconnect()




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
