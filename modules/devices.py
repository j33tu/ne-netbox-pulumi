import pulumi
import pulumi_netbox as netbox

class DeviceModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts
        self.devices = {}

    def create_site_devices(self, site_code: str, site_id: pulumi.Output, rack_id: pulumi.Output, devices_data: list):
        for dev in devices_data:
            dev_name = f"{site_code}-{dev['name']}"
            
            self.devices[dev_name] = netbox.Device(
                f"device-{dev_name.lower()}",
                name=dev_name,
                site_id=site_id,
                rack_id=rack_id,
                position=dev.get("position"),
                face=dev.get("face", "front"),
                device_type_id=dev["device_type_id"],
                device_role_id=dev["device_role_id"],
                status="active",
                opts=self.opts
            )