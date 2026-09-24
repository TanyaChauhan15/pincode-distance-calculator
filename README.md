# Pincode-to-Pincode Road Distance Calculator

A Streamlit application that calculates road distances between source and destination pincodes using OpenStreetMap Nominatim for geocoding and OSRM for road routing.

## Features

- Calculate road distance between multiple pincode pairs
- Upload Excel files for bulk processing
- Automatic geocoding using OpenStreetMap
- Road distance calculation using OSRM
- Download results as CSV or Excel

## Tech Stack

- Python
- Streamlit
- Pandas
- OpenStreetMap Nominatim
- OSRM

## Installation

Clone the repository:

```bash
git clone https://github.com/TanyaChauhan15/pincode-distance-calculator.git
cd pincode-distance-calculator

Install the required dependencies:

pip install -r requirements.txt
Run
streamlit run app.py

The application will open at http://localhost:8501.

Input Format

Upload an Excel file containing two sheets:

From Pin Details

Required columns:

state
city
postal_code
To Pin Details

Required columns:

state
city
postal_code

Both sheets should contain the same number of rows. Each row represents one source-destination pair.

Output

The application provides:

Road distance in kilometers
CSV download
Excel download
Sample Input

A sample Excel file is included as sample.xlsx.

Author

Tanya Chauhan

GitHub: https://github.com/TanyaChauhan15
