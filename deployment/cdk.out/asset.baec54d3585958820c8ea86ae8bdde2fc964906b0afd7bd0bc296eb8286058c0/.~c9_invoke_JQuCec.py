import os
import json
import traceback
import urllib.parse
import boto3
from datetime import datetime
import time
from intelligent_recommendation import *

EMBEDDING_ENDPOINT_NAME = os.environ.get('embedding_endpoint_name')
LLM_ENDPOINT_NAME = os.environ.get('llm_embedding_name')
table_name = os.environ.get('dynamodb_table_name')
region = os.environ.get('AWS_REGION')
openai_api_key = os.environ.get('openai_api_key')
INDEX =  os.environ.get('index')
HOST =  os.environ.get('host')
LANGUAGE =  os.environ.get('language')


chat_system_content="You are an assistant for an e-commerce website, and your task is to collect users' shopping needs. Given the conversation between the following customers and the e-commerce website assistant and their subsequent input, ask the user questions based on their current needs. You can ask questions about the brand, functionality, or price of the product.Do not directly recommend products to users,Just ask users for their shopping needs."

summarize_system_content="Give users questions about what they want to buy, Simply summarize user needs from aspects such as product name, function, size, and price, do not directly recommend products to users, only simply output information about the user needs"


def lambda_handler(event, context):
    
    print("event:",event)

    query = "hello"
    if "query" in event['queryStringParameters'].keys():
        query = event['queryStringParameters']['query'].strip()    
    
    task = "chat"
    if "task" in event['queryStringParameters'].keys():
        task = event['queryStringParameters']['task'].strip()      
    
    if task == 'chat':
        system_content = chat_system_content
    elif task == 'summarize':
        system_content = summarize_system_content
        
    session_id=""
    if "session_id" in event['queryStringParameters'].keys():
        session_id = str(event['queryStringParameters']['session_id'])
    
    llm_modle = "llama2"
    if "llm_modle" in event['queryStringParameters'].keys():
        llm_modle = event['queryStringParameters']['llm_modle'].strip()    
    
    if llm_modle == "llama2":
        llm_embedding_name=LLM_ENDPOINT_NAME
        if "llm_embedding_name" in event['queryStringParameters'].keys():
            llm_embedding_name = event['queryStringParameters']['llm_embedding_name']
            
        question_list,answer_list = get_user_intention_sagemaker(llm_embedding_name,
                                                                 region,
                                                                 task=task,
                                                                 system_content=system_content,
                                                                 session_id=session_id,
                                                                 table_name=table_name,
                                                                 query=query)
    elif llm_modle == "chatgpt":
        response = get_user_intention_openai(openai_api_key,
                                     task=task,
                                     system_content=system_content,
                                     session_id=session_id,
                                     table_name=table_name,
                                     query=query)
        
    products = []
    if task == 'summarize':
        embedding_endpoint_name=EMBEDDING_ENDPOINT_NAME
        if "embedding_endpoint_name" in event['queryStringParameters'].keys():
            embedding_endpoint_name = event['queryStringParameters']['embedding_endpoint_name']
        
        collection_name = COLLECTION_NAME
        if "collection_name" in event['queryStringParameters'].keys():
            collection_name = event['queryStringParameters']['collection_name']
            
        milvus_host = MILVUS_HOST
        if "milvus_host" in event['queryStringParameters'].keys():
            milvus_host = event['queryStringParameters']['milvus_host']

        milvus_port = MILVUS_PORT
        if "milvus_port" in event['queryStringParameters'].keys():
            milvus_port = event['queryStringParameters']['milvus_port']

        
        embeddings = init_embeddings(embedding_endpoint_name,region,language= "english")
        
        vector_store = Milvus(embedding_function=embeddings,
                              collection_name   = collection_name,
                              connection_args   = {"host": milvus_host, "port": milvus_port},
                              consistency_level = "Strong"
                             )
        user_intention = answer_list[-1]
        print('user intention:',user_intention)
        docs = vector_store.similarity_search(user_intention)
        products = [doc.metadata for doc in docs]
        
    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": '*'
        },
        "isBase64Encoded": False
    }
    
    response['body'] = json.dumps(
    {
        'question_list': question_list,
        'answer_list': answer_list,
        'products': products,
    })
    return response