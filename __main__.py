import glob
import os
import pulumi
import pulumi_netbox as netbox
import yaml

from modules.infrastructure import InfrastructureModule
from modules.ipam import IPAMModule
from modules.devices import DevicesModule
from modules.cabling import CablingModule

# Configuration & Provider Setup
config = pulumi.Config("netbox")
server_url = config.get("serverUrl")
api_token = os.getenv("NETBOX_DEV_TOKEN")

netbox_provider = netbox.Provider(
    "netbox-provider",
    server_url=server_url,
    api_token=api_token,
)

opts = pulumi.ResourceOptions(provider=netbox_provider)

# Instantiate Domain Modules
infra_mod = InfrastructureModule(opts=opts)
ipam_mod = IPAMModule(opts=opts)
devices_mod = DevicesModule(opts=opts)
cabling_mod = CablingModule(opts=opts)

input_files = sorted(glob.glob("inputs/site/*.yaml") + glob.glob("inputs/site/*.yml"))

for file_path in input_files:
    with open(file_path, "r") as f:
        site_data = yaml.safe_load(f)

    if not site_data or "site_code" not in site_data:
        continue

    site_code = site_data["site_code"]
    net_id = site_data.get("network_id")

    # 1. Infrastructure (Site, Locations, Racks)
    site = infra_mod.create_site_infrastructure(site_data)

    # 2. IPAM (VLANs & Subnets)
    if net_id is not None:
        ipam_mod.create_site_ipam(site_code=site_code, site_id=site.id, net_id=net_id)

    # 3. Devices
    created_devices = {}
    floors = site_data.get("floors", [])
    for fl in floors:
        fl_num = str(fl["floor_number"]).zfill(2)
        for rm in fl.get("rooms", []):
            rm_type = rm["type"]
            location_slug = f"{site_code}-{fl_num}-{rm_type}".lower()
            
            # Fetch created Location reference
            location = infra_mod.location_resources.get(location_slug)

            for dev_cfg in rm.get("devices", []):
                rack_name = f"{site_code}-{fl_num}-{rm_type}-R01".lower()
                rack = infra_mod.rack_resources.get(rack_name)

                device = devices_mod.create_device(
                    name=dev_cfg["name"],
                    site_id=site.id,
                    location_id=location.id if location else None,
                    rack_id=rack.id if rack else None,
                    position=dev_cfg.get("position", 1),
                    model=dev_cfg.get("model", "Generic Switch"),
                    manufacturer=dev_cfg.get("manufacturer", "Generic"),
                    role=dev_cfg.get("role", "Access Switch"),
                )
                created_devices[dev_cfg["name"]] = device

    # 4. Cabling (Depends on Devices)
    for cable_cfg in site_data.get("cabling", []):
        dev_a = created_devices.get(cable_cfg["device_a"])
        dev_b = created_devices.get(cable_cfg["device_b"])

        if dev_a and dev_b:
            cabling_mod.connect_interfaces(
                cable_id_name=cable_cfg["id"],
                a_device_id=dev_a.id,
                a_interface_name=cable_cfg["interface_a"],
                b_device_id=dev_b.id,
                b_interface_name=cable_cfg["interface_b"],
                cable_type=cable_cfg.get("type", "cat6a"),
            )

pulumi.export("status", "Deployment Completed Successfully")