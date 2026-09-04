import pulumi
import pulumi_netbox as netbox

# Load stack configuration values
config = pulumi.Config()
env = config.require("environment")
region_slug = config.require("region_slug")
netbox_url = config.require("netbox_url")

# Explicitly configure the NetBox provider using the stack's URL
# (Note: NETBOX_API_TOKEN is automatically picked up from the environment variable)
provider = netbox.Provider("netbox-provider",
    endpoint=netbox_url
)

# Create a dynamic NetBox region using the explicitly defined provider
region = netbox.Region(f"region-{env}",
    name=f"US East ({env.upper()})",
    slug=region_slug,
    description=f"Primary geographic region managed by Pulumi ({env} environment)",
    opts=pulumi.ResourceOptions(provider=provider)
)

# Export key resource outputs for CI/CD logs
pulumi.export("region_id", region.id)
pulumi.export("region_name", region.name)
pulumi.export("region_slug", region.slug)
pulumi.export("environment", env)
pulumi.export("netbox_endpoint", netbox_url)