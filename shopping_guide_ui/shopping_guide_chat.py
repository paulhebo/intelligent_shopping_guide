import streamlit as st
import os
import requests
import json
from datetime import datetime
import pandas as pd

#replace the parameter value
chat_bot_invoke_url = "https://ycmrma41ki.execute-api.us-east-1.amazonaws.com/prod"
personalize_ranking_invoke_url = 'https://pcoostqf64.execute-api.us-east-1.amazonaws.com/prod'
product_search_invoke_url = 'https://ogyc7g1oo3.execute-api.us-east-1.amazonaws.com/prod'
user_info_url = 'https://nyvd42lj7g.execute-api.us-east-1.amazonaws.com/prod'
ads_invoke_url = "https://fbuwtnrb0l.execute-api.us-east-1.amazonaws.com/prod"

index = "retail_product_index_demo_1120_2"
language = 'english'

llm_endpoint_name = 'meta-textgeneration-llama-2-7b-f-2023-11-20-03-32-01-706'
embedding_endpoint_name = 'huggingface-inference-eb-minilm'

USER_TABLE_NAME =  'AdsStack-retailusertable9836B5C5-YB0MVPDGW41E'
# ITEM_TABLE_NAME =  'AdsStack-retailitemtable624AB3CD-1FIOS91JDVJ5S'

# App title
st.set_page_config(page_title="aws intelligent search solution")

def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    st.session_state.sessionId = 'ir'+str(timestamp)
    st.session_state.searchItemId = []

def get_user_info(user_id):

    url = user_info_url
    url += ('/user_info?userId='+str(user_id))
    url += ('&userTableName='+USER_TABLE_NAME)
    print('get_user_info url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    
    print('user info result:',result)

    user_base = result['user_base']
    user_history = result['user_history']

    user_age = user_base['age']
    user_gender = user_base['gender']
    user_info = 'User info: ' + str(user_age) + ' years old, ' + user_gender + ';'
    user_history_df = pd.DataFrame(user_history)
    st.write(user_info)
    st.write('User behavior history:')
    st.dataframe(user_history_df,
                 column_order=('category_2','price','event_type'),
                 column_config={'category_1':'category 1','category_2':'category 2'})

with st.sidebar:
    st.title('AWS Intelligent Shopping Guide Solution')
    # st.subheader('Models and parameters')
    # model = st.radio("Choose a model",('llama2', 'chatgpt'))
    model = 'llama2'

    # st.write("### Choose a User")
    user_id = st.slider('Select a user ID:', 1, 6000, 1)
    if st.sidebar.button('Get user information'):
        get_user_info(user_id)

    # st.write("### Choose the number of conversation rounds to make search")
    step = st.radio("Choose the number of conversation rounds to make search",('2','3','4','5'))
    item_num = st.slider('Select the number of recommended items:', 1, 3, 1)
    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)



st.write("## Just For You")

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "Hello,How may I assist you today?"}]
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    st.session_state.sessionId = 'ir'+str(timestamp)
    st.session_state.searchItemId = []

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])



# Function for generating LLaMA2 response
def get_chat(prompt,task,top_k=1):
    url = chat_bot_invoke_url
    url += ('/chat_bot?query='+prompt)
    url += ('&task='+task)
    url += ('&sessionId='+st.session_state.sessionId)
    url += ('&language='+language)
    url += ('&modelType='+model)
    url += ('&top_k='+str(top_k))
    url += ('&sagemakerEndpoint='+llm_endpoint_name)

    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    
    print('chat result:',result)
    answer = result['answer']
    return answer


