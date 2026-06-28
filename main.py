"""
CORS-Aware Metrics API
Endpoint: GET /stats?values=1,2,3,...
Returns: email, count, sum, min, max, mean
CORS: Only allows https://exam.sanand.workers.dev
Headers: X-Request-ID and X-Process-Time on every response
"""

import time
import uuid
from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ── App setup ──────────────────────────────────────────────────────────────
app = FastAPI()

# Your email address (IIT Madras student email)
YOUR_EMAIL = "22f2000013@ds.study.iitm.ac.in"

# The ONE origin the grader is allowed to call from
ALLOWED_ORIGIN = "https://exam.sanand.workers.dev/backendVerify"

# ── CORS Middleware ────────────────────────────────────────────────────────
# This is the "bouncer" — only lets in requests from our allowed origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],   # ← NO wildcard "*", only this one origin
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── Custom Middleware: adds X-Request-ID and X-Process-Time ───────────────
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()                    # Record when request started
        request_id = str(uuid.uuid4())              # Generate a unique ID (like a receipt number)

        response = await call_next(request)         # Actually run the endpoint

        process_time = time.time() - start_time     # How long did it take?

        # Attach our custom headers to EVERY response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response

app.add_middleware(TimingMiddleware)

# ── Endpoint ───────────────────────────────────────────────────────────────
@app.get("/stats")
def get_stats(values: str = Query(..., description="Comma-separated integers, e.g. 1,2,3")):
    """
    Parse comma-separated integers and return descriptive statistics.
    """
    # Split "1,2,3,4" into ["1","2","3","4"] and convert to integers
    nums = [int(v.strip()) for v in values.split(",")]

    count = len(nums)
    total = sum(nums)
    minimum = min(nums)
    maximum = max(nums)
    mean = total / count          # Calculate average

    return {
        "email": YOUR_EMAIL,
        "count": count,
        "sum": total,
        "min": minimum,
        "max": maximum,
        "mean": round(mean, 6),   # Enough decimal places — grader needs ±0.01 accuracy
    }
