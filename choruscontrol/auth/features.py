"""License feature gates — monetization boundary."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request


def require_feature(feature: str):
    """FastAPI dependency: 403 FEATURE_NOT_LICENSED unless demo mode or claim present."""

    async def _dep(request: Request) -> dict:
        cc = getattr(request.app.state, "cc", None)
        if cc is None:
            raise HTTPException(503, detail="not ready")
        await cc.refresh_license()
        if cc.settings.demo_mode:
            return {"feature": feature, "demo": True, "allowed": True}
        if not cc.license_verifier.has_feature(cc.license_status, feature):
            raise HTTPException(
                status_code=403,
                detail={"detail": "FEATURE_NOT_LICENSED", "feature": feature},
            )
        return {"feature": feature, "demo": False, "allowed": True}

    return Depends(_dep)
