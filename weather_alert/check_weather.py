#!/usr/bin/env python3
"""Check today's weather forecast for Sunnyvale, CA.

If the daily high temperature exceeds 25°C or the chance of rain exceeds 20%,
send an alert via Telegram.

Uses the Open-Meteo API (free, no API key required).
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Sunnyvale, CA coordinates
LATITUDE = 37.3688
LONGITUDE = -122.0363
LOCATION_NAME = "Sunnyvale, CA"

RAIN_THRESHOLD_PERCENT = 20
TEMP_THRESHOLD_C = 25

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _session_with_retries() -> requests.Session:
    """Create a requests session with automatic retries."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def get_today_forecast() -> dict:
    """Fetch today's forecast from Open-Meteo."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": "temperature_2m_max,precipitation_probability_max",
        "timezone": "America/Los_Angeles",
        "forecast_days": 1,
    }
    session = _session_with_retries()
    resp = session.get(OPEN_METEO_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = data["daily"]
    return {
        "high_temp_c": daily["temperature_2m_max"][0],
        "rain_chance_pct": daily["precipitation_probability_max"][0],
        "date": daily["time"][0],
    }


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> None:
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    session = _session_with_retries()
    resp = session.post(url, json=payload, timeout=30)
    resp.raise_for_status()


def main():
    parser = argparse.ArgumentParser(description="Check weather and send Telegram alerts.")
    parser.add_argument(
        "--env",
        required=True,
        help="Path to .env file containing TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.env):
        print(f"Error: .env file not found: {args.env}")
        sys.exit(1)

    load_dotenv(args.env)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        sys.exit(1)

    forecast = get_today_forecast()
    high_temp = forecast["high_temp_c"]
    rain_chance = forecast["rain_chance_pct"]
    date = forecast["date"]

    print(f"Forecast for {LOCATION_NAME} on {date}:")
    print(f"  High temperature: {high_temp}°C")
    print(f"  Rain chance: {rain_chance}%")

    alerts = []
    if rain_chance > RAIN_THRESHOLD_PERCENT:
        alerts.append(
            f"🌧 Rain chance: {rain_chance}% (threshold: >{RAIN_THRESHOLD_PERCENT}%)"
        )
    if high_temp > TEMP_THRESHOLD_C:
        alerts.append(
            f"🌡 High temperature: {high_temp}°C (threshold: >{TEMP_THRESHOLD_C}°C)"
        )

    if alerts:
        message = f"*Weather Alert for {LOCATION_NAME}* ({date})\n\n" + "\n".join(
            alerts
        )
        send_telegram_message(bot_token, chat_id, message)
        print("Telegram alert sent.")
    else:
        print("No alerts triggered.")


if __name__ == "__main__":
    main()
