import pulumi
import pulumi_netbox as netbox


class DevicesModule:
    # ... [keep your existing __init__ and helper methods unchanged] ...

    def create_device(
        self,
        name: str,
        site_id: pulumi.Output,
        location_id: pulumi.Output,
        rack_id: pulumi.Output,
        position: int,
        model: str = "Catalyst 9300",
        manufacturer: str = "Cisco",
        role: str = "Access Switch",
    ):
        dev_slug = name.lower().replace(" ", "-")

        mfg = self._get_or_create_manufacturer(manufacturer)
        dev_role = self._get_or_create_device_role(role)
        dev_type = self._get_or_create_device_type(model, mfg.id)

        device = netbox.Device(
            f"device-{dev_slug}",
            name=name,
            site_id=site_id,
            location_id=location_id,
            rack_id=rack_id,
            rack_position=position,  # <-- FIXED: changed 'position' to 'rack_position'
            face="front",
            device_type_id=dev_type.id,
            role_id=dev_role.id,
            status="active",
            opts=self.opts,
        )

        return device