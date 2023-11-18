from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Duration

)
import os

class ChatBotStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        llm_endpoint_name = self.node.try_get_context("llm_endpoint_name")
        language = self.node.try_get_context("language")
        
        # configure the lambda role
        _chat_bot_role_policy = iam.PolicyStatement(
            actions=[
                'sagemaker:InvokeEndpointAsync',
                'sagemaker:InvokeEndpoint',
                'lambda:AWSLambdaBasicExecutionRole',
                'lambda:InvokeFunction',
                'secretsmanager:SecretsManagerReadWrite'
            ],
            resources=['*']
        )
        chat_bot_role = iam.Role(
            self, 'chat_bot_role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )
        chat_bot_role.add_to_policy(_chat_bot_role_policy)

        chat_bot_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        chat_bot_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )

        chat_bot_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
        )
        
        # add intelligent recommendation lambda
        chat_bot_layer = _lambda.LayerVersion(
          self, 'IRLambdaLayer',
          code=_lambda.Code.from_asset('../lambda/lambda_layer_folder'),
          compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
          description='IR Library'
        )
        
        function_name = 'chat_bot'
        chat_bot_function = _lambda.Function(
            self, function_name,
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_9,
            role=chat_bot_role,
            layers=[chat_bot_layer],
            code=_lambda.Code.from_asset('../lambda/' + function_name),
            handler='lambda_function' + '.lambda_handler',
            timeout=Duration.minutes(10),
            reserved_concurrent_executions=100
        )

        chat_bot_function.add_environment("language", language)
        chat_bot_function.add_environment("llm_endpoint_name", llm_endpoint_name)


        qa_api = apigw.RestApi(self, 'chat-bot-api',
                               default_cors_preflight_options=apigw.CorsOptions(
                                   allow_origins=apigw.Cors.ALL_ORIGINS,
                                   allow_methods=apigw.Cors.ALL_METHODS
                               ),
                               endpoint_types=[apigw.EndpointType.REGIONAL]
                               )
                               
        chat_bot_integration = apigw.LambdaIntegration(
            chat_bot_function,
            proxy=True,
            integration_responses=[
                apigw.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
            ]
        )

        chat_bot_resource = qa_api.root.add_resource(
            'chat_bot',
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=['GET', 'OPTIONS'],
                allow_origins=apigw.Cors.ALL_ORIGINS)
        )

        chat_bot_resource.add_method(
            'GET',
            chat_bot_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )
        
        chat_table = dynamodb.Table(self, "chat_session_table",
                                    partition_key=dynamodb.Attribute(name="session-id",
                                                                     type=dynamodb.AttributeType.STRING)
                                    )

        dynamodb_role = iam.Role(
            self, 'dynamodb_role',
            assumed_by=iam.ServicePrincipal('dynamodb.amazonaws.com')
        )
        dynamodb_role_policy = iam.PolicyStatement(
            actions=[
                'sagemaker:InvokeEndpointAsync',
                'sagemaker:InvokeEndpoint',
                's3:AmazonS3FullAccess',
                'lambda:AWSLambdaBasicExecutionRole',
            ],
            effect=iam.Effect.ALLOW,
            resources=['*']
        )
        dynamodb_role.add_to_policy(dynamodb_role_policy)
        chat_table.grant_read_write_data(dynamodb_role)
        chat_bot_function.add_environment("dynamodb_table_name", chat_table.table_name)
        cdk.CfnOutput(self, 'chat_table_name', value=chat_table.table_name, export_name='ChatTableName')
