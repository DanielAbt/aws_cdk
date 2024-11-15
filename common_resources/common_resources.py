from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class CommonResources:
    def __init__(self, scope: Construct):
        self.scope = scope

    def get_volume_type(self, type_string):
        volume_type_map = {
            "standard": ec2.EbsDeviceVolumeType.STANDARD,
            "io1": ec2.EbsDeviceVolumeType.IO1,
            "io2": ec2.EbsDeviceVolumeType.IO2,
            "gp2": ec2.EbsDeviceVolumeType.GP2,
            "gp3": ec2.EbsDeviceVolumeType.GP3,
            "st1": ec2.EbsDeviceVolumeType.ST1,
            "sc1": ec2.EbsDeviceVolumeType.SC1,
        }
        return volume_type_map.get(type_string.lower(), ec2.EbsDeviceVolumeType.GP2)
