import os
import glob
import yaml
import pulumi
import pulumi_netbox as netbox

from modules.infrastructure import InfrastructureModule
from modules.ipam import IPAMModule
from modules.devices import DeviceModule
from modules.cabling import CablingModule

# 1. Config & Provider Setup
config = pulumi.Config("netbox")
server_url = config.get("serverUrl")
api_token = os.getenv("NETBOX_DEV_TOKEN")

if not server_url or not api_token:
    raise ValueError("Missing NetBox serverUrl configuration or NETBOX_DEV_TOKEN variable.")

netbox_provider = netbox.Provider("netbox-provider", server_url=server_url, api_token=api_token)
opts = pulumi.ResourceOptions(provider=netbox_provider)

# 2. Instantiate Modules
infra_mod = InfrastructureModule(opts)
ipam_mod = IPAMModule(opts)
device_mod = DeviceModule(opts)
cabling_mod = CablingModule(opts)

# 3. Process Site YAMLs
input_files = sorted(glob.glob("inputs/site/*.yaml") + glob.glob("inputs/site/*.yml"))

for file_path in input_files:
    with open(file_path, "r") as f:
        site_data = yaml.safe_load(f)

    if not site_data or "site_code" not in site_data:
        continue

    site_code = site_data["site_code"]

    # Step 1: Deploy Infrastructure (Sites, Locations, Racks)
    site = infra_mod.create_site_infrastructure(site_data)

    # Step 2: Deploy IPAM Specs
    if site_data.get("network_id") is not None:
        ipam_mod.create_site_ipam(site_code, site.id, site_data["network_id"])

    # Step 3: Deploy Devices (Optional section in YAML)
    if "devices" in site_data:
        # Example: placing devices on the first rack available
        first_rack = list(infra_mod.racks.values())[0]
        device_mod.create_site_devices(site_code, site.id, first_rack.id, site_data["devices"])

    # Step 4: Patching & Connections
    if "connections" in site_data:
        for conn in site_data["connections"]:
            cabling_mod.connect_interfaces(
                conn["id"], 
                conn["a_interface_id"], 
                conn["b_interface_id"]
            )

# Stack Outputs
pulumi.export("deployed_sites", {k: v.id for k, v in infra_mod.sites.items()})