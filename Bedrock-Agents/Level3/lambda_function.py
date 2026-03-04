import json
import os
import urllib.request

# Required environment variables
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

def lambda_handler(event, _):
    if event["function"] != "tavily-ai-search":
        return {
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "function": event.get("function", ""),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": "Invalid data."
                        }
                    }
                }
            },
            "messageVersion": event.get("messageVersion", "1.0")
        }

    parameters = event.get("parameters", [])
    search_query = next((p["value"] for p in parameters if p["name"] == "search_query"), None)
    target_website = next((p["value"] for p in parameters if p["name"] == "target_website"), "")

    if not search_query:
        return {
            "response": {
                "actionGroup":  event.get("actionGroup", ""),
                "function": "tavily-ai-search",
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": "Missing required parameter: search_query"
                        }
                    }
                }
            },
            "messageVersion": event.get("messageVersion", "1.0")
        }

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": search_query,
        "search_depth": "advanced",
        "include_answer": True,
        "max_results": 3,
    }

    if target_website:
        payload["include_domains"] = [target_website]

    try:
        req = urllib.request.Request(
            url="https://api.tavily.com/search",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as res:
            result = res.read().decode()

        return {
            "response": {
                "actionGroup":  event.get("actionGroup", ""),
                "function": "tavily-ai-search",
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": f"Top results for '{search_query}': {result}"
                        }
                    }
                }
            },
            "messageVersion": event.get("messageVersion", "1.0")
        }

    except Exception as e:
        return {
            "response": {
                "actionGroup":  event.get("actionGroup", ""),
                "function": "tavily-ai-search",
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": f"Tavily search failed: {str(e)}"
                        }
                    }
                }
            },
            "messageVersion": event.get("messageVersion", "1.0")
        }