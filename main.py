import time
import uuid
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

YOUR_EMAIL = "22f2000013@ds.study.iitm.ac.in"
ALLOWED_ORIGIN = "https://exam.sanand.workers.dev/backendVerify"

class CORSAndTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Handle preflight OPTIONS request
        if request.method == "OPTIONS":
            if origin == ALLOWED_ORIGIN:
                return Response(
                    status_code=204,
                    headers={
                        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
                        "Access-Control-Allow-Methods": "GET, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                        "X-Request-ID": request_id,
                        "X-Process-Time": str(time.time() - start_time),
                    }
                )
            else:
                # Evil origin — return no ACAO header
                return Response(status_code=403)

        # Handle normal requests
        response = await call_next(request)

        # Add CORS header only for allowed origin
        if origin == ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(time.time() - start_time)
        return response

app.add_middleware(CORSAndTimingMiddleware)

@app.get("/stats")
def get_stats(values: str = Query(...)):
    nums = [int(v.strip()) for v in values.split(",")]
    count = len(nums)
    total = sum(nums)
    return {
        "email": YOUR_EMAIL,
        "count": count,
        "sum": total,
        "min": min(nums),
        "max": max(nums),
        "mean": round(total / count, 6),
    }
