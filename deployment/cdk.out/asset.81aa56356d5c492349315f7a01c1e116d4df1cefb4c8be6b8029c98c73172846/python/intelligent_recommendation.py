from langchain import PromptTemplate, SagemakerEndpoint
from langchain.llms.sagemaker_endpoint import LLMContentHandler
from langchain.embeddings.sagemaker_endpoint import EmbeddingsContentHandler
from langchain.embeddings import SagemakerEndpointEmbeddings
from typing import Optional, List, Any, Dict
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.utils import enforce_stop_tokens
from langchain.vectorstores import OpenSearchVectorSearch
import boto3
import json
from langchain.llms import OpenAI
import os

def string_processor(string):
    return string.replace('\n','').replace('"','').replace('“','').replace('”','').strip()


def new_call(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> str:
    _model_kwargs = self.model_kwargs or {}
    _model_kwargs = {**_model_kwargs, **kwargs}
    _endpoint_kwargs = self.endpoint_kwargs or {}

    body = self.content_handler.transform_input(prompt, _model_kwargs)
    content_type = self.content_handler.content_type
    accepts = self.content_handler.accepts

    # send request
    try:
        response = self.client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            Body=body,
            ContentType=content_type,
            Accept=accepts,
            CustomAttributes='accept_eula=true',  # Added this line
            **_endpoint_kwargs,
        )
    except Exception as e:
        raise ValueError(f"Error raised by inference endpoint: {e}")

    text = self.content_handler.transform_output(response["Body"])
    if stop is not None:
        text = enforce_stop_tokens(text, stop)

    return text

# Monkey patch the class
SagemakerEndpoint._call = new_call

class LLamaContentHandler(LLMContentHandler):
    def __init__(self, parameters):
        self.parameters = parameters
    
    @property
    def content_type(self):
        return "application/json"
    
    @property
    def accepts(self):
        return "application/json"
    
    def transform_input(self, prompt: str, model_kwargs: dict):
        system_content = "You are a helpful assistant."
        history = []
        query = ''
        prompt = json.loads(prompt)
        if 'system_content' in prompt.keys():
            system_content = prompt['system_content']
        if 'history' in prompt.keys():
            history = prompt['history']
        if 'query' in prompt.keys():
            query = prompt['query']

        inputs='{"role": "system", "content":"'+ system_content + '"},'
        if len(history) > 0:
            for (question,answer) in history:
                inputs += '{"role": "user", "content":"'+ question + '"},'
                inputs += '{"role": "assistant", "content":"'+ answer + '"},'
        
        inputs += '{"role": "user", "content":"'+ query + '"}'
        payload = '{"inputs": [['+ inputs+']],"parameters":'+str(self.parameters)+' }'
        print('payload:',payload)
        return payload
        
        
    def transform_output(self, response_body):
        # Load the response
        output = json.load(response_body)

        # Extract the 'content' value where the 'role' is 'assistant'
        user_response = next((item['generation']['content'] for item in output if item['generation']['role'] == 'assistant'), '')
        return user_response
    
def get_session_info(table_name, session_id):

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    session_result = ""
    response = table.get_item(Key={'session-id': session_id})
    if "Item" in response.keys():
        session_result = json.loads(response["Item"]["content"])
    else:
        session_result = ""

    return session_result
    
    
def update_session_info(table_name, session_id, question, answer, intention):

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    session_result = ""

    response = table.get_item(Key={'session-id': session_id})

    if "Item" in response.keys():
        chat_history = json.loads(response["Item"]["content"])
    else:
        chat_history = []

    chat_history.append([question, answer, intention])
    content = json.dumps(chat_history)

    response = table.put_item(
        Item={
            'session-id': session_id,
            'content': content
        }
    )

    if "ResponseMetadata" in response.keys():
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            update_result = "success"
        else:
            update_result = "failed"
    else:
        update_result = "failed"

    return update_result
    
    
def init_llm_sagemaker(endpoint_name,region):
    
    content_handler = LLamaContentHandler(parameters={})
    llm=SagemakerEndpoint(
            endpoint_name=endpoint_name, 
            region_name=region, 
            model_kwargs={"parameters": {"max_new_tokens": 512, "top_p": 0.9, "temperature": 0.01}},
            content_handler=content_handler,
    )
    return llm
    
def init_llm_openai(openai_api_key):
    llm = OpenAI(openai_api_key=openai_api_key)
    return llm

def get_history(session_id,table_name):
    history = []
    session_info = ""
    if len(session_id) > 0 and len(table_name) > 0:
        session_info = get_session_info(table_name,session_id)
        if len(session_info) > 0:
            for item in session_info:
                print("session info:",item[0]," ; ",item[1]," ; ",item[2])
                if item[2] == "qa_itention":
                    history.append((string_processor(item[0]),string_processor(item[1])))
    return history

def get_user_intention_sagemaker(endpoint_name,
                            region,
                            task: str='chat',
                            system_content: str='',
                            session_id: str='',
                            table_name: str='',
                            query: str=''
                           ):

    llm = init_llm_sagemaker(endpoint_name,region)
    history = get_history(session_id,table_name)
    
    if task == 'chat':
        query = string_processor(query)
    else:
        his_query = ''
        if len(history) > 0:
            for (question,answer) in history:
                his_query += (question+',')
        query = his_query + string_processor(query)
        query = "user's shopping demand are:" + query + "what is user's shopping intention? only simply output information about the user's shopping intention"
        history = []
        
    prompt={
        'system_content':system_content,
        'query':query,
        'history':history
    }

    prompt_str = json.dumps(prompt)
    response = llm.predict(prompt_str)
    
    if len(session_id) > 0 and task == 'chat':
        update_session_info(table_name, session_id, query, response, "qa_itention")
    
    return response


    
