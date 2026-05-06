from fastapi import FastAPI


app = FastAPI(
    title="Skyclad Ventures Agentic Research System",
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Hello, World!"}


