import json
from core import analyze_corda_log
result = analyze_corda_log("c4-logs/client-logs/ChainThat/CS-4002/party005-dev-corda-logs.log")
print(json.dumps(result, indent=2))
