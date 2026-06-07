# Weather API Reference (Open-Meteo)

Free weather data API used by the `weather_by_location` tool. No API key required.

## 1. Geocoding — resolve location to coordinates

```
GET https://geocoding-api.open-meteo.com/v1/search
```

| Parameter | Type   | Required | Description                          |
|-----------|--------|----------|--------------------------------------|
| name      | string | yes      | City or place name (e.g. "London")   |
| count     | int    | no       | Number of results (default: 10)      |
| language  | string | no       | Response language (default: "en")      |
| format    | string | no       | Response format (default: "json")      |

**Example**

```
GET https://geocoding-api.open-meteo.com/v1/search?name=San+Francisco&count=1
```

**Response fields used**

- `results[0].name` — resolved place name
- `results[0].latitude` — latitude
- `results[0].longitude` — longitude
- `results[0].country` — country name

## 2. Weather forecast — current and daily conditions

```
GET https://api.open-meteo.com/v1/forecast
```

| Parameter  | Type  | Required | Description                                      |
|------------|-------|----------|--------------------------------------------------|
| latitude   | float | yes      | Latitude from geocoding step                     |
| longitude  | float | yes      | Longitude from geocoding step                    |
| current    | string| no       | Comma-separated current weather variables        |
| daily      | string| no       | Comma-separated daily forecast variables         |
| timezone   | string| no       | IANA timezone (`auto` recommended)             |
| forecast_days | int| no       | Days to forecast (default: 7, max: 16)         |

**Example**

```
GET https://api.open-meteo.com/v1/forecast?latitude=37.77&longitude=-122.42&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code&timezone=auto&forecast_days=3
```

**Current weather variables**

| Variable            | Unit  | Description                    |
|---------------------|-------|--------------------------------|
| temperature_2m      | °C    | Air temperature at 2 m         |
| apparent_temperature| °C    | Feels-like temperature       |
| relative_humidity_2m| %     | Relative humidity            |
| precipitation       | mm    | Current precipitation        |
| weather_code        | WMO   | Condition code (see below)   |
| wind_speed_10m      | km/h  | Wind speed at 10 m           |

**WMO weather codes (common)**

| Code | Condition        |
|------|------------------|
| 0    | Clear sky        |
| 1–3  | Mainly clear to overcast |
| 45,48| Fog              |
| 51–55| Drizzle          |
| 61–65| Rain             |
| 71–75| Snow             |
| 80–82| Rain showers     |
| 95   | Thunderstorm     |
