from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class WeatherData(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    description: Optional[str] = None
    wind_speed: Optional[float] = None
    pressure: Optional[float] = None
    feels_like: Optional[float] = None


class CropRecommendation(BaseModel):
    crop_name: str
    suitability_score: float
    season: str
    growing_period_days: int
    notes: str


class AdvisoryResponse(BaseModel):
    location: str
    soil_type: str
    weather: Optional[WeatherData] = None
    recommended_crops: List[CropRecommendation]
    reasoning: str
    cached: bool = False


class AdvisoryHistoryResponse(BaseModel):
    id: UUID
    location: str
    soil_type: str
    weather_data: Optional[dict] = None
    recommended_crops: Optional[list] = None
    reasoning: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
