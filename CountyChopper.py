import os
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from tqdm import tqdm
import re
import argparse
from pathlib import Path

def arg_setup():
    # set up argument parser
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=False, \
        help="Input directory path for a single CSV file.")
    ap.add_argument("-o", "--out", required=False, \
        help="Output directory path for multiple CSV files.")
    ap.add_argument("-v", "--verbose", action="store_true", \
        help="Detailed output.")
    args = vars(ap.parse_args())
    return args

# Function to normalize county names
def normalize_county_name(county_name):
    if isinstance(county_name, str):
        county_name = county_name.lower().strip()
        county_name = re.sub(r'(county|co\.?|[\?\.])$', '', county_name).strip()
        return county_name.title()
    else:
        return ''

# Function to count null collectionCodes and suggest substitution
def count_null_collectioncode(df):
    missing_collectioncode = df['collectionCode'].isna() | (df['collectionCode'] == '')
    null_count = missing_collectioncode.sum()

    if null_count > 0:
        substitute_counts = df.loc[missing_collectioncode, 'institutionCode'].value_counts()
        print(f"\nNumber of records with null or empty 'collectionCode': {null_count}")
        print("Potential substitutions using 'institutionCode':")
        print(substitute_counts)

        # Ask user if they want to make the substitution
        choice = input("\nWould you like to substitute missing 'collectionCode' values with 'institutionCode'? (yes/no): ").strip().lower()
        if choice == 'yes':
            df.loc[missing_collectioncode, 'collectionCode'] = df.loc[missing_collectioncode, 'institutionCode']
            print("Substitution applied.\n")
        else:
            print("No changes made.\n")

    return df

# Function to read configurations from Chopper_Config.txt in the script folder
def load_configurations():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(script_dir, 'Chopper_Config.txt')

    if not os.path.exists(config_file):
        print("Configuration file 'Chopper_Config.txt' not found in script directory.")
        return None

    collection_whitelist = set()
    collection_blacklist = set()
    counties = set()
    state_name = None
    in_county_section = False

    with open(config_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("collectionWhitelist:"):
                collection_whitelist.update(map(str.strip, line.split(":", 1)[1].split(',')))
            elif line.startswith("collectionBlacklist:"):
                collection_blacklist.update(map(str.strip, line.split(":", 1)[1].split(',')))
            elif line.startswith("state:"):
                state_name = line.split(":", 1)[1].strip()
            elif line.startswith("counties:"):
                in_county_section = True
            elif in_county_section and line:
                counties.add(normalize_county_name(line))

    return collection_whitelist, collection_blacklist, counties, state_name

def sanitize_filename(filename, replacement=''):
    """
    Sanitizes a string to be safe for use as a filename.

    Args:
        filename (str): The filename to sanitize.
        replacement (str, optional): The string to replace invalid characters with. Defaults to ''.

    Returns:
        str: The sanitized filename.
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', replacement, filename)
    # Remove leading and trailing spaces
    filename = filename.strip()
    # Shorten filename if it exceeds 255 characters
    filename = filename[:255]
    return filename

def split_csv_by_state():
    args = arg_setup()

    if args['input']:
        #print('input path:', args['input'])
        input_csv = Path(args['input']).resolve()
    else:
        # 
        Tk().withdraw()
        input_csv = askopenfilename(title="Select the CSV file", filetypes=[("CSV files", "*.csv")])
        if not input_csv:
            print("No file selected. Exiting.")
            return

    print('input_csv:', input_csv)

    if args['out']:
        print('output path:', args['out'])
        output_dir = Path(args['out']).resolve()
    else:
        # Prompt user for output directory
        output_dir = input("Enter the directory where output files should be saved (or press Enter for default): ").strip()
    
    if not output_dir:
        #output_dir = f"{state_name.lower()}_counties"
        output_dir = "chopper_output_counties"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Output files will be saved in: {output_dir}")

    # Load configurations from Chopper_Config.txt
    config = load_configurations()
    if not config:
        return

    collection_whitelist, collection_blacklist, county_list, state_name = config

    if not state_name:
        print("No state specified in the configuration file. Exiting.")
        return

    try:
        #data = pd.read_csv(input_csv, encoding='ISO-8859-1', dtype=str, on_bad_lines='skip', low_memory=False)
        data = pd.read_csv(input_csv, on_bad_lines='skip', low_memory=False)
    except (UnicodeDecodeError, pd.errors.ParserError) as e:
        print(f"Error reading the file: {e}")
        return

    if 'stateProvince' not in data.columns or 'county' not in data.columns or 'collectionCode' not in data.columns:
        raise ValueError("The CSV file must contain 'stateProvince', 'county', and 'collectionCode' columns.")

    # Run the pre-check for missing collectionCode
    #data = count_null_collectioncode(data)

    data['normalized_county'] = data['county'].apply(normalize_county_name)

    # Apply whitelist/blacklist filter for collectionCode
    data['collectionCode'] = data['collectionCode'].astype(str)
    
    # Separate out records that are whitelisted
    whitelist_data = data[data['collectionCode'].isin(collection_whitelist)]

    # Exclude records with collectionCode on the blacklist
    data = data[~data['collectionCode'].isin(collection_blacklist)]

    # Combine the filtered data with the whitelisted data that bypasses all filters
    final_data = pd.concat([whitelist_data, data])

    # Filter for entries only in the selected state and the counties in the list
    #state_data = final_data[(final_data['stateProvince'].str.lower() == state_name.lower()) & (final_data['normalized_county'].isin(county_list))]
    state_data = final_data

    unique_counties = state_data['normalized_county'].nunique()
    #print('county')

    for county, county_data in tqdm(state_data.groupby('normalized_county'), total=unique_counties, desc=f"Processing {state_name} Counties"):
        output_filename = f"{state_name}_{county}.csv"
        output_filename = sanitize_filename(output_filename, replacement='-')
        output_path = os.path.join(output_dir, output_filename)
        county_data.to_csv(output_path, index=False)

    print(f"Files created in directory: {output_dir}")

# Run the function
split_csv_by_state()
