import pulumi
import pulumi_netbox as netbox

class InfrastructureModule:
    def __init__(self, opts: pulumi.ResourceOptions):
        self.opts = opts
        self.regions = {}
        self.sites = {}
        self.locations = {}
        self.racks = {}

    def get_or_create_region(self, region_name: str, parent_region_id=None):
        slug = region_name.lower().strip().replace(" ", "-")
        if slug not in self.regions:
            resource_args = {"name": region_name, "slug": slug}
            if parent_region_id:
                resource_args["parent_region_id"] = parent_region_id

            prefix = "subregion" if parent_region_id else "region"
            self.regions[slug] = netbox.Region(
                f"{prefix}-{slug}",
                **resource_args,
                opts=self.opts
            )
        return self.regions[slug]

    def create_site_infrastructure(self, site_data: dict):
        site_code = site_data["site_code"]
        site_slug = site_code.lower()
        site_name = site_data.get("site_name", site_code)

        # Parent & Sub-region logic
        parent_reg = self.get_or_create_region(site_data["region"]) if site_data.get("region") else None
        sub_reg = self.get_or_create_region(site_data["subregion"], parent_reg.id) if site_data.get("subregion") else None

        site_args = {
            "name": site_name,
            "slug": site_slug,
            "status": "active",
            "comments": f"Country: {site_data.get('country', 'N/A')}",
        }
        if sub_reg:
            site_args["region_id"] = sub_reg.id
        elif parent_reg:
            site_args["region_id"] = parent_reg.id

        site = netbox.Site(f"site-{site_slug}", **site_args, opts=self.opts)
        self.sites[site_code] = site

        # Floors, Locations & Racks
        for fl in site_data.get("floors", []):
            fl_num = str(fl["floor_number"]).zfill(2)
            for rm in fl.get("rooms", []):
                rm_type = rm["type"]
                loc_name = f"{site_code}-{fl_num}-{rm_type}"
                loc_slug = loc_name.lower()

                location = netbox.Location(
                    f"loc-{loc_slug}",
                    name=loc_name,
                    slug=loc_slug,
                    site_id=site.id,
                    opts=self.opts
                )
                self.locations[loc_name] = location

                for r in range(1, rm.get("racks_count", 0) + 1):
                    rack_name = f"{loc_name}-R{str(r).zfill(2)}"
                    self.racks[rack_name] = netbox.Rack(
                        f"rack-{rack_name.lower()}",
                        name=rack_name,
                        site_id=site.id,
                        location_id=location.id,
                        status="active",
                        width=19,
                        opts=self.opts
                    )

        return site