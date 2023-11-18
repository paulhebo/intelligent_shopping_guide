from constructs import Construct
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

class AdsStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        llm_embedding_name = self.node.try_get_context("llm_embedding_name")
        
    # configure the lambda role
        _ads_role_policy = iam.PolicyStatement(
            actions=[
                'sagemaker:InvokeEndpointAsync',
                'sagemaker:InvokeEndpoint',
                'lambda:AWSLambdaBasicExecutionRole',
            ],
            resources=['*']
        )
        ads_role = iam.Role(
            self, 'ads_role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )
        ads_role.add_to_policy(_ads_role_policy)

        ads_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        

        ads_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
        )
        
                # add intelligent recommendation lambda
        ads_layer = _lambda.LayerVersion(
          self, 'IRLambdaLayer',
          code=_lambda.Code.from_asset('../lambda_layer_folder'),
          compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
          description='IR Library'
        )
        
        function_name = 'get_item_ads'
        ads_function = _lambda.Function(
            self, function_name,
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_9,
            role=ads_role,
            layers=[ads_layer],
            code=_lambda.Code.from_asset('../lambda/' + function_name),
            handler='lambda_function' + '.lambda_handler',
            timeout=Duration.minutes(10),
            reserved_concurrent_executions=100
        )
        ads_function.add_environment("llm_embedding_name", llm_embedding_name)
        
        qa_api = apigw.RestApi(self, 'ads-api',
                               default_cors_preflight_options=apigw.CorsOptions(
                                   allow_origins=apigw.Cors.ALL_ORIGINS,
                                   allow_methods=apigw.Cors.ALL_METHODS
                               ),
                               endpoint_types=[apigw.EndpointType.REGIONAL]
                               )
                               
        ads_integration = apigw.LambdaIntegration(
            ads_function,
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
        
        ads_resource = qa_api.root.add_resource(
            'get_item_ads',
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=['GET', 'OPTIONS'],
                allow_origins=apigw.Cors.ALL_ORIGINS)
        )

        ads_resource.add_method(
            'GET',
            ads_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )
        