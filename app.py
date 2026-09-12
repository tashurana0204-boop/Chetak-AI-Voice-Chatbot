import re

from flask import Flask, render_template, request, jsonify
import requests
import os
import subprocess
import json
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)


# =========================
# WORLD TIME + WEATHER
# =========================

def get_location_info(location):

    encoded_location = urllib.parse.quote(location)

    geocode_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={encoded_location}"
        "&count=1"
        "&language=en"
        "&format=json"
    )

    with urllib.request.urlopen(
        geocode_url,
        timeout=10
    ) as response:

        geo_data = json.loads(
            response.read().decode("utf-8")
        )

    results = geo_data.get("results", [])

    if not results:
        return None

    place = results[0]

    latitude = place["latitude"]
    longitude = place["longitude"]

    city = place.get("name", location)
    country = place.get("country", "")
    timezone = place.get("timezone", "UTC")

    # Get current weather AND local time from Open-Meteo
    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=temperature_2m"
        "&timezone=auto"
    )

    with urllib.request.urlopen(
        weather_url,
        timeout=10
    ) as response:

        weather_data = json.loads(
            response.read().decode("utf-8")
        )

    current_weather = weather_data.get(
        "current",
        {}
    )

    temperature = current_weather.get(
        "temperature_2m"
    )

    local_datetime = current_weather.get(
        "time"
    )

    if temperature is None:
        raise ValueError(
            "Temperature data was not returned"
        )

    if local_datetime is None:
        raise ValueError(
            "Local time data was not returned"
        )

    # Open-Meteo returns local time as YYYY-MM-DDTHH:MM
    dt = datetime.fromisoformat(
        local_datetime
    )

    return {
        "city": city,
        "country": country,
        "timezone": timezone,
        "time": dt.strftime("%I:%M %p"),
        "date": dt.strftime("%d %B %Y"),
        "temperature": temperature
    }


# =========================
# DETECT TIME / WEATHER
# =========================

