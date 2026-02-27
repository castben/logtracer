import json
from core import analyze_corda_log
from object_class import CordaObject

result = analyze_corda_log("c4-logs/client-logs/Nexi Payments/CS-4105_07-01-26/node-ascorda_Bank03069_01-full.log",
                           CordaObject.Type.ERROR_ANALYSIS)
#result = analyze_corda_log("client-logs/ChainThat/CS-4002/party005-dev-corda-logs.txt")

print(json.dumps(result, indent=2))
