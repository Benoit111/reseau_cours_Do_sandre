import asyncio
from fastapi import APIRouter, HTTPException

from services import (
    get_station_info,
    get_upstream_sections,
    get_downstream_sections,
    get_matching_stations,
    get_matching_section_id,
    resolve_troncon_id_from_idtronconh,
    get_upstream_and_downstream,
    get_geodf_between2_stations,
)
#from geojson import troncons_to_geojson
import pandas as pd
from utils.geojson import troncons_to_geojson

def get_router(db):
    router = APIRouter()

    # --- Utilitaire interne ---
    async def get_troncons_for_station(codestation: str):
        """Retourne les troncon_id bdcarthage liés à une station."""
        query = """
        SELECT troncon_id
        FROM bdcarthage.stations_troncons
        WHERE codestation = :codestation
        """
        df = await db.fetch_df(query, params={"codestation": codestation})
        return df["troncon_id"].tolist() if df is not None and not df.empty else []

    # --- Route : infos d'une station ---
    @router.get("/stations/{codestation}")
    async def read_station(codestation: str):
        """Retourne les informations d'une station par son codestation.
        Exemple https://udam4.ofb.fr/coursDo/stations/03049000 """
        df = await get_station_info(db, codestation)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="Station non trouvée")
        return df.iloc[0].to_dict()

    # --- Route : stations amont/aval depuis un codestation ---
    @router.get("/stations/{codestation}/related_stations")
    async def get_related_stations_by_station(codestation: str):
        """Stations amont et aval à partir du code station.
        exemple https://udam4.ofb.fr/coursDo/troncons/500103965/related_stations
        """
        troncon_ids = await get_troncons_for_station(codestation)
        if not troncon_ids:
            raise HTTPException(status_code=404, detail="Aucune station relié à cette station")

        troncon_id = troncon_ids[0]

        # amont et aval en parallèle
        upstream_df, downstream_df = await get_upstream_and_downstream(db, troncon_id)

        upstream_stations, downstream_stations = await asyncio.gather(
            get_matching_stations(db, upstream_df) if upstream_df is not None and not upstream_df.empty else asyncio.coroutine(lambda: [])(),
            get_matching_stations(db, downstream_df) if downstream_df is not None and not downstream_df.empty else asyncio.coroutine(lambda: [])(),
        )

        return {"amont_stations": upstream_stations, "aval_stations": downstream_stations}

    # --- Route : stations amont/aval depuis un idtronconh ---
    @router.get("/troncons/{troncon_id}/related_stations")
    async def get_related_stations_by_troncon(troncon_id: int):
        """Stations amont et aval à partir d'un idtronconh bdcartge.
        Exemple https://udam4.ofb.fr/coursDo/troncons/500103965/graph_tronconh
        """
        try:
            internal_id = await resolve_troncon_id_from_idtronconh(db, troncon_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        upstream_df, downstream_df = await get_upstream_and_downstream(db, internal_id)

        if (upstream_df is None or upstream_df.empty) and (downstream_df is None or downstream_df.empty):
            raise HTTPException(status_code=404, detail="Pas de données récupérées")

        upstream_stations = await get_matching_stations(db, upstream_df) if upstream_df is not None and not upstream_df.empty else []
        downstream_stations = await get_matching_stations(db, downstream_df) if downstream_df is not None and not downstream_df.empty else []

        return {"amont_stations": upstream_stations, "aval_stations": downstream_stations}

    # --- Route : tronçons amont/aval (GeoJSON) depuis un idtronconh ---
    @router.get("/troncons/{troncon_id}/graph_tronconh")
    async def get_related_troncon_by_troncons(troncon_id: int):
        """Tronçons amont et aval (GeoJSON) à partir d'un idtronconh bdcarthage.
        Exemple : https://udam4.ofb.fr/coursDo/troncons/500103965/graph_tronconh
        """
        try:
            internal_id = await resolve_troncon_id_from_idtronconh(db, troncon_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        upstream_df, downstream_df = await get_upstream_and_downstream(db, internal_id)

        if (upstream_df is None or upstream_df.empty) and (downstream_df is None or downstream_df.empty):
            raise HTTPException(status_code=404, detail="Pas de données récupérées")

        upstream_troncon, downstream_troncon = await asyncio.gather(
            get_matching_section_id(db, upstream_df) if upstream_df is not None and not upstream_df.empty else asyncio.coroutine(lambda: [])(),
            get_matching_section_id(db, downstream_df) if downstream_df is not None and not downstream_df.empty else asyncio.coroutine(lambda: [])(),
        )

        return {
            "amont_troncons": troncons_to_geojson(upstream_troncon),
            "aval_troncons": troncons_to_geojson(downstream_troncon),
        }

    # --- Route : tronçons amont/aval (GeoJSON) depuis un codestation ---
    @router.get("/troncon/{codestation}/graph_tronconh")
    async def get_related_troncon_by_station(codestation: str):
        """Tronçons amont et aval (GeoJSON) à partir d'un code station.
        exemple https://udam4.ofb.fr/coursDo/troncon/05023050/graph_tronconh
        """
        troncon_ids = await get_troncons_for_station(codestation)
        if not troncon_ids:
            raise HTTPException(status_code=404, detail="Aucun tronçon lié à cette station")

        troncon_id = troncon_ids[0]
        upstream_df, downstream_df = await get_upstream_and_downstream(db, troncon_id)

        upstream_troncon = await get_matching_section_id(db, upstream_df) if upstream_df is not None and not upstream_df.empty else []
        downstream_troncon = await get_matching_section_id(db, downstream_df) if downstream_df is not None and not downstream_df.empty else []

        return {
            "amont_troncons": troncons_to_geojson(upstream_troncon),
            "aval_troncons": troncons_to_geojson(downstream_troncon),
        }
        
    # --- Route : troncons entre deux stations ---
    @router.get("/between/graph_tronconh")
    async def get_troncons_between(codestation_amont: str, codestation_aval: str):
        """
           Tronçons (GeoJSON) entre deux stations via pgr_dijkstra.
           Exemple : /between/graph_tronconh?codestation_amont=05023050&codestation_aval=05024100
        """
        df = await get_geodf_between2_stations(db, codestation_amont, codestation_aval)
        if not isinstance(df, pd.DataFrame) or df.empty:  # gère les deux cas
            raise HTTPException(status_code=404, detail="Aucun chemin trouvé. Vérifiez le sens amont → aval.")
        troncons = await get_matching_section_id(db, df)
        return troncons_to_geojson(troncons)

    # --- Route : stations entre deux stations ---
    @router.get("/between/stations")
    async def get_stations_between(codestation_amont: str, codestation_aval: str):
        """
            Stations entre deux stations via pgr_dijkstra.
            Exemple : /between/stations?codestation_amont=05023050&codestation_aval=05024100
        """
        df = await get_geodf_between2_stations(db, codestation_amont, codestation_aval)
        if not isinstance(df, pd.DataFrame) or df.empty:  # gère les deux cas
            raise HTTPException(status_code=404, detail="Aucun chemin trouvé. Vérifiez le sens amont → aval.")
        stations = await get_matching_stations(db, df)
        return {"stations": stations}

    return router
