from fastapi import FastAPI
from starlette.responses import Response
from starlette.status import HTTP_200_OK
from .core.settings import settings
from .api.v1.api import api_router as api_v1
from .db.session import db
from .db.models import MODELS
from .initial import initialize_db
from .utils.log import log
from fastapi_utils.tasks import repeat_every
from .tasks.youtube import getVideosFromChannelsJob, getVideosByQueryJob
from .tasks.sites import getNewPostsJob
import traceback
#from peewee import OperationalError
#from psycopg2 import errors

db.connect()
try:
	db.create_tables(MODELS)
	initialize_db()
except Exception as e:
	traceback.print_exc()
db.close()

app = FastAPI(
	title=settings.PROJECT_NAME,
	openapi_url = settings.API_V1_STR+"/docs" if settings.DEV else None
)

app.include_router(api_v1, prefix=settings.API_V1_STR)

@app.get('/')
async def get_root():
	return Response(status_code=HTTP_200_OK)

if settings.RUN_TASKS:
	log("Running tasks",error=False)
	app.on_event("startup")(repeat_every(seconds=settings.INTERVAL)(getNewPostsJob))
	app.on_event("startup")(repeat_every(seconds=settings.INTERVAL)(getVideosFromChannelsJob))
	app.on_event("startup")(repeat_every(seconds=settings.INTERVAL)(getVideosByQueryJob))

