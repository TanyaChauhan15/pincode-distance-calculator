import streamlit as st
import pandas as pd
import requests
import time
from io import BytesIO

st.set_page_config(page_title="Road Distance Calculator", layout="wide")

st.title("Road Distance Calculator")
st.write("Upload Excel with sheets: **From Pin Details** and **To Pin Details**")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

geo_cache = {}

STATE_MAP = {
    "MAH": "Maharashtra",
    "MH": "Maharashtra",
    "KAR": "Karnataka",
    "KA": "Karnataka",
    "TG": "Telangana",
    "TS": "Telangana",
    "AP": "Andhra Pradesh",
    "RJ": "Rajasthan",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "UP": "Uttar Pradesh",
    "MP": "Madhya Pradesh",
    "AS": "Assam",
    "KER": "Kerala",
    "KL": "Kerala",
    "TN": "Tamil Nadu",
    "OR": "Odisha",
    "UC": "Uttarakhand",
    "UK": "Uttarakhand",
}


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_pin(value):
    if pd.isna(value):
        return ""
    return str(value).strip().replace(".0", "")


def normalize_state(state):
    state = clean_text(state).upper()
    return STATE_MAP.get(state, state)


def build_search_addresses(row):
    pincode = clean_pin(row["postal_code"])
    city = clean_text(row["city"])
    state = normalize_state(row["state"])

    return [
        f"{pincode}, {city}, {state}",
        f"{pincode}, {state}",
        f"{pincode}"
    ]


def get_coordinates(row):
    search_addresses = build_search_addresses(row)
    cache_key = "|".join(search_addresses)

    if cache_key in geo_cache:
        return geo_cache[cache_key]

    url = "https://nominatim.openstreetmap.org/search"

    headers = {
        "User-Agent": "RoadDistanceCalculator/1.0"
    }

    for search_address in search_addresses:
        params = {
            "q": search_address,
            "format": "json",
            "limit": 1,
            "countrycodes": "in"
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=20
            )

            if response.status_code != 200:
                continue

            data = response.json()

            if not data:
                continue

            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])

            if not (6 <= lat <= 38 and 68 <= lon <= 98):
                continue

            coord = (lat, lon)
            geo_cache[cache_key] = coord

            time.sleep(1)
            return coord

        except Exception:
            continue

    geo_cache[cache_key] = None
    return None


def get_road_distance(from_coord, to_coord):
    lat1, lon1 = from_coord
    lat2, lon2 = to_coord

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
    )

    params = {"overview": "false"}

    try:
        response = requests.get(url, params=params, timeout=25)
        data = response.json()

        if data.get("code") != "Ok":
            return None

        return round(data["routes"][0]["distance"] / 1000, 2)

    except Exception:
        return None


if uploaded_file is not None:
    try:
        from_df = pd.read_excel(uploaded_file, sheet_name="From Pin Details")
        to_df = pd.read_excel(uploaded_file, sheet_name="To Pin Details")
    except Exception as e:
        st.error(f"Excel reading error: {e}")
        st.stop()

    required_cols = ["state", "city", "postal_code"]

    if not all(col in from_df.columns for col in required_cols):
        st.error("From Pin Details sheet must contain: state, city, postal_code")
        st.stop()

    if not all(col in to_df.columns for col in required_cols):
        st.error("To Pin Details sheet must contain: state, city, postal_code")
        st.stop()

    if len(from_df) != len(to_df):
        st.error("Both sheets must have same number of rows")
        st.stop()

    st.subheader("From Preview")
    st.dataframe(from_df.head())

    st.subheader("To Preview")
    st.dataframe(to_df.head())

    if st.button("Calculate Road Distance"):
        results = []
        progress = st.progress(0)
        status = st.empty()

        total = len(from_df)

        for i in range(total):
            from_row = from_df.iloc[i]
            to_row = to_df.iloc[i]

            from_coord = get_coordinates(from_row)
            to_coord = get_coordinates(to_row)

            if from_coord is None:
                distance = "From Location Not Found"
            elif to_coord is None:
                distance = "To Location Not Found"
            else:
                d = get_road_distance(from_coord, to_coord)
                distance = d if d is not None else "Route Not Found"

            from_searches = build_search_addresses(from_row)
            to_searches = build_search_addresses(to_row)

            results.append({
                "From State": clean_text(from_row["state"]),
                "From City": clean_text(from_row["city"]),
                "From Postal Code": clean_pin(from_row["postal_code"]),
                "From Search 1": from_searches[0],
                "From Search 2": from_searches[1],
                "From Search 3": from_searches[2],
                "From Coordinates": str(from_coord),

                "To State": clean_text(to_row["state"]),
                "To City": clean_text(to_row["city"]),
                "To Postal Code": clean_pin(to_row["postal_code"]),
                "To Search 1": to_searches[0],
                "To Search 2": to_searches[1],
                "To Search 3": to_searches[2],
                "To Coordinates": str(to_coord),

                "Road Distance (km)": distance
            })

            status.write(f"Processing {i + 1}/{total}")
            progress.progress((i + 1) / total)

        result_df = pd.DataFrame(results)

        st.success("Completed")
        st.dataframe(result_df)

        csv_data = result_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download CSV",
            csv_data,
            "road_distance_output.csv",
            "text/csv"
        )

        excel_buffer = BytesIO()
        result_df.to_excel(excel_buffer, index=False, engine="openpyxl")

        st.download_button(
            "Download Excel",
            excel_buffer.getvalue(),
            "road_distance_output.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )