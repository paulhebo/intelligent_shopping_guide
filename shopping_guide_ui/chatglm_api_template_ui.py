import streamlit as st
import os
import requests
import json
from datetime import datetime
import pandas as pd

#replace the parameter value
chat_bot_invoke_url = ""
product_search_invoke_url = ""
ads_invoke_url = ""

index = ""
language = 'chinese'
topK = 2

modelName = 'chatglm_turbo'
modelType = 'llm_api'
apiKey = ''

myscaleHost = 'msc-c6c1595b.us-east-1.aws.myscale.com'
myscalePort = '443'
myscaleUsername = 'myscale_default'
myscalePassword = 'passwd_FIwWZ2NRguOGE8'

  
CHINESE_CHAT = """
你是会展企业的客服人员，帮助客户举办展会、培训、年会、发布会、颁奖、庆典、培训、讲座等活动，任务是与客户沟通，挖掘客户的活动需求，沟通回复客户问题的要求为：
1、如果客户的需求没有包含城市或地点信息，向客户提问想要举办活动的城市，如：请问您的活动地点在哪里呢？
2、如果客户的需求没有包含参加活动的人数信息，向客户提问参加活动的人数，如：请问您的活动有多少人参与呢？
3、如果客户的需求没有包含活动预算信息，向客户提问想要举办活动的预算，如：您的这场活动整体预算大概控制在多少呢？我们会根据您的需求和预算去匹配合适的场地

提问的优先级从上往下，每次提问的内容只包含城市、人数、预算和活动类型的其中一个方面的信息，不要输出客户的活动需求，不要总结客户提问的内容，直接向客户提问。
如果客户的提问类型非举办活动，请回复「我的服务范围为展会、培训或会议等活动举办，謝謝」。

客户提出的需求是: {question}

不要复述客户的需求，不要模拟客户回答，直接向客户提问。
答案:
"""  

CHINESE_ADS = """
你是会展企业的客服人员，帮助客户举办展会、培训、年会、发布会、颁奖、庆典、培训、讲座等活动，请根据客户的需求，对以下的酒店，生成每个酒店的推荐理由。
立即回答问题，不要前言。

酒店信息如下：
<hotel>
{items_info}
</hotel>

客户需求为：{question}

输出每个酒店的推荐理由，按照以下例子输出：
<example>
1、向您推荐广州高岸茶室（北京路店）酒店，该酒店位于北京路、海珠广场商圈，交通便利，会场最大容纳人数为60人，平均全天价格为1650元，符合您的活动需求。该酒店临近东湖地铁站，交通方便。
2、向您推荐广州琶洲酒店，该为三星酒店，属于高端酒店，酒店位于琶洲地铁站附近，交通便利，会场最大容纳人数为200人，平均全天价格为4155元，符合您的活动需求。
</example>
答案:  
"""


# App title
st.set_page_config(page_title="aws & midland intelligent recommendation solution")

def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "欢迎您，这里是人工客服 ，可以免费帮您预定会议场地、酒店住宿等，请问您要在哪个城市举办活动呢？"}]
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    st.session_state.sessionId = 'ir'+str(timestamp)
    st.session_state.recommendationItemId = []
    st.session_state.query = []

with st.sidebar:
    st.title('AWS Intelligent Shopping Guide Solution')
    step = st.radio("请选择问询的轮数",('2','3'))
    top_k = st.slider("请选择搜索酒店的最大数量",1,5,1)
    search_type = st.radio("请选择搜索数据库和搜索类型",('opensearch-vector','opensearch-selfquery','myscale-selfquery'))
    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

st.write("## 智能客服")

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "欢迎您，这里是人工客服 ，可以免费帮您预定会议场地、酒店住宿等，请问您要在哪个城市举办活动呢？"}]
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    st.session_state.sessionId = 'ir'+str(timestamp)
    st.session_state.recommendationItemId = []
    st.session_state.query = []

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# get chat response
def get_chat(query,task):

    url = chat_bot_invoke_url
    url += ('/chat_bot?query='+query)
    url += ('&task='+task)
    url += ('&sessionId='+st.session_state.sessionId)
    url += ('&language='+language)
    url += ('&modelName='+modelName)
    url += ('&modelType='+modelType)
    url += ('&apiKey='+apiKey) 
    url += ('&prompt='+CHINESE_CHAT)


    print('url:',url)
    response = requests.get(url)
    result = response.text
    print('result:',result)
    result = json.loads(result)
    
    print('chat result:',result)
    answer = result['answer']
    return answer


