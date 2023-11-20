from constructs import Construct
import os.path
from aws_cdk.aws_autoscaling import AutoScalingGroup, BlockDevice, BlockDeviceVolume
import aws_cdk as cdk
from aws_cdk.aws_lambda_event_sources import DynamoEventSource
import boto3

from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    App, Stack,
    aws_dynamodb as dynamodb,
    aws_elasticloadbalancingv2 as elbv2,
    Fn,
    RemovalPolicy,
    aws_lambda as _lambda,
    Duration,
    Tags
)

dirname = os.path.dirname(__file__)

# Read content from script
with open(f"{dirname}/asr-user-data/init.sh") as f:
    user_data_script_content = f.read()


class ASRStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.upload_custom_asr_ui_script_to_sagemaker_default_bucket()

        # self.asr_content_table = None
        # self.asr_content_table_name = self.node.try_get_context("asr_content_table_name")
        #
        self.provision_asr_server()
        # self.provision_dynamodb()
        #
        # self.asr_content_layer = _lambda.LayerVersion(
        #     self, 'ASR_Content_layer',
        #     code=_lambda.Code.from_asset('../lambda/asr_content_processor_layer'),
        #     compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
        #     description='ASR_Content_layer'
        # )
        #
        # self.provision_asr_stream_processor()
        # self.provision_asr_content_processor()

    """
        Upload custom whisper ui to Sagemaer default bucket.
        This file will be retrieved when spinning up ASR server
    """

    def upload_custom_asr_ui_script_to_sagemaker_default_bucket(self):
        s3 = boto3.client('s3')
        with open(f"{dirname}/asr-user-data/faster-whisper-ui.py", "rb") as f:
            s3.upload_fileobj(f,
                              "sagemaker-{}-{}".format(os.environ.get("AWS_REGION", ""),
                                                       os.environ.get("AWS_ACCOUNT_ID", "")),
                              "app.py")

        with open(f"{dirname}/asr-user-data/config.json5", "rb") as f:
            s3.upload_fileobj(f,
                              "sagemaker-{}-{}".format(os.environ.get("AWS_REGION", ""),
                                                       os.environ.get("AWS_ACCOUNT_ID", "")),
                              "config.json5")

    """
        Provision ASR Server, along with VPC and LB
    """

    def provision_asr_server(self):
        # VPC
        vpc = ec2.Vpc(self, "asr_vpc",
                      ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/21"),
                      max_azs=2,

                      subnet_configuration=[
                          {
                              "cidrMask": 24,
                              "name": "Public",
                              "subnetType": ec2.SubnetType.PUBLIC,
                          }
                      ]
                      )

        # Pick Deep Learning AMI for speeding up Python Env setup
        deeplearning_linux = ec2.MachineImage.lookup(
            name="Deep Learning AMI GPU PyTorch 2.0.1*",
            owners=["amazon"]
        )

        # Instance Role and SSM Managed Policy
        role = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

        # Add S3 Full Access for quick demo
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"))

        # Add EC2 ReadOnly Access for Describing tags
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ReadOnlyAccess"))

        # Add DynamoDB Full Access for Saving Transcription to table
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess"))

        security_group = ec2.SecurityGroup(self, "SecurityGroup", vpc=vpc)

        # Configure ASG
        asg = AutoScalingGroup(self, "ASR-ASG",
                               vpc=vpc,
                               instance_type=ec2.InstanceType.of(ec2.InstanceClass.G5, ec2.InstanceSize.XLARGE),
                               machine_image=deeplearning_linux,  # ec2.AmazonLinuxImage(),
                               security_group=security_group,
                               role=role,
                               block_devices=[
                                   BlockDevice(
                                       device_name="/dev/xvda",
                                       volume=BlockDeviceVolume.ebs(
                                           self.node.try_get_context('asr_model_server_disk_size')),
                                   )
                               ],
                               associate_public_ip_address=True,
                               user_data=ec2.UserData.custom(user_data_script_content)
                               )

        Tags.of(asg).add('asr_content_table', self.asr_content_table_name);

        # asg: AutoScalingGroup
        # Create the load balancer in a VPC. 'internetFacing' is 'false'
        # by default, which creates an internal load balancer.
        api_alb = elbv2.ApplicationLoadBalancer(self, "API_ALB",
                                                vpc=vpc,
                                                internet_facing=True,
                                                idle_timeout=Duration.seconds(4000),  # timeout set to 4000s
                                                )

        # Add a listener and open up the load balancer security group to the world.
        api_listener = api_alb.add_listener("Listener",
                                            port=80,

                                            # 'open: true' is the default, you can leave it out if you want. Set it
                                            # to 'false' and use `listener.connections` if you want to be selective
                                            # about who can access the load balancer.
                                            open=True
                                            )

        # Create an AutoScaling group and add it as a load balancing target to the listener.
        api_listener.add_targets("ApplicationFleet",
                                 protocol=elbv2.ApplicationProtocol.HTTP,
                                 port=5000,
                                 targets=[asg]
                                 )

        # Create ALB / Listener for ASR UI.
        asr_ui_alb = elbv2.ApplicationLoadBalancer(self, "UI_ALB",
                                                   vpc=vpc,
                                                   internet_facing=True,
                                                   idle_timeout=Duration.seconds(4000),  # timeout set to 4000s
                                                   )

        asr_ui_listener = asr_ui_alb.add_listener("Listener",
                                                  port=80,
                                                  # 'open: true' is the default, you can leave it out if you want. Set it
                                                  # to 'false' and use `listener.connections` if you want to be selective
                                                  # about who can access the load balancer.
                                                  open=True
                                                  )

        asr_ui_listener.add_targets("ApplicationFleet_ASR",
                                    protocol=elbv2.ApplicationProtocol.HTTP,
                                    port=7860,
                                    targets=[asg]
                                    )

        cdk.CfnOutput(self, 'api_alb_endpoint', value=f"http://{api_alb.load_balancer_dns_name}",
                      export_name='API-ALB-Endpoint')
        cdk.CfnOutput(self, 'asr_ui_alb_endpoint', value=f"http://{asr_ui_alb.load_balancer_dns_name}",
                      export_name='ASR-UI-ALB-Endpoint')

    """
        Provision DynamoDB table for storing ASR text 
    """

    # def provision_dynamodb(self):
    #     # Create DynamoDB
    #     asr_content_table = dynamodb.Table(
    #         self,
    #         id=self.asr_content_table_name,
    #         table_name=self.asr_content_table_name,
    #         partition_key=dynamodb.Attribute(
    #             name="file_id",
    #             type=dynamodb.AttributeType.STRING
    #         ),
    #
    #         stream=dynamodb.StreamViewType.NEW_IMAGE,
    #         removal_policy=RemovalPolicy.DESTROY
    #     )
    #
    #     dynamodb_role = iam.Role(
    #         self, 'asr_content_dynamodb_role',
    #         assumed_by=iam.ServicePrincipal('dynamodb.amazonaws.com')
    #     )
    #     dynamodb_role_policy = iam.PolicyStatement(
    #         actions=[
    #             'sagemaker:InvokeEndpointAsync',
    #             'sagemaker:InvokeEndpoint',
    #             's3:AmazonS3FullAccess',
    #             'lambda:AWSLambdaBasicExecutionRole',
    #         ],
    #         effect=iam.Effect.ALLOW,
    #         resources=['*']
    #     )
    #
    #     dynamodb_role.add_to_policy(dynamodb_role_policy)
    #     asr_content_table.grant_read_write_data(dynamodb_role)
    #
    #     self.asr_content_table = asr_content_table
    #
    #     cdk.CfnOutput(self, 'asr_content_table', value=asr_content_table.table_name, export_name='ASR-Content-Table')
    #
    # """
    #     Provision Event Trigger Processor.
    #     The processor is triggered by DynamoDB Stream, covering
    #     - INSERT record - invoke ASR_CONTENT_PROCESSOR for LLM summary
    #     - UPDATE record - when summary is ready, trigger EMAIL sending.
    # """
    #
    # def provision_asr_stream_processor(self):
    #     asr_content_processor_func_name = self.node.try_get_context("asr_content_processor_func_name")
    #     turn_on_email_notification = self.node.try_get_context("turn_on_email_notification")
    #     source_sender = self.node.try_get_context("source_sender")
    #
    #     asr_stream_processor_policy = iam.PolicyStatement(
    #         actions=[
    #             "lambda:InvokeFunction",
    #             "lambda:InvokeAsync",
    #             "ses:SendEmail",
    #             "ses:SendRawEmail",
    #         ],
    #         resources=['*']
    #     )
    #
    #     asr_stream_processor_role = iam.Role(
    #         self,
    #         'asr_stream_processor_role',
    #         assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
    #     )
    #
    #     asr_stream_processor_role.add_to_policy(asr_stream_processor_policy)
    #
    #     asr_stream_processor_role.add_managed_policy(
    #         iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
    #     )
    #
    #     asr_stream_processor_role.add_managed_policy(
    #         iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
    #     )
    #
    #     # add langchain processor for smart query and answer
    #     asr_func_name = 'asr_stream_processor'
    #
    #     asr_stream_processor_func = _lambda.Function(
    #         self, asr_func_name,
    #         function_name=asr_func_name,
    #         runtime=_lambda.Runtime.PYTHON_3_9,
    #         role=asr_stream_processor_role,
    #         code=_lambda.Code.from_asset('../lambda/' + asr_func_name),
    #         handler='lambda_function' + '.lambda_handler',
    #         memory_size=256,
    #         timeout=Duration.minutes(10),
    #         reserved_concurrent_executions=10
    #     )
    #     asr_stream_processor_func.add_environment("asr_content_processor_func_name", asr_content_processor_func_name)
    #     asr_stream_processor_func.add_environment("turn_on_email_notification", turn_on_email_notification)
    #     asr_stream_processor_func.add_environment("source_sender", source_sender)
    #
    #     # Add DynamoDB Stream to ASR_Stream_Processor
    #     asr_stream_processor_func.add_event_source(DynamoEventSource(self.asr_content_table,
    #                                                                  starting_position=_lambda.StartingPosition.LATEST,
    #                                                                  batch_size=10,
    #                                                                  bisect_batch_on_error=False,
    #                                                                  retry_attempts=0
    #                                                                  ))
    #
    # """
    #     Provision Lambda Function that process NEW data from DynamoDB
    #     This function will majorly pass data to LLM and save summary to DynamoDB.
    # """
    #
    # def provision_asr_content_processor(self):
    #     llm_embedding_name = self.node.try_get_context("llm_embedding_name")
    #     asr_content_table = self.node.try_get_context("asr_content_table_name")
    #     asr_func_name = self.node.try_get_context("asr_content_processor_func_name")
    #
    #     asr_content_processor_policy = iam.PolicyStatement(
    #         actions=[
    #             'sagemaker:InvokeEndpointAsync',
    #             'sagemaker:InvokeEndpoint',
    #             'lambda:AWSLambdaBasicExecutionRole',
    #             'secretsmanager:SecretsManagerReadWrite',
    #             'es:ESHttpPost'
    #         ],
    #         resources=['*']
    #     )
    #
    #     asr_content_processor_role = iam.Role(
    #         self,
    #         'asr_content_processor_role',
    #         assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
    #     )
    #
    #     asr_content_processor_role.add_to_policy(asr_content_processor_policy)
    #
    #     asr_content_processor_role.add_managed_policy(
    #         iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
    #     )
    #
    #     asr_content_processor_role.add_managed_policy(
    #         iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
    #     )
    #
    #     asr_content_processor_func = _lambda.Function(
    #         self, asr_func_name,
    #         function_name=asr_func_name,
    #         runtime=_lambda.Runtime.PYTHON_3_9,
    #         role=asr_content_processor_role,
    #         layers=[self.asr_content_layer],
    #         code=_lambda.Code.from_asset('../lambda/' + asr_func_name),
    #         handler='lambda_function' + '.lambda_handler',
    #         memory_size=5120,
    #         timeout=Duration.minutes(15),
    #         reserved_concurrent_executions=10
    #     )
    #     asr_content_processor_func.add_environment("asr_content_table", asr_content_table)
    #     asr_content_processor_func.add_environment("llm_embedding_name", llm_embedding_name)
