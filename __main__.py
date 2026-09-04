import os
import glob
import yaml
import pulumi
import pulumi_netbox as netbox

# 1. Configuration & Provider Setup
config = pulumi.Config("netbox")
server_url = config.get("serverUrl")
api_token = os.getenv("NETBOX_DEV_TOKEN")

if not server_url:
    raise ValueError("Missing 'netbox:serverUrl' in stack configuration file.")
if not api_token:
    raise ValueError("Missing 'NETBOX_DEV_TOKEN' environment variable.")

netbox_provider = netbox.Provider(
    "netbox-provider",
    server_url=server_url,
    api_token=api_token,
)

# Global resource options
opts = pulumi.ResourceOptions(provider=netbox_provider)

# Options specifically for Prefixes to ensure old subnets are deleted before replaced
prefix_opts = pulumi.ResourceOptions(
    provider=netbox_provider,
    delete_before_replace=True,
)

# Standard VLAN specifications relative to network_id input
VLAN_SPECS = [
    {"vid": 64,  "name": "Security", "offset": 64,  "mask": 21},
    {"vid": 72,  "name": "IOT",      "offset": 72,  "mask": 21},
    {"vid": 136, "name": "CORP",     "offset": 136, "mask": 21},
    {"vid": 200, "name": "AV",       "offset": 200, "mask": 21},
    {"vid": 240, "name": "Guest",    "offset": 240, "mask": 21},
    {"vid": 255, "name": "MGMT",     "offset": 254, "mask": 23},
]

# Track region resources in memory across all YAML files in the stack
region_resources = {}
created_sites = {}


def get_or_create_region(region_name: str, parent_region_id=None):
    """
    Ensures a single netbox.Region Pulumi resource is registered per unique slug.
    Reuses the existing Pulumi resource if referenced multiple times across site files.
    """
    slug = region_name.lower().strip().replace(" ", "-")

    if slug not in region_resources:
        resource_args = {
            "name": region_name,
            "slug": slug,
        }
        if parent_region_id is not None:
            resource_args["parent_region_id"] = parent_region_id

        prefix = "subregion" if parent_region_id is not None else "region"

        region_resources[slug] = netbox.Region(
            f"{prefix}-{slug}",
            **resource_args,
            opts=opts,
        )

    return region_resources[slug]


# 2. Process All Input YAML Files
input_files = sorted(glob.glob("inputs/site/*.yaml") + glob.glob("inputs/site/*.yml"))

if not input_files:
    pulumi.log.warn("No site input files found in inputs/site/ directory.")

for file_path in input_files:
    try:
        with open(file_path, "r") as f:
            site_data = yaml.safe_load(f)
    except Exception as e:
        pulumi.log.error(f"Failed to read file {file_path}: {e}")
        continue

    if not site_data or not isinstance(site_data, dict) or "site_code" not in site_data:
        pulumi.log.warn(f"Skipping invalid YAML file (missing 'site_code'): {file_path}")
        continue

    site_code = site_data["site_code"]
    site_slug = site_code.lower()
    site_name = site_data.get("site_name", site_code)
    net_id = site_data.get("network_id")

    # A. Parent Region (e.g., APAC, EMEA)
    parent_region = None
    if site_data.get("region"):
        parent_region = get_or_create_region(site_data["region"])

    # B. Subregion (e.g., IND, JPN, UK)
    sub_region = None
    if site_data.get("subregion"):
        parent_id = parent_region.id if parent_region else None
        sub_region = get_or_create_region(site_data["subregion"], parent_region_id=parent_id)

    # C. Site Resource Creation
    site_args = {
        "name": site_name,
        "slug": site_slug,
        "status": "active",
        "comments": f"Country: {site_data.get('country', 'N/A')}",
    }

    # Assign region precedence (Subregion > Parent Region)
    if sub_region:
        site_args["region_id"] = sub_region.id
    elif parent_region:
        site_args["region_id"] = parent_region.id

    site = netbox.Site(
        f"site-{site_slug}",
        **site_args,
        opts=opts,
    )

    # D. Location Hierarchy & Rack Allocation
    floors = site_data.get("floors", [])
    for fl in floors:
        fl_num = str(fl["floor_number"]).zfill(2)
        rooms = fl.get("rooms", [])

        for rm in rooms:
            rm_type = rm["type"]  # IDF or MDF
            location_name = f"{site_code}-{fl_num}-{rm_type}"
            location_slug = location_name.lower()

            location = netbox.Location(
                f"loc-{location_slug}",
                name=location_name,
                slug=location_slug,
                site_id=site.id,
                opts=opts,
            )

            rack_count = rm.get("racks_count", 0)
            for r in range(1, rack_count + 1):
                rack_num = str(r).zfill(2)
                rack_name = f"{location_name}-R{rack_num}"

                netbox.Rack(
                    f"rack-{rack_name.lower()}",
                    name=rack_name,
                    site_id=site.id,
                    location_id=location.id,
                    status="active",
                    width=19,
                    opts=opts,
                )

    # E. Network & VLAN Subnet Allocation
    if net_id is not None:
        parent_cidr = f"10.{net_id}.0.0/16"

        # Parent /16 Prefix Resource
        netbox.Prefix(
            f"prefix-{site_slug}-10_{net_id}_0_0_16",
            prefix=parent_cidr,
            site_id=site.id,
            status="active",
            description=f"Global Prefix for {site_code}",
            opts=prefix_opts,
        )

        # VLAN and Specific Subnet Resources
        for vspec in VLAN_SPECS:
            vid = vspec["vid"]
            vname = vspec["name"]
            offset = vspec["offset"]
            mask = vspec["mask"]

            vlan_prefix_cidr = f"10.{net_id}.{offset}.0/{mask}"

            vlan = netbox.Vlan(
                f"vlan-{site_slug}-{vid}",
                vid=vid,
                name=vname,
                site_id=site.id,
                status="active",
                opts=opts,
            )

            netbox.Prefix(
                f"prefix-{site_slug}-{vid}",
                prefix=vlan_prefix_cidr,
                site_id=site.id,
                vlan_id=vlan.id,
                status="active",
                description=f"{vname} Subnet",
                opts=prefix_opts,
            )

    created_sites[site_code] = site.id

# Stack Outputs
pulumi.export("deployed_sites", created_sites)
