import asyncio
from typing import List, Any
import pandas as pd
from pandas import DataFrame

from database import PostgreDB


async def resolve_troncon_id_from_idtronconh(db: PostgreDB, idtronconh: int) -> int:
    """Retourne l'id interne pgrouting depuis un idtronconh bdcarthage."""
    query = """
    SELECT id FROM bdcarthage.tronconhydrograelt_fxx
    WHERE idtronconh = :idtronconh
    """
    df = await db.fetch_df(query, params={"idtronconh": idtronconh})
    if df is None or df.empty:
        raise ValueError(f"Aucun tronçon trouvé pour idtronconh = {idtronconh}")
    if len(df) > 1:
        raise ValueError(f"Plusieurs tronçons trouvés pour idtronconh = {idtronconh}")
    return int(df.iloc[0]["id"])


async def get_upstream_sections(db: PostgreDB, troncon_id: int) -> pd.DataFrame:
    """Tronçons en amont du troncon_id (id pgrouting)."""
    query = """
    WITH starting_node AS (
        SELECT source
        FROM bdcarthage.tronconhydrograelt_fxx
        WHERE id = :troncon_id
    ),
    dfs AS (
        SELECT
            seq,
            CASE WHEN edge = -1 THEN :troncon_id ELSE edge END AS edge,
            cost,
            agg_cost
        FROM pgr_depthFirstSearch(
            '
            SELECT
                id,
                target AS source,
                source AS target,
                ST_LENGTH(geom) AS cost
            FROM bdcarthage.tronconhydrograelt_fxx
            ',
            (SELECT source FROM starting_node),
            true
        )
    )
    SELECT DISTINCT
        carthage_troncons.id AS id,
        carthage_troncons.source,
        carthage_troncons.target,
        dfs.seq,
        dfs.cost,
        dfs.agg_cost
    FROM dfs
    JOIN bdcarthage.tronconhydrograelt_fxx carthage_troncons
        ON carthage_troncons.id = dfs.edge
    """
    return await db.fetch_df(query, params={"troncon_id": troncon_id})


async def get_downstream_sections(db: PostgreDB, troncon_id: int) -> pd.DataFrame:
    """Tronçons en aval du troncon_id (id pgrouting)."""
    query = """
    WITH starting_node AS (
        SELECT target FROM bdcarthage.tronconhydrograelt_fxx WHERE id = :troncon_id
    ),
    dfs AS (
        SELECT seq,
               CASE WHEN edge = -1 THEN :troncon_id ELSE edge END AS edge,
               cost, agg_cost
        FROM pgr_depthFirstSearch(
            '
            SELECT id, source, target, ST_LENGTH(geom) AS cost
            FROM bdcarthage.tronconhydrograelt_fxx
            ',
            (SELECT target FROM starting_node),
            true
        )
    )
    SELECT DISTINCT carthage.id, carthage.source, carthage.target,
           dfs.seq, dfs.cost, dfs.agg_cost
    FROM dfs
    JOIN bdcarthage.tronconhydrograelt_fxx carthage
        ON carthage.id = dfs.edge
    """
    return await db.fetch_df(query, params={"troncon_id": troncon_id})


async def get_station_info(db: PostgreDB, codestation: str) -> pd.DataFrame:
    """Infos complètes d'une station par son codestation."""
    query = """
    SELECT id, codestation, inseecom, coordx, coordy,
           codecourseau, libellecourseau, codetronconhydro,
           coderegion, libelleregion, codedepartement, libelledepartement,
           naturestation, libellenaturestation, typeentitehydro
    FROM naiades_referentiel_interne.station_full
    WHERE codestation = :codestation
    """
    return await db.fetch_df(query, params={"codestation": codestation})


async def get_matching_stations(db: PostgreDB, upstream_df: pd.DataFrame) -> List[dict]:
    """Stations associées à une liste de tronçons (id pgrouting)."""
    section_id_list = upstream_df["id"].unique().tolist()

    query = """
    SELECT codestation, coordx, coordy, inseecom,typeentitehydro,
           troncon_id AS matched_troncon_id
    FROM bdcarthage.stations_troncons
    WHERE troncon_id = ANY(:section_id_list)
      AND coordx IS NOT NULL
      AND coordy IS NOT NULL
    """
    stations_df = await db.fetch_df(query, params={"section_id_list": section_id_list})

    if stations_df is None or stations_df.empty:
        return []

    merged_df = (
        stations_df
        .merge(upstream_df[["id", "agg_cost"]], left_on="matched_troncon_id", right_on="id")
        .drop("id", axis=1)
        .rename(columns={"agg_cost": "troncon_distance"})
        .sort_values("troncon_distance")
        .reset_index(drop=True)
    )
    return merged_df[["codestation", "coordx", "coordy", "inseecom","typeentitehydro", "troncon_distance"]].to_dict(orient="records")


async def get_matching_section_id(db: PostgreDB, stream_df: pd.DataFrame) -> List[dict]:
    """Tronçons bdcarthage (avec géométrie) associés à une liste d'id pgrouting."""
    section_id_list = stream_df["id"].unique().tolist()

    query = """
    SELECT id, idtronconh, nomentiteh, etat, largeur, nature, navigable,
           toponyme2 AS nom,
           ST_AsGeoJSON(geom) AS geom
    FROM bdcarthage.tronconhydrograelt_fxx
    WHERE id = ANY(:section_id_list)
    """
    section_df = await db.fetch_df(query, params={"section_id_list": section_id_list})

    if section_df is None or section_df.empty:
        return []
    return section_df.to_dict(orient="records")


async def get_upstream_and_downstream(db: PostgreDB, troncon_id: int):
    """Lance amont et aval en parallèle avec asyncio.gather."""
    return await asyncio.gather(
        get_upstream_sections(db, troncon_id),
        get_downstream_sections(db, troncon_id),
    )


async def get_geodf_between2_stations(db: PostgreDB, codestation_amont: str, codestation_aval: str) -> pd.DataFrame:
    """Obtenir la route directes entre deux stations"""
    query = """
    WITH
    stations AS (
        SELECT codestation, source, target
        FROM bdcarthage.stations_troncons
        WHERE codestation = ANY(:codestations)
    ),
    depart AS (
        SELECT target AS source_id FROM stations WHERE codestation = :codestation_amont
    ),
    arrivee AS (
        SELECT source AS target_id FROM stations WHERE codestation = :codestation_aval
    ),
    ids AS (
        SELECT
            (SELECT source_id FROM depart) AS source_id,
            (SELECT target_id FROM arrivee) AS target_id
    ),
    test AS (
        SELECT * FROM pgr_dijkstra(
            'SELECT id, source, target, st_length(geom) as cost FROM bdcarthage.tronconhydrograelt_fxx',
            (SELECT source_id FROM ids),
            (SELECT target_id FROM ids),
            directed := false
        )
    )
    SELECT c.id,
        c.idtronconh,
        c.nomentiteh,
        c.cdtronconh,
        c.etat,
        c.nature,
        c.source,
        c.target,
        test.cost,
        test.agg_cost,
        ST_AsGeoJSON(c.geom) AS geom
    FROM bdcarthage.tronconhydrograelt_fxx c
    JOIN test ON c.id = test.edge
    """
    params = {
        "codestations": [codestation_amont, codestation_aval],
        "codestation_amont": codestation_amont,
        "codestation_aval": codestation_aval,
    }
    return await db.fetch_df(query, params)