import pulumi
import pulumi_netbox as netbox


class InfrastructureModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts
        self.region_resources = {}

    def get_or_create_region(self, region_name: str, parent_region_id=None):
        slug = region_name.lower().strip().replace(" ", "-")

        if slug not in self.region_resources:
            resource_args = {"name": region_name, "slug": slug}
            if parent_region_id is not None:
                resource_args["parent_region_id"] = parent_region_id

            prefix = "subregion" if parent_region_id is not None else "region"

            self.region_resources[slug] = netbox.Region(
                f"{prefix}-{slug}",
                **resource_args,
                opts=self.opts,
            )

        return self.region_resources[slug]

    def create_site_infrastructure(self, site_data: dict):
        site_code = site_data["site_code"]
        site_slug = site_code.lower()
        site_name = site_data.get("site_name", site_code)

        # Regions
        parent_region = None
        if site_data.get("region"):
            parent_region = self.get_or_create_region(site_data["region"])

        sub_region = None
        if site_data.get("subregion"):
            parent_id = parent_region.id if parent_region else None
            sub_region = self.get_or_create_region(
                site_data["subregion"], parent_region_id=parent_id
            )

        # Site
        site_args = {
            "name": site_name,
            "slug": site_slug,
            "status": "active",
            "comments": f"Country: {site_data.get('country', 'N/A')}",
        }
        if sub_region:
            site_args["region_id"] = sub_region.id
        elif parent_region:
            site_args["region_id"] = parent_region.id

        site = netbox.Site(
            f"site-{site_slug}",
            **site_args,
            opts=self.opts,
        )

        # Locations & Racks
        floors = site_data.get("floors", [])
        for fl in floors:
            fl_num = str(fl["floor_number"]).zfill(2)
            for rm in fl.get("rooms", []):
                rm_type = rm["type"]
                location_name = f"{site_code}-{fl_num}-{rm_type}"
                location_slug = location_name.lower()

                location = netbox.Location(
                    f"loc-{location_slug}",
                    name=location_name,
                    slug=location_slug,
                    site_id=site.id,
                    opts=self.opts,
                )

                for r in range(1, rm.get("racks_count", 0) + 1):
                    rack_num = str(r).zfill(2)
                    rack_name = f"{location_name}-R{rack_num}"

                    netbox.Rack(
                        f"rack-{rack_name.lower()}",
                        name=rack_name,
                        site_id=site.id,
                        location_id=location.id,
                        status="active",
                        width=19,
                        opts=self.opts,
                    )

        return site