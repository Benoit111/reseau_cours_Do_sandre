from contextlib import asynccontextmanager
from fastapi import FastAPI

from database import PostgreDB
from routers import stations


db = PostgreDB()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie : ouverture et fermeture propre du pool DB."""
    yield
    await db.close()


app = FastAPI(lifespan=lifespan, root_path="/coursDo")

app.include_router(stations.get_router(db))
