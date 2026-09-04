import pulumi
import pulumi_netbox as netbox

# Create a new top-level region in NetBox
region = netbox.Region("USA",
    name="USA",
    slug="US",
    description="Primary geographic region for US East infrastructure"
)

# Export outputs for visibility in CI/CD logs
pulumi.export("region_id", region.id)
pulumi.export("region_name", region.name)