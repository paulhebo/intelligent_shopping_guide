import streamlit as st
import os
import requests
import json
from datetime import datetime
import pandas as pd

#replace the parameter value
chat_bot_invoke_url = "https://3glxpi475h.execute-api.us-east-1.amazonaws.com/prod"
product_search_invoke_url = 'https://ogyc7g1oo3.execute-api.us-east-1.amazonaws.com/prod'
ads_invoke_url = "https://s0vy70zyyh.execute-api.us-east-1.amazonaws.com/prod"

index = "hotel_index_demo_1121_2"
language = 'chinese'
topK = 3

modelName = 'anthropic.claude-v2'
# modelName = 'anthropic.claude-instant-v1'
# modelName = 'anthropic.claude-v1'


CLAUDE_CHINESE_CHAT = """

Human:你是会展企业的客服人员，帮助客户举办展会、培训、年会、发布会、颁奖、庆典、培训、讲座等活动，任务是与客户沟通，挖掘客户的活动需求，沟通回复客户问题的要求为：
1、如果客户的需求没有包含城市或地点信息，向客户提问想要举办活动的城市，如：请问您的活动地点在哪里呢？
2、如果客户的需求没有包含参加活动的人数信息，向客户提问参加活动的人数，如：请问您的活动有多少人参与呢？
3、如果客户的需求没有包含活动预算信息，向客户提问想要举办活动的预算，如：您的这场活动整体预算大概控制在多少呢？我们会根据您的需求和预算去匹配合适的场地
4、如果客户的需求没有包含活动的类型信息，向客户提问想要举办活动的类型，如：请问您的活动类型是什么呢？会议、培训还是年会呢？

提问的优先级从上往下，每次提问的内容只包含城市、人数、预算和活动类型的其中一个方面的信息，不要输出客户的活动需求，不要总结客户提问的内容，直接向客户提问。
如果客户的提问类型非举办活动，请回复「我的服务范围为展会、培训或会议等活动举办，謝謝」。

客户提出的需求是: {question}

不要复述客户的需求，不要模拟客户回答，直接向客户提问。
Assistant:
"""  

CLAUDE_CHINESE_SUMMARIZE = """

Human:
你是会展企业的客服人员，帮助客户举办展会、培训、年会、发布会、颁奖、庆典、培训、讲座等活动，向客户推荐符合客户举办活动需求的酒店，并给出推荐理由。
立即回答问题，不要前言。

酒店信息如下：
<hotel>
{items_info}
</hotel>

客户需求为：{question}

输出符合要求的酒店信息，输出的信息需要包括2部分内容：
1、输出符合客户需求的酒店的推荐理由。酒店最大容纳人数大于客户参加活动的最大人数可认为满足人数要求，客户预算高于酒店价格可以认为满足预算要求。人数和预算只要有一个条件满足要求就可以推荐，推荐理由需要结合客户需求和酒店的信息编写，突出酒店的档次和交通便利性。
2、输出符合客户需求的酒店的标签信息
按照以下例子输出：

<example>
1、推荐理由
向您推荐广州高岸茶室（北京路店）酒店，改酒店位于北京路、海珠广场商圈，交通便利，会场最大容纳人数为60人，平均全天价格为1650元，符合您的活动需求。该酒店临近东湖地铁站，交通方便。
2、酒店标签
城市:=广州
酒店名:=高岸茶室（北京路店）
星级:=其他
商圈:=北京路、海珠广场
地铁站:=东湖
会场名称:=诗梳风
最大容纳人数:=60
会场全天价格(平均):=1650
会场半天价格(平均):=1875
围餐:=0
自助:=0
常办活动类型:=研讨/交流/论坛 | 培训/讲座

</example>

如果找不到符合客户全部需求的酒店，可以推荐最接近客户需求的酒店。

Assistant:   
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
    modelType = 'bedrock'
    step = 2
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
    url += ('&modelType='+modelType)
    url += ('&language='+language)
    url += ('&modelName='+modelName)
    url += ('&prompt='+CLAUDE_CHINESE_CHAT)

    print('url:',url)
    response = requests.get(url)
    result = response.text
    print('result:',result)
    result = json.loads(result)
    
    print('chat result:',result)
    answer = result['answer']
    return answer


def get_products(query,top_k=1,filter_item_id=[]):
    
    url = product_search_invoke_url
    url += ('/product_search?query='+query)
    url += ('&index='+index)
    url += ('&topK='+str(topK))
    if len(filter_item_id) > 0:
        url += ('&itemFilterId='+','.join(filter_item_id))
    url += ('&idKey=酒店名')
 
    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    print('result:',result)

    items_info = result['items_info']
    item_info_list = []
    i = 0
    for item in items_info:
        i += 1
        if i >=topK:
            break
        item_info = ''
        for key in item.keys():
            item_info += (key+':='+item[key]+'\n')
        item_info_list.append('<apartment>'+item_info+'</apartment>')


    items_info_text = '\n\n'.join(item_info_list)
    print('items_info_text:',items_info_text)

    return items_info_text


def get_item_ads(query,items_info_text):

    url = ads_invoke_url +'/get_item_ads?'
    url += ('query='+query)
    url += ('itemInfo='+items_info_text)
    url += ('&modelType='+modelType)
    url += ('&language='+language)
    url += ('&modelName='+modelName)
    url += ('&prompt='+CLAUDE_CHINESE_SUMMARIZE)

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
        product_info = result['item_ads']
        if product_info.find('推荐理由') >= 0:
            output_list = product_info.split('推荐理由')[1].split('2、')
            answer = output_list[0].replace('\n','').strip()
            print('reason:',answer)
        
            tags = output_list[1].split('\n')
            for tag in tags:
                tag = tag.split(':=')
                if len(tag) == 2:
                    key = tag[0].strip()
                    value = tag[1].strip()

                    if key == '酒店名':
                        item_id = value
                    
                    dataframe[key] = [value]
                    tag_text += (key+':'+value + ',')

            print('tag_text:',tag_text)
            print('item_id:',item_id)
        else:
            answer = product_info
    return answer,item_id,tag_text,dataframe


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
            if len(st.session_state.messages) >= int(step)*2:
                task = 'ads'

            print('task:',task)
            placeholder = st.empty()
            # try:
            if task == "chat":
                response = get_chat(query,task)
                placeholder.markdown(response.strip())
     
            if task == 'ads':
                items_info_text = get_products(combine_query,filter_item_id=st.session_state.recommendationItemId)
                answer,item_id,tag_text,dataframe = get_item_ads(combine_query,items_info_text)
                if answer == 'error':
                    answer,item_id,tag_text,dataframe = get_item_ads(combine_query,items_info_text)

                response = answer

                if answer.find('对不起') >= 0:
                    placeholder.markdown(answer)
                    
                else: 
                    st.write(answer)
                    if len(dataframe) > 0:
                        df = pd.DataFrame(dataframe)
                        st.dataframe(df,hide_index=True)

                    if len(tag_text) > 0:
                        response = answer + '\n' + tag_text

                    if len(item_id) > 0:
                        st.session_state.recommendationItemId.append(item_id)

            # except:
            #     placeholder.markdown("Sorry,please try again!")
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)