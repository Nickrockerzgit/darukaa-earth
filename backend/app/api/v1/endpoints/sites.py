"""Site endpoints (read, update, delete and the map's GeoJSON feed)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.geojson import FeatureCollection
from app.schemas.site import SiteRead, SiteUpdate
from app.services.site_service import SiteService

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get(
    "/geojson",
    response_model=FeatureCollection,
    summary="Every visible site as a GeoJSON FeatureCollection",
)
async def sites_geojson(
    user: CurrentUser,
    session: DbSession,
    project_id: uuid.UUID | None = Query(
        default=None, description="Restrict the collection to one project"
    ),
) -> FeatureCollection:
    """Return the map layer's data source in a single request.

    The response carries a ``bbox`` so the client can ``fitBounds`` without a
    second round trip or a client-side sweep over every coordinate.
    """
    return await SiteService(session).feature_collection(user, project_id)


@router.get("/{site_id}", response_model=SiteRead, summary="Get a site with its geometry")
async def get_site(site_id: uuid.UUID, user: CurrentUser, session: DbSession) -> SiteRead:
    """Fetch a single site, geometry included."""
    return await SiteService(session).get(user, site_id)


@router.patch("/{site_id}", response_model=SiteRead, summary="Update a site")
async def update_site(
    site_id: uuid.UUID, payload: SiteUpdate, user: CurrentUser, session: DbSession
) -> SiteRead:
    """Apply a partial update; area and centroid are recomputed if it moved."""
    site = await SiteService(session).update(user, site_id, payload)
    await session.commit()
    return site


@router.delete(
    "/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a site and its metric history",
)
async def delete_site(site_id: uuid.UUID, user: CurrentUser, session: DbSession) -> Response:
    """Delete a site; its metric samples cascade."""
    await SiteService(session).delete(user, site_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
