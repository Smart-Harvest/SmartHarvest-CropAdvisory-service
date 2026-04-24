from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.database import get_db
from app.models import AdvisoryHistory
from app.schemas import AdvisoryResponse, AdvisoryHistoryResponse
from app.auth import get_current_user
from app.services import fetch_weather, get_crop_recommendations

router = APIRouter(prefix="/api/v1/crops", tags=["crops"])


@router.get("/advisory", response_model=AdvisoryResponse)
async def get_advisory(
    location: str = Query(..., min_length=1, description="Location for weather lookup"),
    soil_type: str = Query(..., min_length=1, description="Type of soil"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get crop advisory based on location weather and soil type."""

    # Fetch weather (handles failures gracefully)
    weather = await fetch_weather(location)

    # Get recommendations
    recommendations, reasoning = get_crop_recommendations(soil_type, weather)

    # Save to history
    history_entry = AdvisoryHistory(
        user_id=current_user["user_id"],
        location=location,
        soil_type=soil_type,
        weather_data=weather.model_dump() if weather else None,
        recommended_crops=[r.model_dump() for r in recommendations],
        reasoning=reasoning,
    )
    db.add(history_entry)
    await db.flush()

    return AdvisoryResponse(
        location=location,
        soil_type=soil_type,
        weather=weather,
        recommended_crops=recommendations,
        reasoning=reasoning,
        cached=False,
    )


@router.get("/history", response_model=List[AdvisoryHistoryResponse])
async def get_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get advisory history for the current user."""
    result = await db.execute(
        select(AdvisoryHistory)
        .where(AdvisoryHistory.user_id == current_user["user_id"])
        .order_by(desc(AdvisoryHistory.created_at))
        .limit(50)
    )
    history = result.scalars().all()
    return [AdvisoryHistoryResponse.model_validate(h) for h in history]
