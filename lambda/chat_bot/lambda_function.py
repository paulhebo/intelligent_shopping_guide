import os
import json
import traceback
import urllib.parse
from datetime import datetime
import time
from chat_bot import *
from prompt import *

LLM_ENDPOINT_NAME = os.environ.get('llm_endpoint_name')
TABLE_NAME = os.environ.get('dynamodb_table_name')
REGION = os.environ.get('AWS_REGION')
LANGUAGE =  os.environ.get('language')

response = {
    "statusCode": 200,
    "headers": {
        "Access-Control-Allow-Origin": '*'
    },
    "isBase64Encoded": False
}

def lambda_handler(event, context):
    
    print("event:",event)
    print('table name:',TABLE_NAME)

    evt_body = event['queryStringParameters']

    query = "hello"
    if "query" in evt_body.keys():
        query = evt_body['query'].strip()
    print('query:',query)
    
    task = "chat"
    if "task" in evt_body.keys():
        task = evt_body['task'].strip()
    print('task:',task)
    
    sessionId=""
    if "sessionId" in evt_body.keys():
        sessionId = str(evt_body['sessionId'])
    print('sessionId:',sessionId)
    
    modelType = 'normal'
    if "modelType" in evt_body.keys():
        modelType = evt_body['modelType']
  
    apiUrl = ''
    if "apiUrl" in evt_body.keys():
        apiUrl = evt_body['apiUrl']
  
    apiKey = ''
    if "apiKey" in evt_body.keys():
        apiKey = evt_body['apiKey']

    secretKey = ''
    if "secretKey" in evt_body.keys():
        secretKey = evt_body['secretKey']

    modelName = 'anthropic.claude-v2'
    if "modelName" in evt_body.keys():
        modelName = evt_body['modelName']

    maxTokens = 512
    if "maxTokens" in evt_body.keys():
        maxTokens = int(evt_body['maxTokens'])
        
    sagemakerEndpoint = LLM_ENDPOINT_NAME
    if "sagemakerEndpoint" in evt_body.keys():
        sagemakerEndpoint = evt_body['sagemakerEndpoint']
    
    temperature = 0.01
    if "temperature" in evt_body.keys():
        temperature = float(evt_body['temperature'])
    
    language=LANGUAGE
    if "language" in evt_body.keys():
        language = evt_body['language']
    
    try:
        chat_bot = ShoppingGuideChatBot()
        chat_bot.init_cfg(
                         REGION,
                         sagemakerEndpoint,
                         temperature,
                         modelType,
                         apiUrl,
                         modelName,
                         apiKey,
                         secretKey,
                         maxTokens
                         )
    
        query = "hello"
        if "query" in evt_body.keys():
            query = evt_body['query'].strip()
        print('query:', query)
    
        prompt_template = get_prompt_template(language,modelType,task)
                    
        if "prompt" in evt_body.keys():
            prompt_template = evt_body['prompt']  
            
        itemsInfo = ''    
        if "itemsInfo" in evt_body.keys():
            itemsInfo = evt_body['itemsInfo'] 

        if modelType == 'llama2':
            result = chat_bot.get_chat_llama2(query,task,prompt_template,sessionId,TABLE_NAME)
        else:
            result = chat_bot.get_chat(query,task,prompt_template,sessionId,TABLE_NAME,itemsInfo)
    
        print('chat_result:',result)
        
        response['body'] = json.dumps(
        {
            'answer': result
        })
        return response

    except Exception as e:
        traceback.print_exc()
        return {
            'statusCode': 400,
            'body': str(e)
        }