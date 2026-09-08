import pulumi
import pulumi_netbox as netbox


class CablingModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts

    def connect_interfaces(
        self,
        device_a_id: pulumi.Output,
        interface_a_name: str,
        device_b_id: pulumi.Output,
        interface_b_name: str,
        cable_id_name: str = None,  # <-- Added missing keyword argument
        cable_status: str = "connected",
        **kwargs,  # Protects against any future unexpected keyword arguments
    ):
        cable_name = cable_id_name or f"cable-{interface_a_name}-{interface_b_name}"
        resource_slug = cable_name.lower().replace("/", "-")

        # Interface A
        int_a = netbox.Interface(
            f"int-a-{resource_slug}",
            name=interface_a_name,
            device_id=device_a_id,
            type="10gbase-x-sfpp",
            opts=self.opts,
        )

        # Interface B
        int_b = netbox.Interface(
            f"int-b-{resource_slug}",
            name=interface_b_name,
            device_id=device_b_id,
            type="10gbase-x-sfpp",
            opts=self.opts,
        )

        # Cable
        cable = netbox.Cable(
            f"cable-{resource_slug}",
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