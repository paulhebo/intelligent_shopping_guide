import os
import json
import traceback
import urllib.parse
import boto3
from datetime import datetime
import time
from model import init_embeddings,init_vector_store
from chat_bot import *
from search_prompt import get_examples
from search_metadata import *
from langchain.vectorstores import MyScale,MyScaleSettings
from langchain.retrievers.self_query.base import SelfQueryRetriever

EMBEDDING_ENDPOINT_NAME = os.environ.get('embedding_endpoint_name')
LLM_ENDPOINT_NAME = os.environ.get('llm_embedding_name')
region = os.environ.get('AWS_REGION')
INDEX =  os.environ.get('index')
host =  os.environ.get('host')
LANGUAGE =  os.environ.get('language')
port = 443

response = {
    "statusCode": 200,
    "headers": {
        "Access-Control-Allow-Origin": '*'
    },
    "isBase64Encoded": False
}

def get_retriever(database,vector_store,region,
                 sagemakerEndpoint: str = 'pytorch-inference-llm-v1',
                 temperature: float = 0.01,
                 modelType:str = "normal",
                 apiUrl:str = "",
                 modelName:str="anthropic.claude-v2",
                 apiKey:str = "",
                 secretKey:str = "",
                 maxTokens:int=512,
                 ):
                        
    metadata_field_info = get_metadata_field_info(database)
    document_content_description = get_document_content_description()
    
    chain_kwargs = {}
    chain_kwargs["examples"]=get_examples(database)
    chat_bot = ShoppingGuideChatBot()
    chat_bot.init_cfg(
                     region,
                     sagemakerEndpoint,
                     temperature,
                     modelType,
                     apiUrl,
                     modelName,
                     apiKey,
                     secretKey,
                     maxTokens
                     )
    
    retriever = SelfQueryRetriever.from_llm(
        chat_bot.get_llm(), vector_store, document_content_description, metadata_field_info,
        chain_kwargs=chain_kwargs,
        verbose=True
    )
    return retriever

def lambda_handler(event, context):
    
    print("event:",event)
    print('host',host)
    
    evt_body = event['queryStringParameters']
    
    query = "hello"
    if "query" in evt_body.keys():
        query = evt_body['query'].strip()
    print('query:',query)

    vectorDatabase = 'opensearch'
    if "vectorDatabase" in evt_body.keys():
        vectorDatabase = evt_body['vectorDatabase']
    print('vectorDatabase:',vectorDatabase)
    
    if vectorDatabase == 'opensearch':
        index = INDEX
        if "index" in evt_body.keys():
            index = evt_body['index']
        print('index:',index)
        
        searchType = 'vector'
        if "searchType" in evt_body.keys():
            searchType = evt_body['searchType']
        print('searchType:',searchType)
        
    elif vectorDatabase == 'myscale':
        myscaleHost = ''
        if "myscaleHost" in evt_body.keys():
            myscaleHost = evt_body['myscaleHost']
        print('myscaleHost:',myscaleHost)
        
        myscalePort = ''
        if "myscalePort" in evt_body.keys():
            myscalePort = evt_body['myscalePort']
        print('myscalePort:',myscalePort)
        
        myscaleUsername = ''
        if "myscaleUsername" in evt_body.keys():
            myscaleUsername = evt_body['myscaleUsername']
        print('myscaleUsername:',myscaleUsername)
        
        myscalePassword = ''
        if "myscalePassword" in evt_body.keys():
            myscalePassword = evt_body['myscalePassword']
        print('myscalePassword:',myscalePassword)
    
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
    
    
    modelType = 'bedrock'
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
    
    embeddings = init_embeddings(embeddingEndpoint,region,language= LANGUAGE)
    if vectorDatabase == 'opensearch':
        #1.get item info
        sm_client = boto3.client('secretsmanager')
        master_user = sm_client.get_secret_value(SecretId='opensearch-master-user')['SecretString']
        data= json.loads(master_user)
        username = data.get('username')
        password = data.get('password')
        vector_store=init_vector_store(embeddings,index,host,port,username,password)
        
        if searchType == 'vector':
            docs = vector_store.similarity_search(query,k=topK)
        elif searchType == 'selfQuery':
            retriever = get_retriever(vectorDatabase,vector_store,
                                         region,
                                         sagemakerEndpoint,
                                         temperature,
                                         modelType,
                                         apiUrl,
                                         modelName,
                                         apiKey,
                                         secretKey,
                                         maxTokens
                                     )
            docs = retriever.get_relevant_documents(query,k=topK)
    elif vectorDatabase == 'myscale':
        scaleSettings = MyScaleSettings(host=myscaleHost,port=myscalePort,username=myscaleUsername,password=myscalePassword)
        vector_store = MyScale(embeddings,config=scaleSettings)
        retriever = get_retriever(vectorDatabase,vector_store,
                                     region,
                                     sagemakerEndpoint,
                                     temperature,
                                     modelType,
                                     apiUrl,
                                     modelName,
                                     apiKey,
                                     secretKey,
                                     maxTokens
                                  )
        docs = retriever.get_relevant_documents(query,k=topK)
    
    print('docs:',docs)
    item_metadatas = [doc.metadata for doc in docs]
    print('item_metadatas:',item_metadatas)
    
    item_id_list = []
    for metadata in item_metadatas:
        item_id_list.append(metadata[idKey])
    
    item_info_dict = item_metadatas
    if len(itemFilterId) > 0:
        item_filter_id_list = itemFilterId.split(',')
        if len(list(set(item_id_list)-set(item_filter_id_list))) == 0:
            item_id_list = []
            item_info_dict = {}
        else:
            item_id_list, item_info_dict = zip(*((item_id, item_info) for item_id, item_info in zip(item_id_list, item_metadatas) if item_id not in item_filter_id_list))
    
    print('items_info:',item_info_dict)
    
    response['body'] = json.dumps(
    {
        'items_id': item_id_list,
        'items_info': item_info_dict
    })
    
    return response
