import os
import json
from session import get_table_info

USER_TABLE_NAME =  os.environ.get('user_table_name')
ITEM_TABLE_NAME =  os.environ.get('item_table_name')

# user_table_name = 'PersonalizeStack-retailusertable9836B5C5-HKAHZW7IOMWF'
# item_table_name='PersonalizeStack-retailitemtable624AB3CD-DBBU6LWB5U3A'

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
        
    userInfo = get_table_info(USER_TABLE_NAME, userId, 'user')
    print('userInfo:',userInfo)
    userBase = userInfo['user_base']
    userHistory = userInfo['user_history']
    
    print('user_base:',userBase)
    print('user_history:',userHistory)
    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": '*'
        },
        "isBase64Encoded": False
    }
    
    response['body'] = json.dumps(
    {
        'user_base':userBase,
        'user_history':userHistory
    })
    return response