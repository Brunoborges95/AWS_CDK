import aws_cdk as core
import aws_cdk.assertions as assertions
from aws_cdk.aws_cdk_stack import AwsCdkStack


def test_sqs_queue_created():
    app = core.App()
    stack = AwsCdkStack(app, "aws-cdk")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::SQS::Queue", {
        "VisibilityTimeout": 300
    })


def test_sns_topic_created():
    app = core.App()
    stack = AwsCdkStack(app, "aws-cdk")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::SNS::Topic", 1)
