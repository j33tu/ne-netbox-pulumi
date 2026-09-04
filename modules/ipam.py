import pulumi
import pulumi_netbox as netbox

VLAN_SPECS = [
    {"vid": 64,  "name": "Security", "offset": 64,  "mask": 21},
    {"vid": 72,  "name": "IOT",      "offset": 72,  "mask": 21},
    {"vid": 136, "name": "CORP",     "offset": 136, "mask": 21},
    {"vid": 200, "name": "AV",       "offset": 200, "mask": 21},
    {"vid": 240, "name": "Guest",    "offset": 240, "mask": 21},
    {"vid": 255, "name": "MGMT",     "offset": 254, "mask": 23},
]

class IPAMModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        # Uses delete_before_replace to safely handle IP range updates
        self.prefix_opts = opts.merge(pulumi.ResourceOptions(delete_before_replace=True))
        self.opts = opts
        self.vlans = {}
        self.prefixes = {}

    def create_site_ipam(self, site_code: str, site_id: pulumi.Output, net_id: int):
        site_slug = site_code.lower()
        parent_cidr = f"10.{net_id}.0.0/16"

        # Parent /16 Prefix
        self.prefixes[f"{site_slug}-parent"] = netbox.Prefix(
            f"prefix-{site_slug}-10_{net_id}_0_0_16",
            prefix=parent_cidr,
            site_id=site_id,
            status="active",
            description=f"Global Prefix for {site_code}",
            opts=self.prefix_opts,
        )

        # Child Subnets & VLANs
        for vspec in VLAN_SPECS:
            vid = vspec["vid"]
            vname = vspec["name"]
            offset = vspec["offset"]
            mask = vspec["mask"]

            vlan = netbox.Vlan(
                f"vlan-{site_slug}-{vid}",
                vid=vid,
                name=vname,
                site_id=site_id,
                status="active",
                opts=self.opts,
            )
            self.vlans[f"{site_slug}-{vid}"] = vlan

            self.prefixes[f"{site_slug}-{vid}"] = netbox.Prefix(
                f"prefix-{site_slug}-{vid}",
                prefix=f"10.{net_id}.{offset}.0/{mask}",
                site_id=site_id,
                vlan_id=vlan.id,
                status="active",
                description=f"{vname} Subnet",
                opts=self.prefix_opts,
            )