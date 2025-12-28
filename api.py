from fastapi import FastAPI, Query, HTTPException
from typing import Optional
from vendor_finder import VendorFinder
from config import Config

app = FastAPI(
    title="Local Vendor Finder API",
    description="AI-powered vendor discovery for any service and location",
    version="1.0.0"
)

finder = VendorFinder()


@app.on_event("startup")
def startup_check():
    """
    Warn if API keys are missing (non-blocking).
    """
    missing_keys = Config.validate_config()
    if missing_keys:
        print("⚠️ Missing API keys:")
        for key in missing_keys:
            print(f"   - {key}")
        print("API will run with limited functionality.\n")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/search")
def search_vendors(
    service: str = Query(..., description="Service or product (e.g. plumber, cake, photographer)"),
    location: str = Query(..., description="City or area (e.g. Abuja, Lagos, Ibadan)"),
    platform: Optional[str] = Query(
        None,
        description="Preferred platform (instagram, twitter). Visual services auto-force instagram."
    ),
    max_results: int = Query(5, ge=1, le=20),
    min_confidence: float = Query(0.3, ge=0.1, le=1.5)
):
    """
    Search for vendors dynamically.
    No service or location is hardcoded.
    """

    try:
        result = finder.find_vendors(
            service=service,
            location=location,
            platform=platform or "instagram",
            max_results=max_results,
            min_confidence=min_confidence
        )

        return {
            "query": {
                "service": service,
                "location": location,
                "platform": platform or "auto"
            },
            "total_vendors": len(result["vendors"]),
            "vendors": result["vendors"],
            "analysis": result.get("analysis"),
            "agent_reasoning": result.get("agent_reasoning")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
