import streamlit as st
import pandas as pd
import requests
import time
from io import BytesIO


# ---------------------------------------------------------
# STREAMLIT CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Road Distance Calculator",
    layout="wide"
)

st.title("Road Distance Calculator")
st.write(
    "Upload an Excel file containing sheets: "
    "**From Pin Details** and **To Pin Details**"
)


# ---------------------------------------------------------
# STATE MAPPING
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def clean_text(value):
    """Convert a value to clean string."""
    if pd.isna(value):
        return ""

    return str(value).strip()


def clean_pin(value):
    """Clean Excel pincode values."""
    if pd.isna(value):
        return ""

    value = str(value).strip()

    # Handle Excel values such as 400001.0
    if value.endswith(".0"):
        value = value[:-2]

    return value


def normalize_state(state):
    """Convert state abbreviations into full state names."""
    state = clean_text(state).upper()

    return STATE_MAP.get(state, state)


def build_search_addresses(row):
    """
    Build multiple search queries for Nominatim.

    The program first tries the most detailed query,
    then falls back to simpler queries.
    """

    pincode = clean_pin(row["postal_code"])
    city = clean_text(row["city"])
    state = normalize_state(row["state"])

    return [
        f"{pincode}, {city}, {state}",
        f"{pincode}, {state}",
        f"{pincode}"
    ]


# ---------------------------------------------------------
# GEOCODING
# PINCODE/CITY/STATE -> LATITUDE/LONGITUDE
# ---------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_coordinates(search_addresses):
    """
    Convert a location description into latitude and longitude
    using Nominatim.

    search_addresses:
        Tuple containing possible search queries.
    """

    url = "https://nominatim.openstreetmap.org/search"

    headers = {
        "User-Agent": "RCPL-Road-Distance-Calculator/1.0"
    }

    for search_address in search_addresses:

        if not search_address.strip():
            continue

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

            # Basic India coordinate validation
            if not (6 <= lat <= 38 and 68 <= lon <= 98):
                continue

            return (lat, lon)

        except requests.RequestException:
            continue

        except (ValueError, KeyError, TypeError):
            continue

        # Avoid sending requests too quickly
        time.sleep(1)

    return None


# ---------------------------------------------------------
# ROAD DISTANCE
# LAT/LONG -> ROAD DISTANCE
# ---------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_road_distance(from_coord, to_coord):
    """
    Calculate driving distance between two coordinates
    using OSRM.
    """

    if from_coord is None or to_coord is None:
        return None

    lat1, lon1 = from_coord
    lat2, lon2 = to_coord

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
    )

    params = {
        "overview": "false"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=25
        )

        if response.status_code != 200:
            return None

        data = response.json()

        if data.get("code") != "Ok":
            return None

        distance_meters = data["routes"][0]["distance"]

        distance_km = distance_meters / 1000

        return round(distance_km, 2)

    except requests.RequestException:
        return None

    except (ValueError, KeyError, TypeError, IndexError):
        return None


# ---------------------------------------------------------
# EXCEL UPLOAD
# ---------------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)


