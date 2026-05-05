import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .routers import admin, health

app = FastAPI()
app.include_router(admin.router)
app.include_router(health.router)


@app.get("/")
def get_root():
    return RedirectResponse(url="/docs")


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
