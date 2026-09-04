import os
import glob
import yaml
import pulumi
import pulumi_netbox as netbox

# 1. Configuration & Validation
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

opts = pulumi.ResourceOptions(provider=netbox_provider)

# Standard VLAN specifications relative to network_id input
VLAN_SPECS = [
    {"vid": 64,  "name": "Security", "offset": 64,  "mask": 21},
    {"vid": 72,  "name": "IOT",      "offset": 72,  "mask": 21},
    {"vid": 136, "name": "CORP",     "offset": 136, "mask": 21},
    {"vid": 200, "name": "AV",       "offset": 200, "mask": 21},
    {"vid": 240, "name": "Guest",    "offset": 240, "mask": 21},
    {"vid": 255, "name": "MGMT",     "offset": 254, "mask": 23},
]

# Track regions created in the *current* execution run
regions_cache = {}
created_sites = {}


def get_or_create_region(region_name: str, parent_region_id=None) -> pulumi.Output[int]:
    """
    Looks up whether a region exists in NetBox. Reuses it if found,
    or creates a new netbox.Region resource if it doesn't exist.
    """
    slug = region_name.lower().replace(" ", "-")
    cache_key = slug

    if cache_key in regions_cache:
        return regions_cache[cache_key]

    # Check NetBox for an existing region using data lookup
    try:
        existing = netbox.get_region(slug=slug, opts=opts)
        region_id = pulumi.Output.from_input(existing.id)
    except Exception:
        # If lookup fails/not found, create a new Region resource
        resource_args = {
            "name": region_name,
            "slug": slug,
        }
        if parent_region_id is not None:
            resource_args["parent_region_id"] = parent_region_id

        prefix = "subregion" if parent_region_id is not None else "region"
        new_region = netbox.Region(
            f"{prefix}-{slug}",
            **resource_args,
            opts=opts,
        )
        region_id = new_region.id

    regions_cache[cache_key] = region_id
    return region_id


# 2. Processing Input Files
input_files = glob.glob("inputs/site/*.yaml") + glob.glob("inputs/site/*.yml")

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

    # A. Parent Region Lookup or Creation
    parent_region_id = None
    if "region" in site_data and site_data["region"]:
        parent_region_id = get_or_create_region(site_data["region"])

    # B. Subregion Lookup or Creation
    sub_region_id = None
    if "subregion" in site_data and site_data["subregion"]:
        sub_region_id = get_or_create_region(
            site_data["subregion"], 
            parent_region_id=parent_region_id
        )

    # C. Site Resource
    site_args = {
        "name": site_name,
        "slug": site_slug,
        "status": "active",
        "comments": f"Country: {site_data.get('country', 'N/A')}",
    }
    
    # Assign region ID priority (Subregion > Parent Region)
    if sub_region_id is not None:
        site_args["region_id"] = sub_region_id
    elif parent_region_id is not None:
        site_args["region_id"] = parent_region_id

    site = netbox.Site(
        f"site-{site_slug}",
        **site_args,
        opts=opts,
    )

    # D. Location Hierarchy & Racks
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

    # E. Parent Subnet & VLAN Allocation
    if net_id is not None:
        # Create Parent /16 Prefix (e.g., 10.10.0.0/16)
        parent_cidr = f"10.{net_id}.0.0/16"
        netbox.Prefix(
            f"prefix-{site_slug}-10_{net_id}_0_0_16",
            prefix=parent_cidr,
            site_id=site.id,
            status="active",
            description=f"Global Prefix for {site_code}",
            opts=opts,
        )

        # Create Specific VLANs and Subnets
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
                opts=opts,
            )

    created_sites[site_code] = site.id

# Export stack outputs
pulumi.export("deployed_sites", created_sites)