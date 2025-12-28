from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from vendor_finder import VendorFinder

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="AI Vendor Finder",
    version="1.0.0"
)

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # OK for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

finder = VendorFinder()

# @app.get("/")
# def health_check():
#     return {"status": "ok"}

# 1. Update the root route to serve your HTML file
@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join("static", "index.html"))

# 2. Mount the static directory (so it can find CSS/JS/Images if you add them)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/search")
def search_vendors(
    service: str = Query(..., description="Service or product (e.g. plumber, cake, photographer)"),
    location: str = Query(..., description="City or area (e.g. Abuja, Lagos)")
):
    """
    Search for local vendors by service and location.
    """

    result = finder.find_vendors(service, location)

    # Handle both list and dict return types safely
    if isinstance(result, dict):
        vendors = result.get("vendors", [])
    else:
        vendors = result

    # Optional: filter out very weak vendors (recommended)
    vendors = [
        v for v in vendors
        if v.get("confidence_score", 0) >= 0.5
    ]

    vendors = sorted(
        vendors,
        key=lambda v: v.get("confidence_score", 0),
        reverse=True
    )


    return {
        "query": {
            "service": service,
            "location": location
        },
        "total_vendors": len(vendors),
        "vendors": vendors
    }
