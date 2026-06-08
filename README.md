# Road Distance Calculator

## Overview
This Streamlit application calculates road distances between source and destination pincodes using OpenStreetMap (Nominatim) and OSRM routing.

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Input Format

Excel file containing two sheets:

### From Pin Details
Columns:
- state
- city
- postal_code

### To Pin Details
Columns:
- state
- city
- postal_code

Both sheets must have the same number of rows.

## Output

- Road Distance (km)
- CSV Download
- Excel Download    