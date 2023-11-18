import os
import shutil
from langchain.prompts.prompt import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.llms import AmazonAPIGatewayBedrock
import json

import boto3
import json
import os

from model import *
from session import *

def get_history(session_id,table_name):
    history = []
    session_info = ""
    if len(session_id) > 0 and len(table_name) > 0:
        session_info = get_session_info(table_name,session_id)
        if len(session_info) > 0:
            for item in session_info:
                print("session info:",item[0]," ; ",item[1]," ; ",item[2])
                if item[2] == "chat":
                    history.append((string_processor(item[0]),string_processor(item[1])))
    return history


class ShoppingGuideChatBot:
    
    def init_cfg(self,
                 region,
                 llm_endpoint_name: str = 'pytorch-inference-llm-v1',
                 temperature: float = 0.01,
                 model_type:str = "normal",
                 bedrock_api_url:str = "",
                 bedrock_model_id:str="anthropic.claude-v2",
                 bedrock_max_tokens:int=500
                ):
                    
        if model_type == "llama2":
            self.llm = init_model_llama2(llm_endpoint_name,region,temperature)
        elif model_type == "bedrock_api":
            self.llm = AmazonAPIGatewayBedrock(api_url=bedrock_api_url)
            parameters={
                "modelId":bedrock_model_id,
                "max_tokens":bedrock_max_tokens,
                "temperature":temperature
            }
            self.llm.model_kwargs = parameters
        elif model_type == "bedrock":
            self.llm = init_model_bedrock(bedrock_model_id)
            parameters={
                "max_tokens":bedrock_max_tokens,
                "temperature":temperature
            }
            self.llm.model_kwargs = parameters
            
        else:
            self.llm = init_model(llm_endpoint_name,region,temperature)
            
    def get_chat(self,query,
                      task: str='chat',
                      prompt_template: str='',
                      session_id: str='',
                      table_name: str='',
                      items_info: str=''
                ):
                    
        if task == 'chat':    
            prompt = PromptTemplate(
                input_variables=["question"], 
                template=prompt_template
            )
            history = get_history(session_id,table_name)
            his_query = ''
            if len(history) > 0:
                for (question,answer) in history:
                    if question != query:
                        his_query += (question+',') 
            print('his_query:',his_query)
            query = string_processor(query)
            if len(his_query) > 0:
                query = his_query + query  

        elif task == 'summary':
            prompt = PromptTemplate(
                input_variables=["items_info","question"], 
                template=prompt_template
            )
 
        print('query:',query)
        
        chat_chain = LLMChain(
            llm=self.llm,
            prompt=prompt, 
            # verbose=True, 
            # memory=memory,
        )
            
        if task == 'chat':   
            output = chat_chain.predict(question=combine_query)
        elif task == 'summary':
            output = chat_chain.predict(question=combine_query,items_info=items_info)
        
        if len(session_id) > 0 and len(query) > 0:
            chat_result = output
            if task == 'chat' and output.find('@') > 0:
                chat_result = output.split('@')[1].replace('</answer>','').strip()
            update_session_info(table_name, session_id, query, chat_result, "chat")
        
        return output



    def get_chat_llama2(self,query,
                        task: str='chat',
                        prompt_template: str='',
                        session_id: str='',
                        table_name: str=''
                       ):
    
        history = get_history(session_id,table_name)
        
        if task == 'chat':
            query = string_processor(query)
        else:
            his_query = ''
            if len(history) > 0:
                for (question,answer) in history:
                    his_query += (question+',')
            query = his_query + string_processor(query)
            query = LLAMA2_SUMMARIZE_CHAT_TEMPLATE.format(query)
            history = []
            
        prompt={
            'system_content':string_processor(prompt_template),
            'query':string_processor(query),
            'history':history
        }
    
        prompt_str = json.dumps(prompt)
        response = self.llm.predict(prompt_str)
        
        if len(session_id) > 0 and task == 'chat':
            update_session_info(table_name, session_id, query, response, "chat")
        
        return response
        
    def get_item_ads_llama2(self,
                           region,
                           item_info_list,
                           user_base,
                           user_history,
                           system_content
                          ):
        
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
        response = self.llm.predict(prompt_str)
        return response