def get_products(query,top_k=1,search_type='opensearch-vector',filter_item_id=[]):
    
    url = product_search_invoke_url
    url += ('/product_search?query='+query)
    url += ('&index='+index)
    url += ('&topK='+str(top_k))
    if len(filter_item_id) > 0:
        print('filter_item_id:',filter_item_id)
        url += ('&itemFilterId='+','.join(filter_item_id))
    url += ('&idKey=酒店名')
    if search_type == 'opensearch-selfquery':
        url += ('&vectorDatabase=opensearch')
        url += ('&searchType=selfQuery')
        url += ('&modelName='+modelName)
        url += ('&modelType='+modelType)
        url += ('&apiKey='+apiKey) 
    elif search_type == 'myscale-selfquery':
        url += ('&vectorDatabase=myscale')
        url += ('&searchType=selfQuery')
        url += ('&modelName='+modelName)
        url += ('&modelType='+modelType)
        url += ('&apiKey='+apiKey) 
        url += ('&myscaleHost='+myscaleHost)
        url += ('&myscalePort='+myscalePort)
        url += ('&myscaleUsername='+myscaleUsername)
        url += ('&myscalePassword='+myscalePassword)

    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    print('result:',result)

    items_info = result['items_info']
    item_info_list = []
    dataframe = {}
    item_ids = []
    for item in items_info:
        item_info = ''
        for key in item.keys():
            item_info += (key+':='+str(item[key])+'\n')
            if key not in dataframe.keys():
                dataframe[key] = []
            dataframe[key].append(item[key])
                
            if key == '酒店名':
                item_ids.append(item[key])
        item_info_list.append('<hotel>'+item_info+'</hotel>')


    items_info_text = '\n\n'.join(item_info_list)
    print('items_info_text:',items_info_text)

    return items_info_text,dataframe,item_ids


def get_item_ads(query,items_info_text):

    url = ads_invoke_url +'/get_item_ads?'
    url += ('query='+query)
    url += ('itemInfo='+items_info_text)
    url += ('&language='+language)
    url += ('&modelName='+modelName)
    url += ('&modelType='+modelType)
    url += ('&apiKey='+apiKey)
    url += ('&prompt='+CHINESE_ADS)

    print('get_item_ads url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    
    print('ads result:',result)

    tag_text = ''
    item_id = ''
    dataframe = {}
    if 'message' in result.keys():
        answer = '对不起，网络有点慢，请您再重复一下您的问题吧。'
    else:
        answer = result['item_ads']
        
    return answer


# User-provided query
if query := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)
        st.session_state.query.append(query)

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            task = "chat"
            combine_query = ','.join(st.session_state.query)
            print('combine_query',combine_query)
            print('task:',task)
            placeholder = st.empty()
            # try:
            if task == "chat":
                answer = get_chat(query,task)
                print('chat answer:',answer)
                if len(st.session_state.messages) >= int(step)*2:
                    task = "recommendation"
                    answer = '请稍等，马上为您推荐相关酒店。'

                response = answer.strip()
                placeholder.markdown(response)
     
            if task == 'recommendation':
                items_info_text,dataframe,item_ids = get_products(combine_query,top_k=top_k,search_type=search_type,filter_item_id=st.session_state.recommendationItemId)
                if len(dataframe) > 0:
                    df = pd.DataFrame(dataframe)
                    df = df.reindex(columns=['城市','地区','酒店名','星级','会场名称','地铁站','最大容纳人数','会场全天价格','会场半天价格'])
                    st.dataframe(df,hide_index=True)
                if len(items_info_text) > 0:
                    answer = get_item_ads(combine_query,items_info_text)
                    if answer == 'error':
                        answer = get_item_ads(combine_query,items_info_text)

                    answer_list = answer.split('、')
                    item_num = len(item_ids)
                    print('answer_list 0:',answer_list)
                    if len(answer_list) > item_num+1:
                        new_list = answer_list[:item_num+1]
                        print('new_list:',new_list)
                        answer = '、'.join(new_list)[:-1]

                    if answer.find('对不起') >= 0:
                        placeholder.markdown(answer)
                    else: 
                        st.write(eval('"'+answer+'"'))

                        if len(item_ids) > 0:
                            st.session_state.recommendationItemId.append(item_ids)
                else:
                    response = '没有找到满足要的酒店，请输入其他条件试试吧！'
                    st.write(response)

            # except:
            #     placeholder.markdown("Sorry,please try again!")
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)