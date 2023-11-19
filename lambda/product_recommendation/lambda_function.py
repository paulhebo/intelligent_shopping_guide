import os
import json
import traceback
import urllib.parse
import boto3
from datetime import datetime
import time
from model import init_embeddings,init_vector_store
from chat_bot import *
from prompt import *

EMBEDDING_ENDPOINT_NAME = os.environ.get('embedding_endpoint_name')
LLM_ENDPOINT_NAME = os.environ.get('llm_embedding_name')
region = os.environ.get('AWS_REGION')
INDEX =  os.environ.get('index')
host =  os.environ.get('host')
LANGUAGE =  os.environ.get('language')
port = 443
lambda_client = boto3.client('lambda')

response = {
    "statusCode": 200,
    "headers": {
        "Access-Control-Allow-Origin": '*'
    },
    "isBase64Encoded": False
}

def lambda_handler(event, context):
    
    print("event:",event)
    print('host',host)
    
    evt_body = event['queryStringParameters']
    
    query = "hello"
    if "query" in evt_body.keys():
        query = evt_body['query'].strip()
    print('query:',query)

    
    index = INDEX
    if "index" in evt_body.keys():
        index = evt_body['index']
    print('index:',index)
    
    embeddingEndpoint = EMBEDDING_ENDPOINT_NAME
    if "embeddingEndpoint" in evt_body.keys():
        embeddingEndpoint = evt_body['embeddingEndpoint']
    
    itemFilterId = ''
    if "itemFilterId" in evt_body.keys():
        itemFilterId = evt_body['itemFilterId']
    print('itemFilterId:',itemFilterId)
    
    idKey = 'item_id'
    if "idKey" in evt_body.keys():
        idKey = evt_body['idKey']
    print('idKey:',idKey)
    
    topK = 3
    if "topK" in evt_body.keys():
        topK = int(evt_body['topK'])
    print('topK:',topK)
    
    #1.get item info
    sm_client = boto3.client('secretsmanager')
    master_user = sm_client.get_secret_value(SecretId='opensearch-master-user')['SecretString']
    data= json.loads(master_user)
    username = data.get('username')
    password = data.get('password')

    embeddings = init_embeddings(embeddingEndpoint,region,language= LANGUAGE)
    vector_store=init_vector_store(embeddings,index,host,port,username,password)
    
    print('query:',query)
    docs = vector_store.similarity_search_with_score(query.replace('@@@',','),k=topK)
    
    item_metadatas = [doc[0].metadata for doc in docs]
    print('item_metadatas:',item_metadatas)
    
    item_info_list = []
    item_id_list = []
    for metadata in item_metadatas:
        item_info = ''
        for key in metadata.keys():
            item_info += (key+':='+metadata[key]+'\n')
        item_info_list.append('<apartment>'+item_info+'</apartment>')
        item_id_list.append(metadata[idKey])
    
    if len(itemFilterId) > 0:
        item_filter_id_list = itemFilterId.split(',')
        item_id_list, item_info_list = zip(*((item_id, item_info) for item_id, item_info in zip(item_id_list, item_info_list) if item_id not in item_filter_id_list))
        
    items_info = '\n\n'.join(item_info_list)
    print('items_info:',items_info)
    
    response['body'] = json.dumps(
    {
        'items_info': items_info
    })
    
    return response
