import os
import pandas as pd
import geopandas as gpd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError


class PostgreDB:
    def __init__(self):
        database = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT", 5432)
        schemas = os.getenv("POSTGRES_SCHEMAS", "public")

        schema_list = [s.strip() for s in schemas.split(",") if s.strip()]
        search_path = ",".join(schema_list)

        # asyncpg à la place de psycopg2
        db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

        self.engine = create_async_engine(
            db_url,
            connect_args={"server_settings": {"search_path": search_path}},
            pool_size=10,       # connexions maintenues en permanence
            max_overflow=20,    # connexions supplémentaires si besoin
            pool_pre_ping=True, # vérifie que la connexion est vivante
        )

        # expire_on_commit=False : évite de recharger les objets après commit
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def fetch_df(self, select_query: str, params: dict = None) -> pd.DataFrame:
        """Exécute une requête SELECT et retourne un DataFrame pandas."""
        async with self.session_factory() as session:
            try:
                result = await session.execute(text(select_query), params or {})
                rows = result.fetchall()
                columns = result.keys()
                if not rows:
                    return pd.DataFrame()
                return pd.DataFrame(rows, columns=list(columns))
            except SQLAlchemyError as e:
                await session.rollback()
                print(f"Erreur fetch_df: {e}")
                return None

    async def fetch_geodf(
        self, select_query: str, params: dict = None, geom_col: str = "geom"
    ) -> gpd.GeoDataFrame:
        """Exécute une requête SELECT avec géométrie et retourne un GeoDataFrame.
        
        Note : geopandas/read_postgis est synchrone. On exécute la requête en async
        puis on reconstruit le GeoDataFrame manuellement.
        """
        df = await self.fetch_df(select_query, params)
        if df is None or df.empty:
            return gpd.GeoDataFrame()
        try:
            df[geom_col] = gpd.GeoSeries.from_wkb(df[geom_col])
            return gpd.GeoDataFrame(df, geometry=geom_col)
        except Exception as e:
            print(f"Erreur conversion GeoDataFrame: {e}")
            return None

    async def close(self):
        """Ferme proprement le pool de connexions."""
        await self.engine.dispose()
