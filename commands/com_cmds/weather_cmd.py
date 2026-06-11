import aiohttp
import discord

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

# WMO Weather Interpretation Codes → (deutsche Beschreibung, Icon-URL)
WMO_CODES = {
    0: ("Klarer Himmel", "https://openweathermap.org/img/wn/01d.png"),
    1: ("Überwiegend klar", "https://openweathermap.org/img/wn/02d.png"),
    2: ("Teilweise bewölkt", "https://openweathermap.org/img/wn/03d.png"),
    3: ("Bedeckt", "https://openweathermap.org/img/wn/04d.png"),
    45: ("Nebel", "https://openweathermap.org/img/wn/50d.png"),
    48: ("Nebel mit Reifbildung", "https://openweathermap.org/img/wn/50d.png"),
    51: ("Leichter Nieselregen", "https://openweathermap.org/img/wn/09d.png"),
    53: ("Mäßiger Nieselregen", "https://openweathermap.org/img/wn/09d.png"),
    55: ("Starker Nieselregen", "https://openweathermap.org/img/wn/09d.png"),
    56: ("Leichter gefrierender Nieselregen", "https://openweathermap.org/img/wn/09d.png"),
    57: ("Starker gefrierender Nieselregen", "https://openweathermap.org/img/wn/09d.png"),
    61: ("Leichter Regen", "https://openweathermap.org/img/wn/10d.png"),
    63: ("Mäßiger Regen", "https://openweathermap.org/img/wn/10d.png"),
    65: ("Starker Regen", "https://openweathermap.org/img/wn/10d.png"),
    66: ("Leichter gefrierender Regen", "https://openweathermap.org/img/wn/13d.png"),
    67: ("Starker gefrierender Regen", "https://openweathermap.org/img/wn/13d.png"),
    71: ("Leichter Schneefall", "https://openweathermap.org/img/wn/13d.png"),
    73: ("Mäßiger Schneefall", "https://openweathermap.org/img/wn/13d.png"),
    75: ("Starker Schneefall", "https://openweathermap.org/img/wn/13d.png"),
    77: ("Schneegriesel", "https://openweathermap.org/img/wn/13d.png"),
    80: ("Leichte Regenschauer", "https://openweathermap.org/img/wn/09d.png"),
    81: ("Mäßige Regenschauer", "https://openweathermap.org/img/wn/09d.png"),
    82: ("Heftige Regenschauer", "https://openweathermap.org/img/wn/09d.png"),
    85: ("Leichte Schneeschauer", "https://openweathermap.org/img/wn/13d.png"),
    86: ("Starke Schneeschauer", "https://openweathermap.org/img/wn/13d.png"),
    95: ("Gewitter", "https://openweathermap.org/img/wn/11d.png"),
    96: ("Gewitter mit leichtem Hagel", "https://openweathermap.org/img/wn/11d.png"),
    99: ("Gewitter mit starkem Hagel", "https://openweathermap.org/img/wn/11d.png"),
}

MAX_HOURLY_FIELDS = 6


def describe_weather_code(code):
    """Liefert (Beschreibung, Icon-URL) für einen WMO-Code."""
    return WMO_CODES.get(code, ("Unbekanntes Wetter", None))


def is_valid_city_name(name):
    """Buchstaben, Leerzeichen, Bindestrich und Punkt erlaubt (z.B. 'Bad Homburg', 'St. Augustin')."""
    return bool(name) and any(ch.isalpha() for ch in name) and all(
        ch.isalpha() or ch in " -." for ch in name
    )


async def fetch_geocoding(session, city_name):
    """Sucht den Ort via Open-Meteo-Geocoding. Liefert das erste Resultat oder None."""
    params = {"name": city_name, "count": 1, "language": "de"}
    async with session.get(GEOCODING_URL, params=params) as response:
        if response.status != 200:
            raise aiohttp.ClientError(f"Geocoding-API: HTTP {response.status}")
        data = await response.json()
    results = data.get("results")
    return results[0] if results else None


async def fetch_forecast(session, latitude, longitude):
    """Holt aktuelles Wetter + stündliche Vorhersage (12h) von Open-Meteo."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,precipitation",
        "hourly": "temperature_2m,relative_humidity_2m",
        "forecast_hours": 12,
        "timezone": "auto",
    }
    async with session.get(FORECAST_URL, params=params) as response:
        if response.status != 200:
            raise aiohttp.ClientError(f"Forecast-API: HTTP {response.status}")
        return await response.json()


async def handler(interaction, ort):
    city_name = ort.strip()

    await interaction.response.defer()

    if not is_valid_city_name(city_name):
        await interaction.edit_original_response(
            content="Ungültige Eingabe für den Ortsnamen. Bitte verwende nur Buchstaben, Leerzeichen, Bindestriche oder Punkte."
        )
        return

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            location = await fetch_geocoding(session, city_name)
            if location is None:
                await interaction.edit_original_response(content="Ortschaft nicht gefunden.")
                return
            forecast = await fetch_forecast(session, location["latitude"], location["longitude"])
    except (aiohttp.ClientError, TimeoutError):
        await interaction.edit_original_response(content="Der Wetterdienst ist gerade nicht erreichbar.")
        return

    current = forecast.get("current", {})
    description, icon_url = describe_weather_code(current.get("weather_code"))
    temperature = round(current.get("temperature_2m", 0))
    humidity = current.get("relative_humidity_2m", "N/A")

    embed = discord.Embed(
        title=f"Wetter in {location.get('name', city_name)}",
        color=interaction.guild.me.top_role.color,
        timestamp=interaction.created_at,
    )
    if icon_url:
        embed.set_thumbnail(url=icon_url)
    embed.add_field(name="Wetter", value=f"**{description}**", inline=False)
    embed.add_field(name="Temperatur(°C)", value=f"**{temperature}°C**", inline=False)
    embed.add_field(name="Luftfeuchtigkeit(%)", value=f"**{humidity}%**", inline=False)

    hourly = forecast.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    hums = hourly.get("relative_humidity_2m", [])

    for time_iso, temp, hum in list(zip(times, temps, hums))[:MAX_HOURLY_FIELDS]:
        # ISO-Format "2026-06-11T14:00" → "14:00"
        hour_label = time_iso.split("T")[1] if "T" in time_iso else time_iso
        embed.add_field(
            name=f"Zeit: {hour_label}",
            value=f"Temperatur: {round(temp)}°C, Luftfeuchtigkeit: {hum}%",
            inline=False,
        )

    await interaction.edit_original_response(embed=embed)
