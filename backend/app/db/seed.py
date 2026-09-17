"""Demo data seeder.

Run with ``python -m app.db.seed`` (or ``make seed``). It is idempotent: sites
are matched by ``(project, name)`` and metric samples are upserted, so running
it twice changes nothing.

The polygons below are real, recognisable restoration and conservation
landscapes spread across four continents and both hemispheres. That matters
for the demo: the seasonal model in the synthetic provider is latitude-driven,
so a reviewer comparing Sundarbans with Patagonia sees genuinely different
seasonal curves rather than the same shape twice.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from shapely.geometry import Polygon
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.site import Site
from app.models.user import User
from app.services.site_service import SiteService
from app.utils.geo import geojson_to_multipolygon, to_wkb_element

logger = get_logger(__name__)


def _rectangle(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    """Build a closed GeoJSON polygon from a bounding box."""
    return {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


#: (project, sites) fixtures. Coordinates are approximate bounding boxes of
#: well-known landscapes, chosen to span latitudes from 54S to 60N.
DEMO_PROJECTS: tuple[dict[str, Any], ...] = (
    {
        "name": "Sundarbans Mangrove Restoration",
        "description": (
            "Mangrove replanting across the Indian Sundarbans delta. Blue-carbon "
            "accounting with quarterly ground surveys."
        ),
        "project_type": ProjectType.MIXED,
        "status": ProjectStatus.ACTIVE,
        "start_date": date(2022, 4, 1),
        "sites": [
            ("Gosaba Block North", _rectangle(88.78, 22.14, 88.90, 22.24)),
            ("Basanti Tidal Flats", _rectangle(88.62, 22.18, 88.73, 22.27)),
            ("Jharkhali Creek", _rectangle(88.68, 22.02, 88.77, 22.10)),
        ],
    },
    {
        "name": "Western Ghats Agroforestry",
        "description": (
            "Shade-grown coffee and native tree intercropping across smallholder "
            "plots in Karnataka."
        ),
        "project_type": ProjectType.CARBON,
        "status": ProjectStatus.ACTIVE,
        "start_date": date(2021, 6, 1),
        "sites": [
            ("Kodagu Plateau", _rectangle(75.72, 12.30, 75.86, 12.42)),
            ("Bhadra Buffer", _rectangle(75.55, 13.58, 75.68, 13.70)),
        ],
    },
    {
        "name": "Amazon Riparian Corridor",
        "description": (
            "Riparian buffer restoration reconnecting fragmented forest along the Rio Tapajos."
        ),
        "project_type": ProjectType.BIODIVERSITY,
        "status": ProjectStatus.ACTIVE,
        "start_date": date(2023, 1, 1),
        "sites": [
            ("Tapajos Left Bank", _rectangle(-55.10, -3.20, -54.96, -3.06)),
            ("Santarem Fringe", _rectangle(-54.82, -2.62, -54.70, -2.50)),
        ],
    },
    {
        "name": "Patagonia Grassland Recovery",
        "description": (
            "Rotational grazing withdrawal and native grass recovery in Santa Cruz "
            "province. Southern-hemisphere seasonality."
        ),
        "project_type": ProjectType.BIODIVERSITY,
        "status": ProjectStatus.DRAFT,
        "start_date": date(2024, 3, 1),
        "sites": [
            ("Rio Chico Steppe", _rectangle(-70.10, -50.10, -69.92, -49.96)),
        ],
    },
    {
        "name": "Boreal Peatland Protection",
        "description": (
            "Avoided-drainage peatland conservation in Finnish Lapland. Strong "
            "seasonal signal at high latitude."
        ),
        "project_type": ProjectType.CARBON,
        "status": ProjectStatus.ACTIVE,
        "start_date": date(2022, 9, 1),
        "sites": [
            ("Sodankyla Mire", _rectangle(26.55, 67.35, 26.75, 67.46)),
            ("Kemijoki Headwater", _rectangle(27.10, 66.90, 27.28, 67.00)),
        ],
    },
)


async def seed() -> None:
    """Create the demo user, projects, sites and metric history."""
    async with SessionFactory() as session:
        service = SiteService(session)

        user = (
            (await session.execute(select(User).where(User.email == settings.seed_demo_email)))
            .scalars()
            .first()
        )
        if user is None:
            user = User(
                email=settings.seed_demo_email,
                hashed_password=hash_password(settings.seed_demo_password),
                full_name="Darukaa Demo Admin",
            )
            session.add(user)
            await session.flush()
            logger.info("seed.user.created", email=user.email)

        created_sites = 0
        created_samples = 0

        for fixture in DEMO_PROJECTS:
            sites_fixture: list[tuple[str, dict[str, Any]]] = fixture["sites"]
            project = (
                (
                    await session.execute(
                        select(Project).where(
                            Project.owner_id == user.id, Project.name == fixture["name"]
                        )
                    )
                )
                .scalars()
                .first()
            )

            if project is None:
                project = Project(
                    owner_id=user.id,
                    name=fixture["name"],
                    description=fixture["description"],
                    project_type=fixture["project_type"],
                    status=fixture["status"],
                    start_date=fixture["start_date"],
                )
                session.add(project)
                await session.flush()
                logger.info("seed.project.created", name=project.name)

            for site_name, geojson in sites_fixture:
                existing = (
                    (
                        await session.execute(
                            select(Site).where(
                                Site.project_id == project.id, Site.name == site_name
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

                multipolygon = geojson_to_multipolygon(geojson)
                if existing is None:
                    element = to_wkb_element(multipolygon)
                    area, centroid = await service.sites.compute_geometry_facts(element)
                    existing = Site(
                        project_id=project.id,
                        name=site_name,
                        description=f"Monitoring unit within {project.name}.",
                        geometry=element,
                        area_hectares=area,
                        centroid=centroid,
                    )
                    session.add(existing)
                    await session.flush()
                    created_sites += 1

                created_samples += await service.backfill_metrics(
                    existing, multipolygon, start_date=project.start_date
                )

        await session.commit()
        logger.info(
            "seed.complete",
            projects=len(DEMO_PROJECTS),
            sites_created=created_sites,
            samples_created=created_samples,
            login_email=settings.seed_demo_email,
        )


def _validate_fixtures() -> None:
    """Fail fast if a fixture polygon is malformed."""
    for fixture in DEMO_PROJECTS:
        for name, geojson in fixture["sites"]:
            ring = geojson["coordinates"][0]
            if not Polygon(ring).is_valid:
                msg = f"Demo fixture {name!r} is not a valid polygon"
                raise ValueError(msg)


def main() -> None:
    """CLI entry point."""
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    _validate_fixtures()
    asyncio.run(seed())


if __name__ == "__main__":
    main()
