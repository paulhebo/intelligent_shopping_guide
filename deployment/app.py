#!/usr/bin/env python3
import os
import aws_cdk as cdk
from lib.ss_osstack import OpenSearchStack
from lib.ss_chatstack import ChatBotStack
from lib.ss_searchstack import ProductSearchStack
from lib.ss_perrankstack import PersonalizeRankingStack
from lib.ss_adsstack import AdsStack
from lib.ss_userstack import UserInfoStack
from lib.ss_bedrockstack import BedrockStack
from lib.ss_notebook import NotebookStack


ACCOUNT = os.getenv('AWS_ACCOUNT_ID', '')
REGION = os.getenv('AWS_REGION', '')
AWS_ENV = cdk.Environment(account=ACCOUNT, region=REGION)
env = AWS_ENV
print(env)
app = cdk.App()


searchstack = OpenSearchStack(app, "OpenSearchStack2", env=env)
search_engine_key = searchstack.search_domain_endpoint
chatstack = ChatBotStack(app, "ChatBotStack",env=env)
adsstack = AdsStack(app,"AdsStack",env=env)
productsearchstack = ProductSearchStack(app, "ProductSearchStack",search_engine_key=search_engine_key,env=env)
notebookstack = NotebookStack(app, "NotebookStack", search_engine_key=search_engine_key, env=env)

if app.node.try_get_context('use_bedrock'):
    bedrockstack = BedrockStack( app, "BedrockStack", env=env)
if app.node.try_get_context('personalize'):
    prerankstack = PersonalizeRankingStack(app,"PersonalizeRankingStack",env=env)
if app.node.try_get_context('get_userinfo'):
    userstack = UserInfoStack(app,"UserInfoStack",env=env)


app.synth()
