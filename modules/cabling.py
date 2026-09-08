import pulumi
import pulumi_netbox as netbox


class CablingModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts

    def connect_interfaces(
        self,
        cable_id_name: str,
        a_device_id: pulumi.Output,
        a_interface_name: str,
        b_device_id: pulumi.Output,
        b_interface_name: str,
        cable_type: str = "cat6a",
        cable_status: str = "connected",
        **kwargs,
    ):
        cable_slug = cable_id_name.lower().replace("/", "-")

        # Create Side A Interface
        int_a = netbox.Interface(
            f"int-a-{cable_slug}",
            name=a_interface_name,
            device_id=a_device_id,
            type="10gbase-x-sfpp",
            opts=self.opts,
        )

        # Create Side B Interface
        int_b = netbox.Interface(
            f"int-b-{cable_slug}",
            name=b_interface_name,
            device_id=b_device_id,
            type="10gbase-x-sfpp",
            opts=self.opts,
        )

        # Create Cable Connection
        cable = netbox.Cable(
            f"cable-{cable_slug}",
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
            type=cable_type,
            status=cable_status,
            opts=self.opts,
        )

        return cable