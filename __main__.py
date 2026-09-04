import os
import sys
import yaml
import pulumi
import pulumi_netbox as netbox

# ------------------------------------------------------------------------------
# 1. READ STACK CONFIG
# ------------------------------------------------------------------------------
pulumi_config = pulumi.Config()
netbox_url = pulumi_config.require("netbox_url")
environment = pulumi_config.get("environment") or "dev"

# ------------------------------------------------------------------------------
# 2. FETCH DEV SECRET FROM CI/CD ENVIRONMENT
# ------------------------------------------------------------------------------
netbox_dev_token = os.getenv("NETBOX_DEV_TOKEN")

if not netbox_dev_token:
    pulumi.log.error(
        "CRITICAL: NETBOX_DEV_TOKEN environment variable is missing from CI/CD runner context."
    )
    sys.exit(1)

# ------------------------------------------------------------------------------
# 3. INITIALIZE NETBOX PROVIDER FOR DEV
# ------------------------------------------------------------------------------
netbox_provider = netbox.Provider(
    "dev-netbox-provider",
    server_url=netbox_url,
    api_token=netbox_dev_token,
)

# ------------------------------------------------------------------------------
# 4. LOAD INPUT YAML DATA
# ------------------------------------------------------------------------------
def load_yaml(file_path: str) -> dict:
    if not os.path.exists(file_path):
        pulumi.log.warn(f"File not found: {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

site_data = load_yaml(os.path.join("inputs", "site", "site.yaml"))
vendors_data = load_yaml(os.path.join("inputs", "sync", "vendors.yaml"))

# ------------------------------------------------------------------------------
# 5. DEFINE RESOURCES ON DEV NETBOX
# ------------------------------------------------------------------------------
site_name = site_data.get("name", f"Site-{environment}")
site_slug = site_data.get("slug", f"{environment}-site")

netbox_site = netbox.Site(
    "dev-netbox-site",
    name=site_name,
    slug=site_slug,
    status="active",
    opts=pulumi.ResourceOptions(provider=netbox_provider),
)

# Outputs
pulumi.export("target_netbox_url", netbox_url)
pulumi.export("created_site_name", netbox_site.name)
