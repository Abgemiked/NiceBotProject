import aiohttp
import discord


async def handler(cfg_json, interaction, ort):
    API_KEY = cfg_json['API_KEY']
    BASE_URL = cfg_json['BASE_URL']
    city_name = ort.capitalize()

    await interaction.response.defer()

    if not city_name.isalpha():
        await interaction.edit_original_response(content="Ungültige Eingabe für den Ortsnamen. Bitte verwende nur Buchstaben.")
        return

    complete_url = BASE_URL + "lang=de" + "&key=" + API_KEY + "&city=" + city_name + "&days=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(complete_url) as response:
                data = await response.json()
    except aiohttp.ClientError:
        await interaction.edit_original_response(content="Der Wetterdienst ist gerade nicht erreichbar.")
        return

    if data.get("data"):
        weather_data = data["data"][0]
        current_temperature = weather_data["temp"]
        current_temperature_celsius = str(round(current_temperature))
        current_humidity = weather_data["rh"]
        weather_description = weather_data["weather"]["description"]
        precipitation_probability = weather_data["precip"]

        if precipitation_probability is not None:
            precipitation_probability = f"{precipitation_probability}"
        else:
            precipitation_probability = "N/A"

        city_name = weather_data["city_name"].capitalize()

        embed = discord.Embed(
            title=f"Wetter in {city_name}",
            color=interaction.guild.me.top_role.color,
            timestamp=interaction.created_at,
        )
        embed.add_field(name="Wetter", value=f"**{weather_description}**", inline=False)
        embed.add_field(name="Temperatur(°C)", value=f"**{current_temperature_celsius}°C**", inline=False)
        embed.add_field(name="Luftfeuchtigkeit(%)", value=f"**{current_humidity}%**", inline=False)

        hourly_data = weather_data.get("hourly")

        if hourly_data:
            for hour in hourly_data:
                time = hour.get("time")
                temperature = hour.get("temp")
                temperature_celsius = str(round(temperature))
                humidity = hour.get("rh")
                embed.add_field(
                    name=f"Zeit: {time}",
                    value=f"Temperatur: {temperature_celsius}°C, Luftfeuchtigkeit: {humidity}%",
                    inline=False,
                )

        await interaction.edit_original_response(embed=embed)
    else:
        await interaction.edit_original_response(content="Ortschaft nicht gefunden.")
