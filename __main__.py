import glob
import os
import yaml
import pulumi
import pulumi_netbox as netbox

# Dictionary to collect created site IDs for stack exports
created_sites = {}

# 1. Recursively search for all YAML files inside 'inputs/' and any subfolders (e.g., inputs/site/*.yaml)
input_files = glob.glob("inputs/**/*.yaml", recursive=True) + glob.glob("inputs/**/*.yml", recursive=True)

if not input_files:
    pulumi.log.warn("No site input files found in 'inputs/' or any of its subfolders.")

# 2. Iterate through each site file and provision NetBox resources
for file_path in input_files:
    try:
        with open(file_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        pulumi.log.error(f"Failed to read file {file_path}: {e}")
        continue

    # Skip empty files or files without required 'slug' property
    if not config or not isinstance(config, dict) or "slug" not in config:
        pulumi.log.warn(f"Skipping invalid or empty YAML file: {file_path}")
        continue

    site_slug = config["slug"]
    site_name = config.get("site_name", site_slug)

    # Resource: NetBox Site
    site = netbox.Site(
        f"site-{site_slug}",
        name=site_name,
        slug=site_slug,
        status=config.get("status", "active"),
        comments=config.get("description", ""),
    )

    # Resource: NetBox ASN (Optional)
    if "facilities" in config and "asn" in config["facilities"]:
        asn_val = config["facilities"]["asn"]
        netbox.Asn(
            f"asn-{site_slug}-{asn_val}",
            asn=asn_val,
            rir_id=config["facilities"].get("rir_id", 1),
        )

    # Resource: NetBox Prefixes (Optional)
    if "facilities" in config and "prefixes" in config["facilities"]:
        for prefix_cidr in config["facilities"]["prefixes"]:
            # Sanitize prefix string for safe Pulumi resource naming
            resource_safe_prefix = prefix_cidr.replace("/", "_").replace(".", "_")

            netbox.Prefix(
                f"prefix-{site_slug}-{resource_safe_prefix}",
                prefix=prefix_cidr,
                site_id=site.id,  # Implicit dependency on the Site resource above
                status="active",
            )

    # Add created Site ID to export map
    created_sites[site_slug] = site.id

# 3. Export all deployed Site IDs as Pulumi Stack Outputs
pulumi.export("deployed_sites", created_sites)