import os
import sys
from typing import Dict

import aws_cdk as cdk
import boto3
from ami_creation.ami_creation_stack import AMICreationStack
from ami_creation.ami_pipeline_stack import AmiPipelineStack
from ami_creation.ec2_launch_stack import LaunchTemplateStack


def read_properties_file(environment) -> Dict[str, str]:
    properties = {}

    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    properties_file_path = os.path.join(parent_dir, "aws_v2", f"config.{environment}.properties")

    if not os.path.exists(properties_file_path):
        raise FileNotFoundError(f"Properties file not found at {properties_file_path}")

    with open(properties_file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                properties[key.strip()] = value.strip()
    return properties


def get_latest_custom_ami(ec2_client, machine_type: str, component_version: str) -> Dict:
    filters = [
        {"Name": "state", "Values": ["available"]},
        {"Name": "tag:MachineType", "Values": [machine_type]},
        {"Name": "tag:ComponentVersion", "Values": [component_version]},
    ]

    response = ec2_client.describe_images(Owners=["self"], Filters=filters)

    if not response["Images"]:
        print(f"No AMI found for MachineType '{machine_type}' and ComponentVersion '{component_version}'\n")
        return None

    # Sort images by creation date (newest first)
    sorted_images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
    latest_ami = sorted_images[0]

    return {"ImageId": latest_ami["ImageId"], "Name": latest_ami["Name"], "CreationDate": latest_ami["CreationDate"]}


def main():
    app = cdk.App()

    environment_name = app.node.try_get_context("environment_name")
    if environment_name not in ["staging", "production"]:
        print("Environment must be either 'staging' or 'production'\n")
        sys.exit(1)

    properties = read_properties_file(environment_name)
    properties["environment"] = environment_name

    env = {"account": properties["aws.account.id"], "region": properties["aws.region"]}

    boto3_session = boto3.session.Session(profile_name=properties["aws.profile"])
    ec2_client = boto3_session.client("ec2", region_name=properties["aws.region"])

    stack_name = app.node.try_get_context("stack_name")

    # Create stacks
    create_ami = AMICreationStack(app, "CreateAMI", "Testing", properties, env=env)

    build_ami = AmiPipelineStack(app, "BuildAMI", "Testing", env=env)

    # For LaunchTemplateStacks, we'll check AMI availability before creating the stack
    if stack_name == "CreateTemplate":
        custom_ami = get_latest_custom_ami(ec2_client, "Testing", properties["ami.component.version"])
        if not custom_ami:
            print("Failed to find required AMI or AMI is not in 'available' state\n")
            sys.exit(1)
        create_template = LaunchTemplateStack(
            app, "CreateTemplate", "Testing", properties, custom_ami["ImageId"], env=env
        )
        create_template.add_dependency(build_ami)

    # Define dependencies
    build_ami.add_dependency(create_ami)

    app.synth()


if __name__ == "__main__":
    main()
