import glob
import os
import yaml
import pulumi
import pulumi_netbox as netbox

# Container to export created resources
created_sites = {}

# 1. Locate all YAML files in the inputs directory
input_files = glob.glob(os.path.join("inputs/site", "*.yaml"))

if not input_files:
    pulumi.log.warn("No site input files found in inputs/site folder.")

# 2. Iterate through each site file and provision resources
for file_path in input_files:
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)

    site_slug = config["slug"]
    site_name = config["site_name"]

    # Create NetBox Site Resource
    site = netbox.Site(
        f"site-{site_slug}",
        name=site_name,
        slug=site_slug,
        status="active",
        comments=config.get("description", ""),
    )

    # Create ASN if specified
    asn_resource = None
    if "facilities" in config and "asn" in config["facilities"]:
        asn_val = config["facilities"]["asn"]
        asn_resource = netbox.Asn(
            f"asn-{site_slug}-{asn_val}",
            asn=asn_val,
            rir_id=1,  # Example RIR ID
        )

    # Create Prefixes under this Site
    if "facilities" in config and "prefixes" in config["facilities"]:
        for prefix_cidr in config["facilities"]["prefixes"]:
            # Format resource name cleanly for Pulumi tracking
            resource_safe_prefix = prefix_cidr.replace("/", "_").replace(".", "_")

            netbox.Prefix(
                f"prefix-{site_slug}-{resource_safe_prefix}",
                prefix=prefix_cidr,
                site_id=site.id,  # Wire dependency directly to the created Site ID
                status="active",
            )

    # Save created site ID for Pulumi Outputs
    created_sites[site_slug] = site.id

# 3. Export all deployed Site IDs as stack outputs
pulumi.export("deployed_sites", created_sites)