def get_user_intention_openai(openai_api_key,
                            task: str='chat',
                            system_content: str='You are a helpful assistant.',
                            session_id: str='',
                            table_name: str='',
                            query: str=''
                           ):
    
    llm = init_llm_openai(openai_api_key)
    question_list,answer_list = get_history(session_id,table_name)
    
    if task == 'chat':
        prompt = system_content + '\n'
        if len(question_list) > 0 and len(answer_list) > 0:
            prompt += ('history:'+'\n'+'======='+'\n')
            for i in range(len(question_list)):
                prompt +=('user:'+question_list[i]+'\n')
                prompt +=('assistant answer:'+answer_list[i]+'\n')
            prompt += '======='+'\n'
        prompt += 'user new qusetion:'+query+'\n'
        prompt += 'Assistant answer:'
        question_list.append(query)
    elif task == 'summarize':
        question_list.append(query)
        prompt = system_content + '\n'
        if len(question_list) > 0:
            prompt += ('history:'+'\n'+'======='+'\n'+'user question:')
            for i in range(len(question_list)):
                prompt += question_list[i]
                if i == len(question_list) -1:
                    prompt += '.'
                else:
                    prompt += ','
            prompt += ('\n'+'======='+'\n'+'Answer:')
    elif task == 'generate':
        prompt = system_content + '\n'
        if len(question_list) > 0:
            prompt += ('======='+'\n'+'user question:')
            for i in range(len(question_list)):
                prompt += question_list[i]
                if i == len(question_list) -1:
                    prompt += '.'
                else:
                    prompt += ','
            prompt += ('======='+'\n'+'Answer:')
            
    print('prompt:',prompt)
    response = llm.predict(prompt)
    
    if len(session_id) > 0 and task == 'chat':
        update_session_info(table_name, session_id, query, response, "qa_itention")
        
    return response


def init_embeddings(endpoint_name,region_name,language: str = "english"):
    
    class ContentHandler(EmbeddingsContentHandler):
        content_type = "application/json"
        accepts = "application/json"

        def transform_input(self, inputs: List[str], model_kwargs: Dict) -> bytes:
            input_str = json.dumps({"inputs": inputs, **model_kwargs})
            return input_str.encode('utf-8')

        def transform_output(self, output: bytes) -> List[List[float]]:
            response_json = json.loads(output.read().decode("utf-8"))
            if language.find("chinese")>=0:
                return response_json[0][0]
            elif language == "english":
                return response_json

    content_handler = ContentHandler()

    embeddings = SagemakerEndpointEmbeddings(
        endpoint_name=endpoint_name, 
        region_name=region_name, 
        content_handler=content_handler
    )
    return embeddings
    
def init_vector_store(embeddings,
             index_name,
             opensearch_host,
             opensearch_port,
             opensearch_user_name,
             opensearch_user_password):

    vector_store = OpenSearchVectorSearch(
        index_name=index_name,
        embedding_function=embeddings, 
        is_aoss=False,
        opensearch_url="aws-opensearch-url",
        hosts = [{'host': opensearch_host, 'port': opensearch_port}],
        http_auth = (opensearch_user_name, opensearch_user_password),
    )
    return vector_store
    
def get_table_info(table_name, index, table_type):

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    session_result = ""
    if table_type=='user':
        key='user_id'
    elif table_type=='item':
        key='item_id'
    response = table.get_item(Key={key: index})
    if "Item" in response.keys():
        session_result = json.loads(response["Item"]["content"])
    else:
        session_result = ""

    return session_result    
    
def get_item_ads_sagemaker(endpoint_name,
                          region,
                          item_info_list,
                          user_base,
                          user_history,
                          system_content
                          ):
    llm = init_llm_sagemaker(endpoint_name,region)
    
    age = user_base['age']
    gender = user_base['gender']
    user_base_info = 'user age:'+str(age)+',gender:'+gender+';'
    
    history_item_info = "user's shopping history:"
    for item in user_history:
        category_2 = item['category_2']
        product_description = item['product_description']
        price = item['price']
        history_item_info += ('The '+ category_2 + ',' + product_description + ',the price is ' + str(price) + ';')
        # history_item_info += ('a '+ category_2 + ',')
    system_content += (user_base_info + history_item_info)
    
    item_info = ''
    i = 0
    for item in item_info_list:
        category_2=item['category_2']
        product_description=item['product_description']
        price=item['price']
        i += 1
        item_info += ('Commodity ' + str(i) + ':the' + category_2 + ',' + product_description + ',the price is ' + str(price) + ';')
    
    query="Based on the user's shopping history,Please create advertising messages for each of the following 3 products, each product advertising message is within 200 words."    
    query += item_info
    prompt={
        'system_content':string_processor(system_content),
        'query':string_processor(query)
    }
    prompt_str = json.dumps(prompt)
    response = llm.predict(prompt_str)
    return response