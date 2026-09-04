import os
import sys
import yaml
import pulumi
import pulumi_netbox as netbox

# ------------------------------------------------------------------------------
# 1. DETECT ACTIVE STACK & LOAD STACK CONFIG
# ------------------------------------------------------------------------------
current_stack = pulumi.get_stack().lower()  # Returns "dev", "prod", etc.
pulumi_config = pulumi.Config()

# Reads 'ne-netbox-pulumi:netbox_url' from Pulumi.<stack>.yaml
netbox_url = pulumi_config.require("netbox_url")
environment = pulumi_config.get("environment") or current_stack


# ------------------------------------------------------------------------------
# 2. MAP & VALIDATE ENVIRONMENT TOKEN
# ------------------------------------------------------------------------------
# Choose token based on active stack name, falling back to NETBOX_API_TOKEN if present
if "prod" in current_stack:
    netbox_api_token = os.getenv("NETBOX_PROD_TOKEN") or os.getenv("NETBOX_API_TOKEN")
    expected_var = "NETBOX_PROD_TOKEN"
else:
    netbox_api_token = os.getenv("NETBOX_DEV_TOKEN") or os.getenv("NETBOX_API_TOKEN")
    expected_var = "NETBOX_DEV_TOKEN"

if not netbox_api_token:
    pulumi.log.error(
        f"CRITICAL: Missing API token for stack '{current_stack}'. "
        f"Ensure environment variable '{expected_var}' is set in your pipeline."
    )
    sys.exit(1)


# ------------------------------------------------------------------------------
# 3. INITIALIZE NETBOX PROVIDER
# ------------------------------------------------------------------------------
netbox_provider = netbox.Provider(
    "netbox-provider",
    server_url=netbox_url,
    api_token=netbox_api_token,
)


# ------------------------------------------------------------------------------
# 4. READ YAML INPUT FILES
# ------------------------------------------------------------------------------
def load_yaml(file_path: str) -> dict:
    if not os.path.exists(file_path):
        pulumi.log.warn(f"Input file not found: {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

site_data = load_yaml(os.path.join("inputs", "site", "site.yaml"))
vendors_data = load_yaml(os.path.join("inputs", "sync", "vendors.yaml"))


# ------------------------------------------------------------------------------
# 5. DEFINE NETBOX RESOURCES
# ------------------------------------------------------------------------------
site_name = site_data.get("name", f"Site-{environment}")
site_slug = site_data.get("slug", f"{environment}-site")

netbox_site = netbox.Site(
    f"{environment}-netbox-site",
    name=site_name,
    slug=site_slug,
    status="active",
    opts=pulumi.ResourceOptions(provider=netbox_provider),
)


# ------------------------------------------------------------------------------
# 6. EXPORT OUTPUTS
# ------------------------------------------------------------------------------
pulumi.export("active_stack", current_stack)
pulumi.export("configured_netbox_url", netbox_url)
pulumi.export("site_name", netbox_site.name)