if uploaded_file is not None:

    # -----------------------------------------------------
    # READ EXCEL FILE
    # -----------------------------------------------------

    try:

        from_df = pd.read_excel(
            uploaded_file,
            sheet_name="From Pin Details"
        )

        # Reset file position before reading another sheet
        uploaded_file.seek(0)

        to_df = pd.read_excel(
            uploaded_file,
            sheet_name="To Pin Details"
        )

    except Exception as e:

        st.error(
            f"Excel reading error: {e}"
        )

        st.stop()


    # -----------------------------------------------------
    # REQUIRED COLUMNS
    # -----------------------------------------------------

    required_cols = [
        "state",
        "city",
        "postal_code"
    ]


    missing_from = [
        col for col in required_cols
        if col not in from_df.columns
    ]

    missing_to = [
        col for col in required_cols
        if col not in to_df.columns
    ]


    if missing_from:

        st.error(
            "From Pin Details is missing columns: "
            + ", ".join(missing_from)
        )

        st.stop()


    if missing_to:

        st.error(
            "To Pin Details is missing columns: "
            + ", ".join(missing_to)
        )

        st.stop()


    # -----------------------------------------------------
    # CHECK ROW COUNTS
    # -----------------------------------------------------

    if len(from_df) != len(to_df):

        st.error(
            "Both sheets must contain the same number of rows."
        )

        st.stop()


    # -----------------------------------------------------
    # PREVIEW
    # -----------------------------------------------------

    st.subheader("From Pin Details")

    st.dataframe(
        from_df.head(),
        use_container_width=True
    )


    st.subheader("To Pin Details")

    st.dataframe(
        to_df.head(),
        use_container_width=True
    )


    st.write(
        f"Total locations to process: **{len(from_df)}**"
    )


    # -----------------------------------------------------
    # CALCULATE DISTANCE
    # -----------------------------------------------------

    if st.button(
        "Calculate Road Distance",
        type="primary"
    ):

        results = []

        progress = st.progress(0)

        status = st.empty()

        total = len(from_df)


        for i in range(total):

            from_row = from_df.iloc[i]
            to_row = to_df.iloc[i]


            # ---------------------------------------------
            # BUILD SEARCH QUERIES
            # ---------------------------------------------

            from_searches = build_search_addresses(
                from_row
            )

            to_searches = build_search_addresses(
                to_row
            )


            # ---------------------------------------------
            # GET COORDINATES
            # ---------------------------------------------

            from_coord = get_coordinates(
                tuple(from_searches)
            )

            to_coord = get_coordinates(
                tuple(to_searches)
            )


            # ---------------------------------------------
            # CALCULATE ROAD DISTANCE
            # ---------------------------------------------

            if from_coord is None:

                distance = "From Location Not Found"

            elif to_coord is None:

                distance = "To Location Not Found"

            else:

                distance_km = get_road_distance(
                    from_coord,
                    to_coord
                )

                if distance_km is None:

                    distance = "Route Not Found"

                else:

                    distance = distance_km


            # ---------------------------------------------
            # STORE RESULT
            # ---------------------------------------------

            results.append({

                "From State":
                    clean_text(from_row["state"]),

                "From City":
                    clean_text(from_row["city"]),

                "From Postal Code":
                    clean_pin(from_row["postal_code"]),

                "From Search 1":
                    from_searches[0],

                "From Search 2":
                    from_searches[1],

                "From Search 3":
                    from_searches[2],

                "From Coordinates":
                    str(from_coord),

                "To State":
                    clean_text(to_row["state"]),

                "To City":
                    clean_text(to_row["city"]),

                "To Postal Code":
                    clean_pin(to_row["postal_code"]),

                "To Search 1":
                    to_searches[0],

                "To Search 2":
                    to_searches[1],

                "To Search 3":
                    to_searches[2],

                "To Coordinates":
                    str(to_coord),

                "Road Distance (km)":
                    distance
            })


            # ---------------------------------------------
            # UPDATE PROGRESS
            # ---------------------------------------------

            current = i + 1

            status.write(
                f"Processing {current}/{total}"
            )

            progress.progress(
                current / total
            )


        # -------------------------------------------------
        # CREATE RESULT DATAFRAME
        # -------------------------------------------------

        result_df = pd.DataFrame(results)


        st.success(
            "Road distance calculation completed successfully!"
        )


        st.subheader("Results")

        st.dataframe(
            result_df,
            use_container_width=True
        )


        # -------------------------------------------------
        # DOWNLOAD CSV
        # -------------------------------------------------

        csv_data = result_df.to_csv(
            index=False
        ).encode("utf-8")


        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="road_distance_output.csv",
            mime="text/csv"
        )


        # -------------------------------------------------
        # DOWNLOAD EXCEL
        # -------------------------------------------------

        excel_buffer = BytesIO()

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl"
        ) as writer:

            result_df.to_excel(
                writer,
                index=False,
                sheet_name="Road Distance Results"
            )


        excel_buffer.seek(0)


        st.download_button(
            label="Download Excel",
            data=excel_buffer.getvalue(),
            file_name="road_distance_output.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )