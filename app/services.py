import json
import logging
from typing import Optional, List
import httpx
import redis.asyncio as aioredis
from app.config import settings
from app.schemas import WeatherData, CropRecommendation

logger = logging.getLogger(__name__)

# Redis client
redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global redis_client
    if redis_client is None:
        try:
            redis_client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True,
            )
            await redis_client.ping()
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            redis_client = None
    return redis_client


async def fetch_weather(location: str) -> Optional[WeatherData]:
    """Fetch weather data from OpenWeatherMap API with caching."""
    cache_key = f"weather:{location.lower().strip()}"

    # Try cache first
    try:
        r = await get_redis()
        if r:
            cached = await r.get(cache_key)
            if cached:
                logger.info(f"Weather cache hit for {location}")
                data = json.loads(cached)
                return WeatherData(**data)
    except Exception as e:
        logger.warning(f"Redis cache read error: {e}")

    # Fetch from API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": location,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )
            if response.status_code == 200:
                data = response.json()
                weather = WeatherData(
                    temperature=data.get("main", {}).get("temp"),
                    humidity=data.get("main", {}).get("humidity"),
                    description=data.get("weather", [{}])[0].get("description", ""),
                    wind_speed=data.get("wind", {}).get("speed"),
                    pressure=data.get("main", {}).get("pressure"),
                    feels_like=data.get("main", {}).get("feels_like"),
                )

                # Cache the result (TTL: 10 minutes)
                try:
                    r = await get_redis()
                    if r:
                        await r.setex(cache_key, 600, weather.model_dump_json())
                except Exception as e:
                    logger.warning(f"Redis cache write error: {e}")

                return weather
            else:
                logger.error(f"Weather API returned {response.status_code}: {response.text}")
                return None
    except httpx.TimeoutException:
        logger.error(f"Weather API timeout for location: {location}")
        return None
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return None


def get_crop_recommendations(
    soil_type: str, weather: Optional[WeatherData]
) -> tuple[List[CropRecommendation], str]:
    """Rule-based crop recommendation engine."""

    soil = soil_type.lower().strip()
    temp = weather.temperature if weather else None
    humidity = weather.humidity if weather else None

    recommendations = []
    reasoning_parts = []

    # Soil-based base recommendations
    soil_crops = {
        "clay": {
            "crops": [
                ("Rice", 0.95, "Kharif", 120, "Excellent water retention for paddy"),
                ("Wheat", 0.85, "Rabi", 140, "Good for winter wheat cultivation"),
                ("Sugarcane", 0.80, "Annual", 365, "Heavy soil supports deep roots"),
                ("Cabbage", 0.75, "Rabi", 90, "Thrives in moisture-rich clay"),
            ],
            "note": "Clay soil has excellent water retention",
        },
        "sandy": {
            "crops": [
                ("Groundnut", 0.90, "Kharif", 120, "Sandy soil provides good drainage"),
                ("Millet", 0.88, "Kharif", 90, "Drought-tolerant, ideal for sandy soil"),
                ("Watermelon", 0.85, "Zaid", 80, "Loves warm, well-drained soil"),
                ("Carrot", 0.80, "Rabi", 75, "Root vegetables thrive in loose soil"),
            ],
            "note": "Sandy soil offers excellent drainage",
        },
        "loamy": {
            "crops": [
                ("Corn", 0.95, "Kharif", 100, "Ideal balanced soil for maize"),
                ("Wheat", 0.92, "Rabi", 140, "Perfect for wheat cultivation"),
                ("Tomato", 0.90, "Rabi", 75, "Rich soil supports high yields"),
                ("Soybean", 0.88, "Kharif", 100, "Nitrogen-fixing crop for loamy soil"),
                ("Cotton", 0.85, "Kharif", 180, "Good soil structure for cotton"),
            ],
            "note": "Loamy soil is versatile and nutrient-rich",
        },
        "silt": {
            "crops": [
                ("Rice", 0.92, "Kharif", 120, "Silty soil retains moisture well"),
                ("Wheat", 0.90, "Rabi", 140, "Fertile silt ideal for wheat"),
                ("Sugarcane", 0.85, "Annual", 365, "Rich nutrients support growth"),
                ("Peas", 0.80, "Rabi", 60, "Cool season crop for silty soil"),
            ],
            "note": "Silt soil is highly fertile and moisture-retentive",
        },
        "red": {
            "crops": [
                ("Groundnut", 0.90, "Kharif", 120, "Red soil is ideal for groundnuts"),
                ("Millet", 0.88, "Kharif", 90, "Drought-tolerant in red soil"),
                ("Tobacco", 0.82, "Rabi", 120, "Traditional red soil crop"),
                ("Pulses", 0.80, "Rabi", 90, "Lentils thrive in red soil"),
            ],
            "note": "Red soil is rich in iron and well-drained",
        },
        "black": {
            "crops": [
                ("Cotton", 0.95, "Kharif", 180, "Black soil is famous for cotton"),
                ("Soybean", 0.90, "Kharif", 100, "Excellent moisture retention"),
                ("Wheat", 0.88, "Rabi", 140, "Winter crop for black soil"),
                ("Sugarcane", 0.85, "Annual", 365, "Deep roots thrive in black soil"),
                ("Sunflower", 0.82, "Rabi", 90, "Good for oilseed production"),
            ],
            "note": "Black (regur) soil has high moisture retention — ideal for cotton",
        },
    }

    # Default if soil type not recognized
    default_crops = [
        ("Wheat", 0.80, "Rabi", 140, "Versatile crop suitable for most soils"),
        ("Rice", 0.78, "Kharif", 120, "Staple crop with wide adaptability"),
        ("Corn", 0.75, "Kharif", 100, "Adaptable to various soil conditions"),
    ]

    soil_info = soil_crops.get(soil, None)
    if soil_info:
        base_crops = soil_info["crops"]
        reasoning_parts.append(f"Soil Analysis: {soil_info['note']}.")
    else:
        base_crops = default_crops
        reasoning_parts.append(
            f"Soil type '{soil_type}' is not in our detailed database. Showing general recommendations."
        )

    # Adjust recommendations based on weather
    if weather and temp is not None:
        if temp > 35:
            reasoning_parts.append(
                f"Current temperature is {temp}°C (hot). Prioritizing heat-tolerant crops."
            )
        elif temp > 25:
            reasoning_parts.append(
                f"Current temperature is {temp}°C (warm). Good conditions for Kharif crops."
            )
        elif temp > 15:
            reasoning_parts.append(
                f"Current temperature is {temp}°C (moderate). Suitable for Rabi crops."
            )
        else:
            reasoning_parts.append(
                f"Current temperature is {temp}°C (cool). Recommending cold-tolerant crops."
            )

        if humidity is not None:
            if humidity > 75:
                reasoning_parts.append(
                    f"Humidity is {humidity}% (high). Water-loving crops will flourish."
                )
            elif humidity < 40:
                reasoning_parts.append(
                    f"Humidity is {humidity}% (low). Drought-resistant varieties recommended."
                )

        if weather.description:
            reasoning_parts.append(f"Current conditions: {weather.description}.")
    else:
        reasoning_parts.append(
            "Weather data unavailable. Recommendations based solely on soil type."
        )

    for crop_name, score, season, period, notes in base_crops:
        # Adjust score based on temperature
        adjusted_score = score
        if weather and temp is not None:
            if season == "Kharif" and temp > 25:
                adjusted_score = min(1.0, score + 0.05)
            elif season == "Rabi" and 10 <= temp <= 25:
                adjusted_score = min(1.0, score + 0.05)
            elif season == "Zaid" and temp > 30:
                adjusted_score = min(1.0, score + 0.05)

        recommendations.append(
            CropRecommendation(
                crop_name=crop_name,
                suitability_score=round(adjusted_score, 2),
                season=season,
                growing_period_days=period,
                notes=notes,
            )
        )

    # Sort by score
    recommendations.sort(key=lambda x: x.suitability_score, reverse=True)
    reasoning = " ".join(reasoning_parts)

    return recommendations, reasoning
