from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.api.routes import router

settings=get_settings()
app=FastAPI(title='SpaceWeave AI API',version='2.0.0',description='Multimodal visual product retrieval with spatial fit and marketplace adapters.')
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=False,allow_methods=['*'],allow_headers=['*'])
app.include_router(router)
try: app.mount('/',StaticFiles(directory='/app/frontend',html=True),name='frontend')
except RuntimeError: pass
