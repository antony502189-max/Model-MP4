from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.config import settings
from app.db import init_db

app = FastAPI(title=settings.app_name, version='1.0.0')
app.include_router(router)
app.mount('/static', StaticFiles(directory='app/static'), name='static')
templates = Jinja2Templates(directory='app/templates')


@app.on_event('startup')
def startup() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name='index.html', context={'app_name': settings.app_name})
