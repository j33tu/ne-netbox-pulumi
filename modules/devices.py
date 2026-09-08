import pulumi
import pulumi_netbox as netbox
import pynetbox


class DevicesModule:
    def __init__(self, opts: pulumi.ResourceOptions, server_url: str, api_token: str):
        self.opts = opts
        self._shared_cache = {}
        # Direct read-only client used purely to check for pre-existing objects
        # (e.g. seeded by the NetBox Data Exchange import) before asking Pulumi
        # to create them.
        self._nb = pynetbox.api(server_url, token=api_token)

    def _get_or_create_manufacturer(self, name: str):
        slug = name.lower().replace(" ", "-")
        if slug in self._shared_cache:
            return self._shared_cache[slug]

        existing = self._nb.dcim.manufacturers.get(slug=slug)
        if existing:
            pulumi.log.info(f"Manufacturer '{name}' already exists in NetBox (id={existing.id}); adopting it.")
            resource = netbox.Manufacturer.get(f"mfg-{slug}", str(existing.id), opts=self.opts)
        else:
            resource = netbox.Manufacturer(
                f"mfg-{slug}",
                name=name,
                slug=slug,
                opts=self.opts,
            )

        self._shared_cache[slug] = resource
        return resource

    def _get_or_create_device_role(self, name: str, color_hex: str = "00ff00"):
        slug = name.lower().replace(" ", "-")
        if slug in self._shared_cache:
            return self._shared_cache[slug]

        existing = self._nb.dcim.device_roles.get(slug=slug)
        if existing:
            pulumi.log.info(f"DeviceRole '{name}' already exists in NetBox (id={existing.id}); adopting it.")
            resource = netbox.DeviceRole.get(f"role-{slug}", str(existing.id), opts=self.opts)
        else:
            resource = netbox.DeviceRole(
                f"role-{slug}",
                name=name,
                slug=slug,
                color_hex=color_hex,
                opts=self.opts,
            )

        self._shared_cache[slug] = resource
        return resource

    def _get_or_create_device_type(self, model: str, manufacturer_id: pulumi.Output, u_height: int = 1):
        slug = model.lower().replace(" ", "-")
        if slug in self._shared_cache:
            return self._shared_cache[slug]

        existing = self._nb.dcim.device_types.get(slug=slug)
        if existing:
            pulumi.log.info(f"DeviceType '{model}' already exists in NetBox (id={existing.id}); adopting it.")
            resource = netbox.DeviceType.get(f"devtype-{slug}", str(existing.id), opts=self.opts)
        else:
            resource = netbox.DeviceType(
                f"devtype-{slug}",
                model=model,
                slug=slug,
                manufacturer_id=manufacturer_id,
                u_height=u_height,
                opts=self.opts,
            )

        self._shared_cache[slug] = resource
        return resource

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
            rack_face="front",  # <-- FIXED: changed 'face' to 'rack_face'
            device_type_id=dev_type.id,
            role_id=dev_role.id,
            status="active",
            opts=self.opts,
        )

        return device