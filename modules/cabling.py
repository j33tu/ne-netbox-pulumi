import pulumi
import pulumi_netbox as netbox

class CablingModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts
        self.cables = {}

    def connect_interfaces(self, link_id: str, termination_a_id: pulumi.Output, termination_b_id: pulumi.Output, cable_type: str = "cat6a"):
        self.cables[link_id] = netbox.Cable(
            f"cable-{link_id}",
            a_terminations=[{"object_type": "dcim.interface", "object_id": termination_a_id}],
            b_terminations=[{"object_type": "dcim.interface", "object_id": termination_b_id}],
            type=cable_type,
            status="connected",
            opts=self.opts
        )