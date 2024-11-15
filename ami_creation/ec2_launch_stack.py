from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_ec2 as ec2
from common_resources.common_resources import CommonResources
from constructs import Construct


class LaunchTemplateStack(Stack):
    def __init__(
        self, scope: Construct, id: str, machine_type: str, properties: dict, custom_ami: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        common_resources = CommonResources(self)
        ami_id = custom_ami
        machine_image = ec2.MachineImage.generic_linux({self.region: ami_id})

        if machine_type == "Testing":
            device_name_root = properties["ec2.instance.pm.volume.name.root"]
            volume_size_root = int(properties["ec2.instance.pm.volume.size.root"])
            volume_type_root = common_resources.get_volume_type(properties["ec2.instance.pm.volume.type.root"])
            device_name_home = properties["ec2.instance.pm.volume.name.home"]
            volume_size_home = int(properties["ec2.instance.pm.volume.size.home"])
            volume_type_home = common_resources.get_volume_type(properties["ec2.instance.pm.volume.type.home"])
            volume_hdd_type_home = properties["ec2.instance.pm.volume.hdd.type.home"]
            instance_type = properties["ec2.instance.pm.type"]
        else:
            device_name_root = properties["ec2.instance.dm.volume.name.root"]
            volume_size_root = int(properties["ec2.instance.dm.volume.size.root"])
            volume_type_root = common_resources.get_volume_type(properties["ec2.instance.dm.volume.type.root"])
            device_name_home = properties["ec2.instance.dm.volume.name.home"]
            volume_size_home = int(properties["ec2.instance.dm.volume.size.home"])
            volume_type_home = common_resources.get_volume_type(properties["ec2.instance.dm.volume.type.home"])
            volume_hdd_type_home = properties["ec2.instance.dm.volume.hdd.type.home"]
            instance_type = properties["ec2.instance.dm.type"]

        # Define block devices
        block_devices = [
            ec2.BlockDevice(
                device_name=device_name_root,
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=volume_size_root,
                    volume_type=volume_type_root,
                    delete_on_termination=True,
                    encrypted=True,
                ),
            ),
            ec2.BlockDevice(
                device_name=device_name_home,
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=volume_size_home,
                    volume_type=volume_type_home,
                    delete_on_termination=True,
                    encrypted=True,
                ),
            ),
        ]

        user_data = ec2.UserData.for_linux()
        (
            user_data.add_commands(
                "#!/bin/bash -xe\n"
                "# Mount the home volume in /home\n"
                "# create mount point directory\n"
                "mkdir /mnt/tmp\n"
                f"mkfs -t ext4 /dev/{volume_hdd_type_home}\n"
                f"mount -t ext4 /dev/{volume_hdd_type_home} /mnt/tmp\n"
                "cp -rp /home/* /mnt/tmp/\n"
                "umount /mnt/tmp\n"
                "# create ext4 filesystem on new volume\n"
                "# add an entry to fstab to mount volume during boot\n"
                f'echo "/dev/{volume_hdd_type_home}        /home   ext4    defaults,nofail 0       2" >> /etc/fstab\n'
                "# mount the volume on current boot\n"
                "mount -a\n"
                "INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)\n"
                "# Save instance id\n"
                'echo "$INSTANCE_ID" > /var/log/instance-id.log\n'
            ),
        )

        if machine_type == "Testing":
            user_data.add_commands(
                "sudo apt-get update  &> /dev/null || true\n" "sudo apt-get -y install [CUSTOM APP only for this machine type] \n"
            )

        # Create a Launch Template
        launch_template = ec2.LaunchTemplate(
            self,
            f"{machine_type}LaunchTemplate",
            launch_template_name=f"{machine_type}LaunchTemplate",
            instance_type=ec2.InstanceType(instance_type),
            machine_image=machine_image,
            block_devices=block_devices,
            user_data=user_data,
        )

        # Add network configuration and key pair to the launch template
        cfn_launch_template = launch_template.node.default_child
        cfn_launch_template.add_property_override(
            "LaunchTemplateData.NetworkInterfaces",
            [
                {
                    "DeviceIndex": 0,
                    "Groups": [properties["sg.id"]],
                    "SubnetId": properties["subnet.private.id"],
                    "DeleteOnTermination": True,
                    "AssociatePublicIpAddress": False,
                    "InterfaceType": "interface",
                }
            ],
        )
        cfn_launch_template.add_property_override("LaunchTemplateData.KeyName", properties["ec2.keypair.id"])

        cfn_launch_template.add_property_override(
            "LaunchTemplateData.MetadataOptions",
            {
                "HttpEndpoint": "enabled",
            },
        )

        cfn_launch_template.add_property_override(
            "LaunchTemplateData.IamInstanceProfile", {"Arn": properties["ec2.instance.profile.arn"]}
        )

        cfn_launch_template.add_property_override(
            "LaunchTemplateData.PrivateDnsNameOptions",
            {"EnableResourceNameDnsARecord": False, "EnableResourceNameDnsAAAARecord": False},
        )

        # Set the master instance 
        machine_name = f"Custom-{machine_type}-machine"
        cfn_launch_template.add_property_override(
            "LaunchTemplateData.TagSpecifications",
            [
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "MachineType", "Value": machine_type},
                        {"Key": "Name", "Value": machine_name},
                        {"Key": "CanTerminate", "Value": "False"},
                        {"Key": "MachineNumber", "Value": "1"},
                        {"Key": "IsMaster", "Value": "True"},
                    ],
                },
            ],
        )

        # Output the Launch Template ID
        CfnOutput(
            self,
            f"{machine_type}LaunchTemplateId",
            value=launch_template.launch_template_id,
            description=f"{machine_type} launch Template ID",
        )

        # Output the Launch Template Version
        CfnOutput(
            self,
            f"{machine_type}LatestLaunchTemplateVersion",
            value=launch_template.latest_version_number,
            description=f"{machine_type} latest version",
        )
