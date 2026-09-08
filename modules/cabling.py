import pulumi
import pulumi_netbox as netbox


class CablingModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts

    def create_interface(self, name: str, device_id: pulumi.Output, type: str = "10gbase-x-sfpp"):
        return netbox.Interface(
            f"int-{name.lower().replace('/', '-')}",
            name=name,
            device_id=device_id,  # If device_id failed, try passing device_id or device_id
            type=type,
            opts=self.opts,
        )

    def connect_interfaces(
        self,
        device_a_id: pulumi.Output,
        interface_a_name: str,
        device_b_id: pulumi.Output,
        interface_b_name: str,
        cable_status: str = "connected",
    ):
        # Create Interface A
        int_a = netbox.Interface(
            f"int-a-{interface_a_name.lower().replace('/', '-')}",
            name=interface_a_name,
            device_id=device_a_id,  # <-- Change device_id to device_id if needed or check provider docs
            type="10gbase-x-sfpp",
            opts=self.opts,
        )

        # Create Interface B
        int_b = netbox.Interface(
            f"int-b-{interface_b_name.lower().replace('/', '-')}",
            name=interface_b_name,
            device_id=device_b_id,  # <-- Change device_id to device_id
            type="10gbase-x-sfpp",
            opts=self.opts,
        )

        # Cable connecting both interfaces
        cable = netbox.Cable(
            f"cable-{interface_a_name}-{interface_b_name}".lower().replace("/", "-"),
            a_terminations=[
                netbox.CableATerminationArgs(
                    object_id=int_a.id,
                    object_type="dcim.interface",
                )
            ],
            b_terminations=[
                netbox.CableBTerminationArgs(
                    object_id=int_b.id,
                    object_type="dcim.interface",
                )
            ],
            status=cable_status,
            opts=self.opts,
        )

        return cable