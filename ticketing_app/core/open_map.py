import httpx
from shapely.geometry import Point


async def geocode_address(address: str) -> Point:
    """Take an address string, return a Shapely Point (lon, lat)"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    if not data:
        raise ValueError(f"Could not geocode address: {address}")

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    return Point(lon, lat)
