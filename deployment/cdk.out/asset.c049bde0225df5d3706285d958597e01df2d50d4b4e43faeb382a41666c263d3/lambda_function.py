import os
import json
import traceback
from chat_bot import *
from session import get_table_info
from prompt import get_prompt_template

LLM_ENDPOINT_NAME = os.environ.get('llm_embedding_name')
REGION = os.environ.get('AWS_REGION')
LANGUAGE =  os.environ.get('language')

USER_TABLE_NAME =  os.environ.get('user_table_name')
ITEM_TABLE_NAME =  os.environ.get('item_table_name')


def lambda_handler(event, context):
    
    print("event:",event)
    print('user_table_name:',USER_TABLE_NAME)
    print('item_table_name:',ITEM_TABLE_NAME)    
    
    evt_body = event['queryStringParameters']
    
    query = "hello"
    if "query" in evt_body.keys():
        query = evt_body['query'].strip()
    print('query:',query)    
    
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

    items_Info_text = ''
    if len(itemIdList) > 0:
        itemInfoList = []
        for itemId in itemIdList:
            print('item_id:',itemId)
            itemInfo = get_table_info(ITEM_TABLE_NAME, itemId, 'item')
            print('item_info:',itemInfo)
            itemInfoList.append(itemInfo)
        print('item_info_list:',itemInfoList)
        i = 0
        for item in itemInfoList:
            category_2=item['category_2']
            product_description=item['product_description']
            price=item['price']
            i += 1
            items_Info_text += ('Commodity ' + str(i) + ':the' + category_2 + ',' + product_description + ',the price is ' + str(price) + ';')
    else:
        if "itemInfo" in evt_body.keys():
            items_Info_text = evt_body['itemInfo']

    userInfo = get_table_info(USER_TABLE_NAME, userId, 'user')
    user_base_info = ''
    history_item_info = ''
    print('user_info:',userInfo)
    if len(userInfo) > 0:
        userBase = userInfo['user_base']
        userHistory = userInfo['user_history']
        age = userBase['age']
        gender = userBase['gender']
        user_base_info = 'user age:'+str(age)+',gender:'+gender+';'
        
        if len(userHistory) > 0:
            history_item_info = "user's shopping history:"
            for item in userHistory:
                category_2 = item['category_2']
                product_description = item['product_description']
                price = item['price']
                history_item_info += ('The '+ category_2 + ',' + product_description + ',the price is ' + str(price) + ';')
    
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
        if modelType == 'llama2':
            system_content = get_prompt_template(language,modelType,'ads-sys')
            query = get_prompt_template(language,modelType,'ads-chat')
            itemAds = chat_bot.get_item_ads_llama2(query,
                                                  item_Info_text,
                                                  user_base_info,
                                                  history_item_info,
                                                  system_content
                                                  )
        else:
            prompt_template = get_prompt_template(language,modelType,'ads')
            itemAds = chat_bot.get_item_ads(
                                      query,
                                      items_Info_text,
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