import os
import glob
import yaml
import pulumi
import pulumi_netbox as netbox

# 1. Read 'serverUrl' directly from Pulumi config
config = pulumi.Config("netbox")
server_url = config.get("serverUrl")

# Read API Token from GitHub Action environment variable
api_token = os.getenv("NETBOX_DEV_TOKEN")

# Validate configuration
if not server_url:
    raise ValueError("Missing 'netbox:serverUrl' in stack configuration file (Pulumi.dev.yaml).")
if not api_token:
    raise ValueError("Missing 'NETBOX_DEV_TOKEN' environment variable in CI/CD pipeline.")

# 2. Instantiate explicit NetBox Provider
netbox_provider = netbox.Provider(
    "netbox-provider",
    server_url=server_url,
    api_token=api_token,
)

opts = pulumi.ResourceOptions(provider=netbox_provider)

# Standard VLAN specifications relative to network_id
VLAN_SPECS = [
    {"vid": 64,  "name": "Security", "offset": 64,  "mask": 21},
    {"vid": 72,  "name": "IOT",      "offset": 72,  "mask": 21},
    {"vid": 136, "name": "CORP",     "offset": 136, "mask": 21},
    {"vid": 200, "name": "AV",       "offset": 200, "mask": 21},
    {"vid": 240, "name": "Guest",    "offset": 240, "mask": 21},
    {"vid": 255, "name": "MGMT",     "offset": 254, "mask": 23},
]

created_sites = {}

# 3. Target site input files strictly inside inputs/site/
input_files = glob.glob("inputs/site/*.yaml") + glob.glob("inputs/site/*.yml")

if not input_files:
    pulumi.log.warn("No site input files found in inputs/site/ directory.")

# 4. Iterate over site definition files
for file_path in input_files:
    try:
        with open(file_path, "r") as f:
            site_data = yaml.safe_load(f)
    except Exception as e:
        pulumi.log.error(f"Failed to read file {file_path}: {e}")
        continue

    # Validate mandatory schema field
    if not site_data or not isinstance(site_data, dict) or "site_code" not in site_data:
        pulumi.log.warn(f"Skipping invalid YAML file (missing 'site_code'): {file_path}")
        continue

    site_code = site_data["site_code"]
    site_name = site_data.get("site_name", site_code)
    net_id = site_data.get("network_id")

    # A. Region Hierarchy Creation (APAC -> IND)
    parent_region = None
    if "region" in site_data:
        region_name = site_data["region"]
        parent_region = netbox.Region(
            f"region-{region_name.lower()}",
            name=region_name,
            slug=region_name.lower(),
            opts=opts,
        )

    sub_region = None
    if "subregion" in site_data:
        subregion_name = site_data["subregion"]
        sub_region_args = {
            "name": subregion_name,
            "slug": subregion_name.lower(),
        }
        if parent_region:
            sub_region_args["parent_region_id"] = parent_region.id

        sub_region = netbox.Region(
            f"subregion-{subregion_name.lower()}",
            **sub_region_args,
            opts=opts,
        )

    # B. Site Creation
    site_args = {
        "name": site_name,
        "slug": site_code.lower(),
        "status": "active",
        "comments": f"Country: {site_data.get('country', 'N/A')}",
    }
    if sub_region:
        site_args["region_id"] = sub_region.id
    elif parent_region:
        site_args["region_id"] = parent_region.id

    site = netbox.Site(
        f"site-{site_code.lower()}",
        **site_args,
        opts=opts,
    )

    # C. Floor, Room Location (e.g. BLR01-02-IDF), and Racks (e.g. BLR01-02-IDF-R01)
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

    # D. Network Setup: Parent Prefix (10.input.0.0/16) and VLAN Subnets
    if net_id is not None:
        parent_cidr = f"10.{net_id}.0.0/16"
        parent_prefix = netbox.Prefix(
            f"prefix-{site_code.lower()}-10_{net_id}_0_0_16",
            prefix=parent_cidr,
            site_id=site.id,
            status="active",
            description=f"Global Prefix for {site_code}",
            opts=opts,
        )

        for vspec in VLAN_SPECS:
            vid = vspec["vid"]
            vname = vspec["name"]
            offset = vspec["offset"]
            mask = vspec["mask"]

            vlan_prefix_cidr = f"10.{net_id}.{offset}.0/{mask}"

            vlan = netbox.Vlan(
                f"vlan-{site_code.lower()}-{vid}",
                vid=vid,
                name=vname,
                site_id=site.id,
                status="active",
                opts=opts,
            )

            netbox.Prefix(
                f"prefix-{site_code.lower()}-{vid}",
                prefix=vlan_prefix_cidr,
                site_id=site.id,
                vlan_id=vlan.id,
                status="active",
                description=f"{vname} Subnet",
                opts=opts,
            )

    created_sites[site_code] = site.id

# Export stack outputs
pulumi.export("deployed_sites", created_sites)