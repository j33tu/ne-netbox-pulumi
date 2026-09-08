import pulumi
import pulumi_netbox as netbox


class DevicesModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts
        self._shared_cache = {}

    def _get_or_create_manufacturer(self, name: str):
        slug = name.lower().replace(" ", "-")
        if slug not in self._shared_cache:
            self._shared_cache[slug] = netbox.Manufacturer(
                f"mfg-{slug}",
                name=name,
                slug=slug,
                opts=self.opts,
            )
        return self._shared_cache[slug]

    def _get_or_create_device_role(self, name: str, color_hex: str = "00ff00"):
        slug = name.lower().replace(" ", "-")
        if slug not in self._shared_cache:
            self._shared_cache[slug] = netbox.DeviceRole(
                f"role-{slug}",
                name=name,
                slug=slug,
                color_hex=color_hex,
                opts=self.opts,
            )
        return self._shared_cache[slug]

    def _get_or_create_device_type(self, model: str, manufacturer_id: pulumi.Output, u_height: int = 1):
        slug = model.lower().replace(" ", "-")
        if slug not in self._shared_cache:
            self._shared_cache[slug] = netbox.DeviceType(
                f"devtype-{slug}",
                model=model,
                slug=slug,
                manufacturer_id=manufacturer_id,
                u_height=u_height,
                opts=self.opts,
            )
        return self._shared_cache[slug]

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
            rack_position=position,
            face="front",
            device_type_id=dev_type.id,
            role_id=dev_role.id,
            status="active",
            opts=self.opts,
        )

        return device