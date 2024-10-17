import os
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from tqdm import tqdm
import re

# Function to normalize county names
def normalize_county_name(county_name):
    # Check if county_name is a valid string
    if isinstance(county_name, str):
        # Convert to lowercase, strip leading/trailing spaces, and remove punctuation
        county_name = county_name.lower().strip()

        # Remove common suffixes like "county", "co.", "co", etc.
        county_name = re.sub(r'(county|co\.?|[\?\.])$', '', county_name).strip()

        # Capitalize the first letter of each word for consistency
        return county_name.title()
    else:
        # If it's not a string (e.g., NaN), return an empty string or handle appropriately
        return ''

def split_csv_by_state():
    # Create a Tkinter root window (hidden)
    Tk().withdraw()

    # Prompt the user to select the CSV file
    input_csv = askopenfilename(title="Select the CSV file", filetypes=[("CSV files", "*.csv")])
    if not input_csv:
        print("No file selected. Exiting.")
        return

    # Prompt the user to enter the state they want to filter
    state_name = input("Enter the state name to process: ").strip()

    # Prompt the user to select the county list file (e.g., county_list.txt)
    county_list_file = askopenfilename(title="Select the county list file", filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")])
    if not county_list_file:
        print("No county list file selected. Exiting.")
        return

    # Read the county list from the external file (assuming it's a text file with one county per line)
    with open(county_list_file, 'r') as file:
        county_list = [normalize_county_name(line.strip()) for line in file.readlines()]

    # Try reading the input CSV, skipping bad lines
    try:
        data = pd.read_csv(input_csv, encoding='ISO-8859-1', on_bad_lines='skip', low_memory=False)
    except UnicodeDecodeError:
        print("Error decoding the file. Please check the encoding.")
        return
    except pd.errors.ParserError as e:
        print(f"Parser error: {e}")
        return

    # Ensure the columns are named 'stateProvince' and 'county'
    if 'stateProvince' not in data.columns or 'county' not in data.columns:
        raise ValueError("The CSV file must contain 'stateProvince' and 'county' columns.")

    # Normalize county names in the dataset
    data['normalized_county'] = data['county'].apply(normalize_county_name)

    # Filter for entries only in the selected state and the counties in the list
    state_data = data[(data['stateProvince'].str.lower() == state_name.lower()) & (data['normalized_county'].isin(county_list))]

    # Create output directory for the new CSV files
    output_dir = f'{state_name.lower()}_counties'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get the total number of counties for the progress bar
    unique_counties = state_data['normalized_county'].nunique()

    # Group data by normalized county and save each county's data to a separate CSV file
    for county, county_data in tqdm(state_data.groupby('normalized_county'), total=unique_counties, desc=f"Processing {state_name} Counties"):
        # Create filename as "<State>_<county>.csv"
        output_filename = os.path.join(output_dir, f"{state_name}_{county}.csv")
        # Save to new CSV
        county_data.to_csv(output_filename, index=False)

    print(f"Files created in directory: {output_dir}")

# Run the function
split_csv_by_state()
