import os
import json
import traceback
from chat_bot import *
from session import get_table_info

LLM_ENDPOINT_NAME = os.environ.get('llm_embedding_name')
REGION = os.environ.get('AWS_REGION')
LANGUAGE =  os.environ.get('language')

USER_TABLE_NAME =  os.environ.get('user_table_name')
ITEM_TABLE_NAME =  os.environ.get('item_table_name')

# user_table_name = 'PersonalizeStack-retailusertable9836B5C5-HKAHZW7IOMWF'
# item_table_name='PersonalizeStack-retailitemtable624AB3CD-DBBU6LWB5U3A'

system_content = "If you are a shopping guide of an e-commerce website, please generate product marketing advertising messages within 50 words for the user according to the user's information and shopping history, as well as the basic information of the product."


def lambda_handler(event, context):
    
    print("event:",event)
    print('user_table_name:',USER_TABLE_NAME)
    print('item_table_name:',ITEM_TABLE_NAME)    
    
    evt_body = event['queryStringParameters']
    
    userId = 1
    if "userId" in event.keys():
        userId = event['userId']
    elif "queryStringParameters" in event.keys():
        if "userId" in evt_body.keys():
            userId = evt_body['userId'].strip()

    itemIdList = ""
    if "itemIdList" in event.keys():
        itemIdList = event['itemIdList']
    elif "queryStringParameters" in event.keys():
        if "itemIdList" in evt_body.keys():
            itemIdList = evt_body['itemIdList'].strip()
        
    itemIdList=itemIdList.split(',')
    print('itemIdList:',itemIdList)

    itemInfoList = []
    for itemId in itemIdList:
        print('item_id:',itemId)
        itemInfo = get_table_info(ITEM_TABLE_NAME, itemId, 'item')
        print('item_info:',itemInfo)
        itemInfoList.append(itemInfo)
    print('item_info_list:',itemInfoList)

    userInfo = get_table_info(USER_TABLE_NAME, userId, 'user')
    print('user_info:',userInfo)
    userBase = userInfo['user_base']
    userHistory = userInfo['user_history']
    
    modelType = 'normal'
    if "modelType" in evt_body.keys():
        modelType = evt_body['modelType']
  
    urlOrApiKey = ''
    if "urlOrApiKey" in evt_body.keys():
        urlOrApiKey = evt_body['urlOrApiKey']
  
    modelName = 'anthropic.claude-v2'
    if "modelName" in evt_body.keys():
        modelName = evt_body['modelName']

    bedrockMaxTokens = 512
    if "bedrockMaxTokens" in evt_body.keys():
        bedrockMaxTokens = int(evt_body['bedrockMaxTokens'])
        
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
                         urlOrApiKey,
                         modelName,
                         bedrockMaxTokens
                         )
    
        itemAds = chat_bot.get_item_ads_llama2(
                                              REGION,
                                              itemInfoList,
                                              userBase,
                                              userHistory,
                                              system_content
                                              )
        print('item_ads:',itemAds)
        response = {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": '*'
            },
            "isBase64Encoded": False
        }
        
        response['body'] = json.dumps(
        {
            'item_ads':itemAds
        })
        return response

    except Exception as e:
        traceback.print_exc()
        return {
            'statusCode': 400,
            'body': str(e)
        }