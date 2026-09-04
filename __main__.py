import os
import glob
import yaml
import pulumi
import pulumi_netbox as netbox

# 1. Read 'serverUrl' directly from Pulumi.dev.yaml config
config = pulumi.Config("netbox")
server_url = config.get("serverUrl")

# Read API Token from GitHub Action environment variable
api_token = os.getenv("NETBOX_DEV_TOKEN")

# Validate configuration before proceeding
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

    if not site_data or not isinstance(site_data, dict) or "slug" not in site_data:
        pulumi.log.warn(f"Skipping invalid YAML file (missing 'slug'): {file_path}")
        continue

    site_slug = site_data["slug"]
    site_name = site_data.get("site_name", site_slug)

    # Provision NetBox Site using the configured provider
    site = netbox.Site(
        f"site-{site_slug}",
        name=site_name,
        slug=site_slug,
        status=site_data.get("status", "active"),
        comments=site_data.get("description", ""),
        opts=pulumi.ResourceOptions(provider=netbox_provider),
    )

    created_sites[site_slug] = site.id

# Export stack outputs
pulumi.export("deployed_sites", created_sites)