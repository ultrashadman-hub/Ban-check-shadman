from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

# ================= CONFIG =================

INFO_API = "https://shadman-six.vercel.app/info"

BAN_API = "https://ff.garena.com/api/antihack/check_banned"

DEVELOPER = "@slowgoods"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "referer": "https://ff.garena.com/en/support/",
    "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH"
}

BAN_PERIOD_MAP = {
    604800: "7 Days",
    259200: "3 Days",
    86400: "1 Day",
    3600: "1 Hour",
    1800: "30 Minutes",
    600: "10 Minutes",
    0: "Permanent / Not Specified"
}


# ================= BAN PERIOD =================

def format_ban_period(seconds):

    try:
        seconds = int(seconds)

        if seconds in BAN_PERIOD_MAP:
            return BAN_PERIOD_MAP[seconds]

        if seconds > 0:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60

            parts = []

            if days:
                parts.append(f"{days} Days")

            if hours:
                parts.append(f"{hours} Hours")

            if minutes:
                parts.append(f"{minutes} Minutes")

            return " ".join(parts) if parts else f"{seconds} Seconds"

        return "Permanent / Not Specified"

    except (ValueError, TypeError):
        return "Unknown"


# ================= MAIN API =================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "service": "Free Fire Ban Check API",
        "status": "online",
        "developer": DEVELOPER
    })


@app.route("/bancheck", methods=["GET"])
def bancheck():

    uid = request.args.get("uid", "").strip()

    if not uid:
        return jsonify({
            "error": "UID is required",
            "status_code": 400
        }), 400

    if not uid.isdigit():
        return jsonify({
            "error": "Invalid UID",
            "status_code": 400
        }), 400

    # Default values
    nickname = "Unknown"
    level = 0
    region = "Unknown"
    last_login = "Unknown"
    signature = ""
    clan_name = "None"
    credit_score = 100

    info_error = None
    ban_error = None

    # ================= PLAYER INFO =================

    try:

        info_response = requests.get(
            INFO_API,
            params={"uid": uid},
            timeout=20
        )

        info_response.raise_for_status()

        data = info_response.json()

        if not isinstance(data, dict):
            raise ValueError("Invalid Info API JSON structure")

        basic = data.get("BasicInformation") or {}
        guild = data.get("GuildInformation") or {}
        activity = data.get("ActivityInformation") or {}

        # Basic Information
        nickname = basic.get("Name", "Unknown")
        level = basic.get("Level", 0)
        region = basic.get("Region", "Unknown")
        signature = basic.get("Signature", "")
        credit_score = basic.get("HonorScore", 100)

        # Guild Information
        clan_name = guild.get("GuildName", "None")

        # Activity Information
        last_login = activity.get("LastLogin", "Unknown")

    except Exception as e:

        info_error = str(e)

    # ================= BAN CHECK =================

    is_banned = None
    ban_period = None
    formatted_ban_period = "Unknown"
    ban_status_text = "Unable to Verify"
    ban_reason = None
    ban_date = "N/A"

    try:

        ban_response = requests.get(
            BAN_API,
            params={
                "lang": "en",
                "uid": uid
            },
            headers=HEADERS,
            timeout=15
        )

        ban_response.raise_for_status()

        ban_data = ban_response.json().get("data", {})

        if "is_banned" not in ban_data:
            raise ValueError("Ban API returned invalid data")

        is_banned = bool(ban_data.get("is_banned", 0))

        raw_period = ban_data.get("period", 0)

        if is_banned:

            ban_status_text = "BANNED"

            ban_period = int(raw_period)

            formatted_ban_period = format_ban_period(
                ban_period
            )

            # Garena does not provide a confirmed ban reason here
            ban_reason = "Not provided by Garena"

        else:

            ban_status_text = "NOT BANNED"
            ban_period = 0
            formatted_ban_period = "N/A"

    except Exception as e:

        ban_error = str(e)

    # ================= FINAL RESULT =================

    result = {

        "nickname": str(nickname),

        "uid": uid,

        "AccountLevel": level,

        "region": str(region),

        "AccountLastLogin": str(last_login),

        "status": ban_status_text,

        "is_banned": is_banned,

        "ban_period": formatted_ban_period,

        "ban_period_seconds": ban_period,

        "ban_reason": ban_reason,

        "ban_date": ban_date,

        "signature": signature,

        "clan_name": clan_name,

        "credit_score": credit_score,

        "developer": DEVELOPER,

        "error": {
            "info_api": info_error,
            "ban_api": ban_error
        } if info_error or ban_error else None

    }

    return jsonify(result)


# ================= HEALTH CHECK =================

@app.route("/api", methods=["GET"])
def api_info():

    return jsonify({
        "status": "online",
        "service": "Free Fire Ban Check API",
        "developer": DEVELOPER
    })


# ================= RUN =================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )