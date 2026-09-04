# E. Network & VLAN Setup
    if net_id is not None:
        parent_cidr = f"10.{net_id}.0.0/16"
        
        # Parent /16 Prefix
        netbox.Prefix(
            f"prefix-{site_slug}-10_{net_id}_0_0_16",
            prefix=parent_cidr,
            site_id=site.id,
            status="active",
            description=f"Global Prefix for {site_code}",
            opts=pulumi.ResourceOptions(
                provider=netbox_provider,
                delete_before_replace=True,  # Crucial: Releases old IP space before creating new
            ),
        )

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
                opts=pulumi.ResourceOptions(
                    provider=netbox_provider,
                    delete_before_replace=True,
                ),
            )