def get_products(query,top_k=1,filter_item_id=[]):
    
    url = product_search_invoke_url
    url += ('/product_search?query='+query)
    url += ('&index='+index)
    url += ('&topK='+str(top_k))
    if len(filter_item_id) > 0:
        url += ('&itemFilterId='+','.join(filter_item_id))
    url += ('&embeddingEndpoint='+embedding_endpoint_name)
    url += ('&idKey=id')

    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    
    print('product result:',result)
    products = result['items_info']
    items_id = result['items_id']
    top_item_ids_str = ','.join(items_id)


    image_path_list = []
    item_id_list = []
    if len(products) > 0:
        for product in products:
            category = product['category']
            image = product['image']
            image_path = 'https://d3j4fy1ccpxvdd.cloudfront.net/'+category+'/'+image
            image_path_list.append(image_path)
            item_id_list.append(product['id'])
        # product_ad_str = result['ad_response']
    return top_item_ids_str,image_path_list,item_id_list

def get_item_ads(top_item_ids_str,user_id=1):

    url = ads_invoke_url +'/get_item_ads?'
    url += ('itemIdList='+top_item_ids_str)
    url += ('&userId='+str(user_id))
    url += ('&sagemakerEndpoint='+llm_endpoint_name)
    url += ('&modelType='+model)
    url += ('&language='+language)
    # url += ('&itemTable='+ITEM_TABLE_NAME)
    # url += ('&userTable='+USER_TABLE_NAME)

    print('get_item_ads url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    
    print('ads result:',result)
    ads_response = result['item_ads']
    return ads_response

def item_ads_processor(item_ad):
    return item_ad.split('\n\n')[1]

# User-provided prompt
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            task = "chat"
            if len(st.session_state.messages) >= int(step)*2:
                task = 'summarize'
            placeholder = st.empty()
            # try:
            if task == "chat":
                response = get_chat(prompt,task)
                placeholder.markdown(response)
            elif task == 'summarize':
                answer = get_chat(prompt,task)
                print('intention:',answer)
                top_item_ids_str,image_path_list,item_id_list = get_products(answer,top_k=3,filter_item_id=st.session_state.searchItemId)
                st.session_state.searchItemId.extend(item_id_list)
                item_ads = get_item_ads(top_item_ids_str,user_id=user_id)
                if item_ads.find('Commodity') > 0:
                    item_ads_list = item_ads.split('Commodity')
                elif item_ads.find('Product') > 0:
                    item_ads_list = item_ads.split('Product')
                
                print("item_ads_list len:",len(item_ads_list))
                print("image_path_list len:",len(image_path_list))
                if item_num == 3:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                       st.write(item_ads_processor(item_ads_list[1]))
                       # image0 = Image.open(image_path_list[0])
                       st.image(image_path_list[0])
                       st.write('http://d2qogd6e3vaci5.cloudfront.net/#/product/'+item_id_list[0])

                    with col2:
                       st.write(item_ads_processor(item_ads_list[2]))
                       # image1 = Image.open(image_path_list[1])
                       st.image(image_path_list[1])
                       st.write('http://d2qogd6e3vaci5.cloudfront.net/#/product/'+item_id_list[1])

                    with col3:
                       st.write(item_ads_processor(item_ads_list[3]))
                       # image2 = Image.open(image_path_list[2])
                       st.image(image_path_list[2])
                       st.write('http://d2qogd6e3vaci5.cloudfront.net/#/product/'+item_id_list[2])
                elif item_num ==2:
                    col1, col2 = st.columns(2)
                    with col1:
                       st.write(item_ads_processor(item_ads_list[1]))
                       # image0 = Image.open(image_path_list[0])
                       st.image(image_path_list[0])
                       st.write('http://d2qogd6e3vaci5.cloudfront.net/#/product/'+item_id_list[0])
                    with col2:
                       st.write(item_ads_processor(item_ads_list[2]))
                       # image1 = Image.open(image_path_list[1])
                       st.image(image_path_list[1])
                       st.write('http://d2qogd6e3vaci5.cloudfront.net/#/product/'+item_id_list[1])
                elif item_num ==1:
                   st.write(item_ads_processor(item_ads_list[1]))
                   st.image(image_path_list[0])
                   st.write('http://d2qogd6e3vaci5.cloudfront.net/#/product/'+item_id_list[0])
                else:
                    st.write("Sorry, We can't find that product!")
                response = item_ads_processor(item_ads_list[1])


            # except:
            #     placeholder.markdown("Sorry,please try again!")
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)
