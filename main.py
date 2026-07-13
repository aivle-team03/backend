from fastapi import FastAPI

app = FastAPI(
    title="FastAPI Backend",
    description="FastAPI 기본 프로젝트 구조",
    version="1.0.0"
)


@app.get("/")
def read_root():
    return {"Hello": "World"}