from fastapi import FastAPI

from build import Builder

app = FastAPI(title="Schema-grounded NL2SQL", version="0.2.0")
Builder(app).build_and_initialize_app()
