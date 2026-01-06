import json
from core import analyze_corda_log
result = analyze_corda_log("client-logs/ChainThat/CS-4002/party005-dev-corda-logs.txt")
print(json.dumps(result, indent=2))
