from aws_cdk import (
    CfnOutput,
    Fn,
    Stack,
    aws_logs,
)
from aws_cdk import (
    custom_resources as cr,
)
from constructs import Construct


class AmiPipelineStack(Stack):
    ALLOWED_MACHINE_TYPES = {"Testing", "Another machine name here"}
    
    def __init__(self, scope: Construct, construct_id: str, machine_type: str, **kwargs) -> None:
        """
        CDK Stack to run the AMI pipeline for the given machine type.

        :param scope: CDK construct scope
        :param construct_id: CDK construct ID
        :param machine_type: Machine type to run the pipeline for
                            (e.g., "Testing", "Another machine name here")
        :param kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        machine_type = machine_type.title()
        if machine_type not in self.ALLOWED_MACHINE_TYPES:
            raise ValueError(f"{machine_type} is not a valid machine type.")

        pipeline_arn_name = f"{machine_type}PipelineArn"

        # Import the pipeline ARN from the other stack
        pipeline_arn = Fn.import_value(pipeline_arn_name)

        # Create a custom resource to run the pipeline
        run_pipeline = cr.AwsCustomResource(
            self,
            f"AmiPipeline-{machine_type}",
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            on_create=cr.AwsSdkCall(
                service="ImageBuilder",
                action="startImagePipelineExecution",
                parameters={"imagePipelineArn": pipeline_arn},
                physical_resource_id=cr.PhysicalResourceId.of("ImagePipelineExecution"),
            ),
            on_update=cr.AwsSdkCall(
                service="ImageBuilder",
                action="startImagePipelineExecution",
                parameters={"imagePipelineArn": pipeline_arn},
                physical_resource_id=cr.PhysicalResourceId.of("ImagePipelineExecution"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(resources=[pipeline_arn]),
        )

        # Output the execution ID
        CfnOutput(
            self,
            f"PipelineId-{machine_type}",
            value=run_pipeline.get_response_field("imageBuildVersionArn"),
            export_name=f"PipelineId-{machine_type}",
        )
