import os
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from tqdm import tqdm
import re

# Function to normalize county names
def normalize_county_name(county_name):
    if isinstance(county_name, str):
        county_name = county_name.lower().strip()
        county_name = re.sub(r'(county|co\.?|[\?\.])$', '', county_name).strip()
        return county_name.title()
    else:
        return ''

# Function to read configurations from Chopper_Config.txt in the script folder
def load_configurations():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(script_dir, 'Chopper_Config.txt')

    if not os.path.exists(config_file):
        print("Configuration file 'Chopper_Config.txt' not found in script directory.")
        return None

    whitelist = set()
    blacklist = set()
    georeference_sources_blacklist = set()
    georeference_verification_status_blacklist = set()
    georeference_remarks_blacklist = set()  # New blacklist for georeferenceRemarks
    counties = set()
    state_name = None
    coordinate_uncertainty_threshold = 10000  # Default value
    filter_georeferenced_by = True  # Default: apply filter
    filter_georeference_remarks = True  # Default: apply filter
    in_county_section = False

    with open(config_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("whitelist:"):
                whitelist.update(map(str.strip, line.split(":", 1)[1].split(',')))
            elif line.startswith("blacklist:"):
                blacklist.update(map(str.strip, line.split(":", 1)[1].split(',')))
            elif line.startswith("georeferenceSourcesBlacklist:"):
                georeference_sources_blacklist.update(map(str.strip, line.split(":", 1)[1].split(',')))
            elif line.startswith("coordinateUncertaintyThreshold:"):
                coordinate_uncertainty_threshold = int(line.split(":", 1)[1].strip())
            elif line.startswith("filterGeoreferencedBy:"):
                filter_georeferenced_by = line.split(":", 1)[1].strip().lower() == 'true'
            elif line.startswith("filterGeoreferenceRemarks:"):
                filter_georeference_remarks = line.split(":", 1)[1].strip().lower() == 'true'
            elif line.startswith("georeferenceVerificationStatusBlacklist:"):
                georeference_verification_status_blacklist.update(map(str.strip, line.split(":", 1)[1].split(',')))
            elif line.startswith("georeferenceRemarksBlacklist:"):  # New blacklist for georeferenceRemarks
                georeference_remarks_blacklist.update(map(str.strip, line.split(":", 1)[1].split(',')))
            elif line.startswith("state:"):
                state_name = line.split(":", 1)[1].strip()
            elif line.startswith("counties:"):
                in_county_section = True
            elif in_county_section and line:
                counties.add(normalize_county_name(line))

    return (whitelist, blacklist, georeference_sources_blacklist, 
            georeference_verification_status_blacklist, georeference_remarks_blacklist, counties, state_name, 
            coordinate_uncertainty_threshold, filter_georeferenced_by, filter_georeference_remarks)

def split_csv_by_state():
    Tk().withdraw()

    input_csv = askopenfilename(title="Select the CSV file", filetypes=[("CSV files", "*.csv")])
    if not input_csv:
        print("No file selected. Exiting.")
        return

    # Load configurations from Chopper_Config.txt
    config = load_configurations()
    if not config:
        return

    (whitelist, blacklist, georeference_sources_blacklist, 
    georeference_verification_status_blacklist, georeference_remarks_blacklist, county_list, state_name, 
    coordinate_uncertainty_threshold, filter_georeferenced_by, 
    filter_georeference_remarks) = config

    if not state_name:
        print("No state specified in the configuration file. Exiting.")
        return

    try:
        data = pd.read_csv(input_csv, encoding='ISO-8859-1', on_bad_lines='skip', low_memory=False)
    except (UnicodeDecodeError, pd.errors.ParserError) as e:
        print(f"Error reading the file: {e}")
        return

    if 'stateProvince' not in data.columns or 'county' not in data.columns or 'institutionCode' not in data.columns or 'locality' not in data.columns:
        raise ValueError("The CSV file must contain 'stateProvince', 'county', 'institutionCode', and 'locality' columns.")

    data['normalized_county'] = data['county'].apply(normalize_county_name)
    data['filterFailed'] = ""  # New column to track failed filters

    # Apply whitelist/blacklist filter for institutionCode
    data['institutionCode'] = data['institutionCode'].astype(str)
    
    # Mark records with institutionCode in the blacklist
    data.loc[data['institutionCode'].isin(blacklist), 'filterFailed'] += "Blacklisted institutionCode; "

    # Mark records that are whitelisted (these bypass other filters)
    data.loc[data['institutionCode'].isin(whitelist), 'filterFailed'] += "Whitelisted institutionCode; "

    # Include records with null locality only if institutionCode is in the whitelist
    data_with_locality = data['locality'].notnull()
    data_null_locality = data['locality'].isnull() & ~data['institutionCode'].isin(whitelist)
    data.loc[data_null_locality, 'filterFailed'] += "Null locality; "

    # Apply coordinateUncertaintyInMeters filter
    coord_fail = (data['coordinateUncertaintyInMeters'] >= coordinate_uncertainty_threshold) | (data['coordinateUncertaintyInMeters'].isnull())
    data.loc[coord_fail, 'filterFailed'] += "Coordinate uncertainty too high or missing; "

    # Apply georeferencedBY and georeferenceRemarks filters if toggled on in the config
    if filter_georeferenced_by:
        data.loc[data['georeferencedBy'].isnull(), 'filterFailed'] += "Null georeferencedBy; "

    if filter_georeference_remarks:
        data.loc[data['georeferenceRemarks'].isnull(), 'filterFailed'] += "Null georeferenceRemarks; "

    # Apply georeferenceSourcesBlacklist filter
    data.loc[data['georeferenceSources'].isin(georeference_sources_blacklist), 'filterFailed'] += "Blacklisted georeferenceSources; "

    # Apply georeferenceVerificationStatusBlacklist filter
    if 'georeferenceVerificationStatus' in data.columns:
        data.loc[data['georeferenceVerificationStatus'].isin(georeference_verification_status_blacklist), 'filterFailed'] += "Blacklisted georeferenceVerificationStatus; "

    # Apply georeferenceRemarksBlacklist filter - substring search
    if 'georeferenceRemarks' in data.columns:
        for remark in georeference_remarks_blacklist:
            data.loc[data['georeferenceRemarks'].str.contains(remark, case=False, na=False), 'filterFailed'] += f"Contains blacklisted remark: {remark}; "

    # Filter for entries only in the selected state and the counties in the list
    state_data = data[(data['stateProvince'].str.lower() == state_name.lower()) & (data['normalized_county'].isin(county_list))]

    output_dir = f'{state_name.lower()}_counties'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    unique_counties = state_data['normalized_county'].nunique()

    for county, county_data in tqdm(state_data.groupby('normalized_county'), total=unique_counties, desc=f"Processing {state_name} Counties"):
        output_filename = os.path.join(output_dir, f"{state_name}_{county}.csv")
        county_data.to_csv(output_filename, index=False)

    print(f"Files created in directory: {output_dir}")

# Run the function
split_csv_by_state()
