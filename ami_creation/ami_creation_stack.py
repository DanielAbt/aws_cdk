from aws_cdk import (
    CfnOutput,
    Stack,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_imagebuilder as imagebuilder,
)
from common_resources.common_resources import CommonResources
from constructs import Construct

from ami_creation.ami_component_stack import AmiComponentStack


class AMICreationStack(Stack):
    ALLOWED_MACHINE_TYPES = {"Testing", "Another machine name here"}

    def __init__(
        self,
        scope: Construct,
        id: str,
        machine_type: str,
        properties: dict,
        **kwargs,
    ) -> None:
        """
        CDK Stack to create an AMI for the given machine type.

        This stack includes the following components:
        - Common resources (VPC, security groups, etc.)
        - AMI component (e.g., packages, files, etc.)
        - Image Builder infrastructure configuration
        - Image Builder distribution configuration
        - Image Builder recipe
        - Image Builder pipeline

        :param scope: CDK construct scope
        :param construct_id: CDK construct ID
        :param machine_type: Machine type to run the pipeline for
                            (e.g., "Testing", "Another machine name here")
        :param kwargs: Additional keyword arguments
        """
        super().__init__(scope, id, **kwargs)

        # Common resources
        machine_type = machine_type.title()
        if machine_type not in self.ALLOWED_MACHINE_TYPES:
            raise ValueError(f"{machine_type} is not a valid machine type.")

        self.machine_type = machine_type
        self.properties = properties
        self.resources = CommonResources(self)
        self.component = AmiComponentStack(self)
        self.instance_role = self._create_instance_role(self.machine_type)
        self.infra_config = self._create_infrastructure_config(self.machine_type)
        self.dist_config = self._create_distribution_config(self.machine_type)
        if self.machine_type == "Testing":
            self.custom_component = self.component.testing_component(self.properties)
        if self.machine_type == "Another machine name here":
            self.custom_component = self.component.Another_machine_name_here_component(self.properties) # create another custom component for this machine type

        self.custom_recipe = self._create_recipe(self.machine_type, self.custom_component)
        self.custom_pipeline = self._create_pipeline(self.machine_type, self.custom_recipe)

    def _create_instance_role(self, name):
        image_builder_role = iam.Role(
            self,
            f"ImageBuilderRole-{name}",
            role_name=f"ImageBuilderRole-{name}",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                iam.ManagedPolicy.from_aws_managed_policy_name("EC2InstanceProfileForImageBuilder"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMFullAccess"),
            ],
        )
        # Create a custom policy for S3 access
        s3_access_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:ListBucket",
            ],
            resources=[
                f"arn:aws:s3:::{self.properties['s3.bucket.name']}/packages/*",
            ],
        )

        # Add the custom policy to the role
        image_builder_role.add_to_principal_policy(s3_access_policy)

        # Create an instance profile and add the role to it
        instance_profile = iam.CfnInstanceProfile(
            self,
            f"ImageBuilderInstanceProfile-{name}",
            instance_profile_name=f"ImageBuilderInstanceProfile-{name}",
            roles=[image_builder_role.role_name],
        )
        return instance_profile

    def _create_infrastructure_config(self, name):
        return imagebuilder.CfnInfrastructureConfiguration(
            self,
            f"InfraConfig-{name}",
            name=f"InfraConfig{name}",
            instance_types=["t3.micro"],
            instance_profile_name=self.instance_role.ref,
            subnet_id=self.properties["subnet.private.id"],
            security_group_ids=[self.properties["sg.id"]],
        )

    def _create_distribution_config(self, name):
        return imagebuilder.CfnDistributionConfiguration(
            self,
            f"DistributionConfig-{name}",
            description="custom machine",
            name=f"DistributionConfig-{name}",
            distributions=[
                {
                    "region": self.region,
                    "targetAccountIds": [self.account],
                    "amiDistributionConfiguration": {
                        "Name": f"Custom-{name}-{{{{imagebuilder:buildDate}}}}",
                        "AmiTags": {
                            "OS": "Ubuntu",
                            "OSVersion": "20.04 LTS",
                            "Platform": "Ubuntu",
                            "BaseAMI": "Canonical Ubuntu",
                            "Distribution": "Ubuntu",
                            "Environment": "Staging",
                            "ComponentVersion": self.properties["ami.component.version"],
                            "PythonVersion": "3.8",
                            "MachineType": name,
                        },
                        "Description": f"Custom {name} AMI created on {{{{imagebuilder:buildDate}}}}",
                    },
                },
            ],
            tags={
                "OS": "Ubuntu",
                "OSVersion": "20.04 LTS",
                "Platform": "Ubuntu",
                "BaseAMI": "Canonical Ubuntu",
                "Distribution": "Ubuntu",
                "Environment": "Staging",
                "ComponentVersion": self.properties["ami.component.version"],
                "PythonVersion": "3.8",
                "MachineType": name,
            },
        )

    def _create_recipe(self, name, component):
        return imagebuilder.CfnImageRecipe(
            self,
            f"Recipe-{name}",
            name=f"Custom-recipe-{name}",
            version=self.properties["ami.component.version"],
            components=[
                {"componentArn": component.attr_arn},
            ],
            parent_image=self.properties["ami.parent.image"],
            block_device_mappings=[
                imagebuilder.CfnImageRecipe.InstanceBlockDeviceMappingProperty(
                    device_name="/dev/sda1",
                    ebs=imagebuilder.CfnImageRecipe.EbsInstanceBlockDeviceSpecificationProperty(
                        delete_on_termination=True,
                        encrypted=False,
                        volume_size=8,
                        volume_type="gp2",
                    ),
                )
            ],
            tags={
                "OS": "Ubuntu",
                "OSVersion": "20.04 LTS",
                "Platform": "Ubuntu",
                "BaseAMI": "Canonical Ubuntu",
                "Distribution": "Ubuntu",
                "Environment": "Staging",
                "ComponentVersion": self.properties["ami.component.version"],
                "PythonVersion": "3.8",
                "MachineType": name,
            },
        )

    def _create_pipeline(self, name, recipe):
        pipeline = imagebuilder.CfnImagePipeline(
            self,
            f"Pipeline-{name}",
            name=f"Pipeline-{name}",
            image_recipe_arn=recipe.attr_arn,
            infrastructure_configuration_arn=self.infra_config.attr_arn,
            distribution_configuration_arn=self.dist_config.attr_arn,
        )

        CfnOutput(
            self,
            f"{name}PipelineArn",
            value=pipeline.attr_arn,
            description=f"The ARN of the {name}",
            export_name=f"{name}PipelineArn",
        )

        return pipeline
