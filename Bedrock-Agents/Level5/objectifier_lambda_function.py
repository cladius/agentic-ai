import json
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Processing event: {event}")
    try:
        # Navigate to the stringified JSON in the input
        value_str = event['node']['inputs'][0]['value']a
        
        # Parse the string into a JSON object
        result = json.loads(value_str)        
        return result
    
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return {
            "error": f"Failed to process input: {str(e)}"
        }