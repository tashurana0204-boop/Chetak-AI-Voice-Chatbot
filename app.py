from flask import Flask, render_template, request, jsonify
import requests
import os
import subprocess
import re
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


    # Get current temperature
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

    if temperature is None:
        raise ValueError(
            "Temperature data was not returned by weather service"
        )


    # Get local time
    local_time = datetime.now(
        ZoneInfo(timezone)
    )


    return {
        "city": city,
        "country": country,
        "timezone": timezone,
        "time": local_time.strftime("%I:%M %p"),
        "date": local_time.strftime("%d %B %Y"),
        "temperature": temperature
    }


# =========================
# DETECT TIME / WEATHER
# =========================

def extract_location(message):

    text = message.strip()

    patterns = [

        # What is the time in Perth?
        r"(?:what(?:'s| is)?|tell me|give me)?\s*"
        r"(?:the\s+)?time\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # Current time in Perth
        r"(?:current|local)\s+time\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # What is the temperature in Delhi?
        r"(?:what(?:'s| is)?|tell me|give me)?\s*"
        r"(?:the\s+)?(?:temperature|temp)\s+(?:in|at|of)\s+(.+?)[?.!]*$",

        # Weather in Delhi
        r"(?:what(?:'s| is)?|tell me|give me)?\s*"
        r"(?:the\s+)?weather\s+(?:in|at|of)\s+(.+?)[?.!]*$",

    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            location = match.group(
                1
            ).strip()

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

    data = request.get_json()

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


            time_requested = (
                is_time_question(
                    user_message
                )
            )


            weather_requested = (
                is_weather_question(
                    user_message
                )
            )


            # Both time and temperature
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


            # Time only
            elif time_requested:

                reply = (
                    f"The current time in "
                    f"{info['city']}, "
                    f"{info['country']} is "
                    f"{info['time']} on "
                    f"{info['date']}."
                )


            # Temperature / weather
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
                "I couldn't get the current time or weather right now. Please check your internet connection."
            })


    # =========================
    # HUGGING FACE AI
    # =========================

    try:

        hf_token = os.getenv(
            "HF_TOKEN"
        )

        if not hf_token:

            raise ValueError(
                "HF_TOKEN is missing."
            )


        response = requests.post(

            "https://router.huggingface.co/v1/chat/completions",

            headers={
                "Authorization":
                    f"Bearer {hf_token}",

                "Content-Type":
                    "application/json"
            },

            json={

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
            },

            timeout=60
        )


        response.raise_for_status()

        response_data = response.json()

        answer = response_data[
            "choices"
        ][0][
            "message"
        ][
            "content"
        ]


        # =========================
        # CORRECT CHETAK SPELLING
        # =========================

        answer = answer.replace(
            "Chetal",
            "Chetak"
        )

        answer = answer.replace(
            "chetal",
            "Chetak"
        )

        answer = answer.replace(
            "Chetac",
            "Chetak"
        )

        answer = answer.replace(
            "chetac",
            "Chetak"
        )

        answer = answer.replace(
            "Chetik",
            "Chetak"
        )

        answer = answer.replace(
            "chetik",
            "Chetak"
        )

        answer = answer.replace(
            "Chetek",
            "Chetak"
        )

        answer = answer.replace(
            "chetek",
            "Chetak"
        )


        return jsonify({
            "reply":
                answer
        })


    except Exception as e:

        print(
            "AI ERROR:",
            e
        )

        return jsonify({
            "error":
            "AI connection failed."
        }), 500


# =========================
# OPEN LAPTOP APPLICATION
# =========================

@app.route(
    "/open_app",
    methods=["POST"]
)
def open_app():

    data = request.get_json()

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

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )