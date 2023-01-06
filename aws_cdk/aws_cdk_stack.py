from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_logs as logs,
    custom_resources as cr,
    Duration
)
from aws_cdk.aws_ecr_assets import DockerImageAsset
from constructs import Construct
import os

class Housepredict_CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        # ---------- PERMISSIONS AND NETWORK CONFIG ---------- #

        # Role used for ECS (this role is already configured for ECS use)
        role_ecs_athena = iam.Role.from_role_arn(self, 'role',
            role_arn='arn:aws:iam::324430962407 :role/ECS_EC2'
        )

        # VPC - gets the default VCP for the account used
        vpc = ec2.Vpc.from_lookup(self, "Vpc",
            is_default=True,
        )
        
        # Log group
        log_group = logs.LogGroup(self, "active-users-report-cdk-log")

        

        # ---------- INFRASTRUCTURE ---------- #


        # Docker image upload (this will automatically create an ECR repository and upload the docker image to it)
        image = DockerImageAsset(self,
                                "MyBuildImage",
                                directory="active_users_report_cdk/house_predict/"
            )

        # Create ECS cluster
        cluster = ecs.Cluster(self, "Cluster",    
            cluster_name= 'house-predict-cluster',
            vpc=vpc,
        )
        
        # Create task definition
        task_definition = ecs.FargateTaskDefinition(self, 'task_definition',
            task_role=role_ecs_athena,
            cpu=16384, #16 vCPU
            memory_limit_mib=65536, #64 GB
            ephemeral_storage_gib=48 #48 GB (20GB for free in Fargate, only paying for 28GB - $0.000111 per hour per GB)
        )

        # Container Definition
        container_definition = task_definition.add_container('container_definition',
            image=ecs.ContainerImage.from_docker_image_asset(image),
            logging=ecs.LogDrivers.aws_logs(stream_prefix='house-predict-cdk-log', log_group=log_group)
        )

        # ---------- RUN CONFIGURATION ---------- #
        ecs_task = tasks.EcsRunTask(self, 'run_task',
            cluster=cluster,
            assign_public_ip=True,
            task_definition=task_definition,
            container_overrides=[tasks.ContainerOverride(container_definition=container_definition)],
            launch_target=tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST),
            timeout=Duration.hours(6),
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
        )

        #Define the initial state of the state machine
        start_state = sfn.Pass(self, 'Start_State_create_client_cluster')

        #The next state of the state machine
        definition = start_state.next(ecs_task)

        #The role that will be used by the state machine
        role_state_machine = iam.Role.from_role_arn(self, 'role_state_machine_create_client_cluster',
            role_arn='arn:aws:iam::324430962407 :role/BrunoTestStepFun202212271338'
        )

        #Define the state machine, 
        state_machine = sfn.StateMachine(self, 'State_Machine_create_client_cluster',
            definition=definition,
            timeout=Duration.hours(6),
            logs= sfn.LogOptions(destination=log_group,
                level=sfn.LogLevel.ALL,
                include_execution_data=True,
            ),
            role=role_state_machine
        )

        #The SDK call that will run the state machine and the step function
        custom_resorce = cr.AwsCustomResource(self, 'RunStateMachine_create_client_cluster',
            on_create=cr.AwsSdkCall(service= 'StepFunctions',
                action= 'startExecution',
                parameters= {
                    'stateMachineArn': state_machine.state_machine_arn
                },
                physical_resource_id=cr.PhysicalResourceId.of(state_machine.state_machine_arn),
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(resources=[state_machine.state_machine_arn]),
            resource_type='Custom::RunStateMachine'
        )