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
        status: str = "connected",
        cable_type: str = "cat6a",
    ):
        """
        Establishes a physical cable link between two device interfaces.
        """
        # 1. Instantiate Interface A
        interface_a = netbox.Interface(
            f"intf-{cable_id_name}-a",
            device_id=a_device_id,
            name=a_interface_name,
            type="1000base-t",
            opts=self.opts,
        )

        # 2. Instantiate Interface B
        interface_b = netbox.Interface(
            f"intf-{cable_id_name}-b",
            device_id=b_device_id,
            name=b_interface_name,
            type="1000base-t",
            opts=self.opts,
        )

        # 3. Create Cable Object connecting A and B
        cable = netbox.Cable(
            f"cable-{cable_id_name}",
            a_terminations=[
                netbox.CableATerminationArgs(
                    object_id=interface_a.id,
                    object_type="dcim.interface",
                )
            ],
            b_terminations=[
                netbox.CableBTerminationArgs(
                    object_id=interface_b.id,
                    object_type="dcim.interface",
                )
            ],
            status=status,
            type=cable_type,
            opts=self.opts.merge(
                pulumi.ResourceOptions(depends_on=[interface_a, interface_b])
            ),
        )

        return cable