def extract_location(message):

    text = message.strip()

    patterns = [

        # What is the time in Perth?
        r"(?:what(?:'s| is)?\s+)?(?:the\s+)?time\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # What time is it in Perth?
        r"(?:what\s+)?time\s+is\s+it\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # Tell me the time in Perth
        r"(?:tell me|give me)\s+(?:the\s+)?time\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # Current/local time in Perth
        r"(?:current|local)\s+time\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # What is the temperature in Delhi?
        r"(?:what(?:'s| is)?\s+)?(?:the\s+)?(?:temperature|temp)\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # What is the temperature of Delhi?
        r"(?:what(?:'s| is)?\s+)?(?:the\s+)?(?:temperature|temp)\s+(?:of)\s+(.+?)[?.!]*$",

        # Weather in Delhi
        r"(?:what(?:'s| is)?\s+)?(?:the\s+)?weather\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # What's the weather like in Delhi?
        r"(?:what(?:'s| is)?\s+)?(?:the\s+)?weather\s+like\s+(?:in|at|of)\s+(.+?)[?.!]*$",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            location = match.group(1).strip()

            location = re.sub(
                r"[?.!]+$",
                "",
                location
            ).strip()

            return location

    return None


def is_time_question(message):

    text = message.lower()

    return (
        "time" in text
        or "clock" in text
    )


def is_weather_question(message):

    text = message.lower()

    return (
        "temperature" in text
        or "temp" in text
        or "weather" in text
    )


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================
# AI CHAT
# =========================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    data = request.get_json() or {}

    user_message = data.get(
        "message",
        ""
    ).strip()

    if not user_message:

        return jsonify({
            "error":
            "Please enter a message."
        }), 400


    # =========================
    # WORLD TIME / WEATHER
    # =========================

    location = extract_location(
        user_message
    )

    if location:

        try:

            info = get_location_info(
                location
            )

            if info is None:

                return jsonify({
                    "reply":
                    f"I couldn't find the location '{location}'."
                })

            time_requested = is_time_question(
                user_message
            )

            weather_requested = is_weather_question(
                user_message
            )

            if (
                time_requested
                and weather_requested
            ):

                reply = (
                    f"The current time in "
                    f"{info['city']}, "
                    f"{info['country']} is "
                    f"{info['time']} on "
                    f"{info['date']}.\n\n"
                    f"The current temperature is "
                    f"{info['temperature']}°C."
                )

            elif time_requested:

                reply = (
                    f"The current time in "
                    f"{info['city']}, "
                    f"{info['country']} is "
                    f"{info['time']} on "
                    f"{info['date']}."
                )

            else:

                reply = (
                    f"The current temperature in "
                    f"{info['city']}, "
                    f"{info['country']} is "
                    f"{info['temperature']}°C."
                )

            return jsonify({
                "reply": reply
            })

        except Exception as e:

            print(
                "TIME/WEATHER ERROR:",
                e
            )

            return jsonify({
                "reply":
                "I couldn't get the current time or weather right now."
            })


    # =========================
    # HUGGING FACE AI
    # =========================

    try:

        hf_token = os.getenv("HF_TOKEN")

        if not hf_token:

            print("AI ERROR: HF_TOKEN is missing")

            return jsonify({
                "error":
                "HF_TOKEN is missing on the server."
            }), 500


        api_url = (
            "https://router.huggingface.co/v1/chat/completions"
        )


        headers = {

            "Authorization":
                f"Bearer {hf_token}",

            "Content-Type":
                "application/json"
        }


        payload = {

            "model":
                "openai/gpt-oss-120b:fastest",

            "messages": [

                {
                    "role":
                        "system",

                    "content":
                        """
You are Chetak, a helpful personal AI assistant.

Your name is exactly Chetak.
The spelling is C-H-E-T-A-K.

If the user asks your name, answer:
"My name is Chetak."

If the user asks who created you, who made you,
who invented you, or who is your creator, answer:
"Tanmay Rana created me."

If the user says hi, hello, hey, or gives a greeting,
respond with a normal friendly greeting.

For all other questions, answer the user's actual question normally.

Never introduce yourself or say "My name is Chetak"
unless the user asks about your name.

Keep answers clear, natural and helpful.

Do not claim that you cannot answer a normal question
just because it is difficult. Try your best to answer it.
"""
                },

                {
                    "role":
                        "user",

                    "content":
                        user_message
                }
            ],

            "stream":
                False
        }


        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60
        )


        print(
            "HUGGING FACE STATUS:",
            response.status_code
        )

        print(
            "HUGGING FACE RESPONSE:",
            response.text[:1000]
        )


        response.raise_for_status()


        response_data = response.json()


        answer = (
            response_data["choices"][0]
            ["message"]["content"]
        )


        # =========================
        # CORRECT CHETAK SPELLING
        # =========================

        replacements = {

            "Chetal": "Chetak",
            "chetal": "Chetak",
            "Chetac": "Chetak",
            "chetac": "Chetak",
            "Chetik": "Chetak",
            "chetik": "Chetak",
            "Chetek": "Chetak",
            "chetek": "Chetak"
        }


        for old, new in replacements.items():

            answer = answer.replace(
                old,
                new
            )


        return jsonify({
            "reply":
                answer
        })


    except requests.exceptions.HTTPError as e:

        print(
            "HUGGING FACE HTTP ERROR:",
            e
        )

        print(
            "STATUS:",
            response.status_code
        )

        print(
            "RESPONSE:",
            response.text[:1000]
        )

        return jsonify({
            "error":
                f"Hugging Face error: {response.status_code}"
        }), 500


    except requests.exceptions.RequestException as e:

        print(
            "HUGGING FACE CONNECTION ERROR:",
            e
        )

        return jsonify({
            "error":
                "Could not connect to Hugging Face."
        }), 500


    except Exception as e:

        print(
            "AI ERROR:",
            e
        )

        return jsonify({
            "error":
                "AI error occurred. Check Render logs."
        }), 500


# =========================
# OPEN LAPTOP APPLICATION
# =========================

@app.route(
    "/open_app",
    methods=["POST"]
)
def open_app():

    data = request.get_json() or {}

    command = data.get(
        "command",
        ""
    ).lower().strip()


    apps = {

        "spotify":
            "spotify",

        "chrome":
            "chrome",

        "google chrome":
            "chrome",

        "calculator":
            "calc",

        "notepad":
            "notepad",

        "paint":
            "mspaint",

        "file explorer":
            "explorer",

        "explorer":
            "explorer"
    }


    app_name = None


    for name in apps:

        if name in command:

            app_name = apps[name]

            break


    if not app_name:

        return jsonify({
            "reply":
            "I don't know how to open that application yet."
        })


    try:

        subprocess.Popen(
            [
                "cmd",
                "/c",
                "start",
                "",
                app_name
            ],
            shell=False
        )


        return jsonify({
            "reply":
            f"Opening {app_name}."
        })


    except Exception as e:

        print(
            "APP ERROR:",
            e
        )

        return jsonify({
            "reply":
            "I couldn't open that application."
        })


# =========================
# RUN FLASK
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )