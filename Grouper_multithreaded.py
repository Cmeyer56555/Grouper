import os
import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askdirectory
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz
from datetime import datetime
import time
import sys
import re
import multiprocessing as mp
import argparse
from tqdm import tqdm

def arg_setup():
    # set up argument parser
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=False, \
        help="Input directory path for CSV files.")
    ap.add_argument("-v", "--verbose", action="store_true", \
        help="Detailed output.")
    args = vars(ap.parse_args())
    return args

# Function to display the custom fish progress bar
def fish_progress_bar(iterable, total=None, desc="Processing"):
    total = total or len(iterable)  # Set total if not provided
    fish = '><(((º>'
    bar_length = 40  # Length of the progress bar in characters
    
    for i, item in enumerate(iterable):
        progress = (i + 1) / total
        fish_position = int(progress * bar_length)  # Calculate fish position
        
        # Build the progress bar with the moving fish
        bar = ' ' * fish_position + fish + ' ' * (bar_length - fish_position)
        
        # Print the progress bar with the description
        sys.stdout.write(f'\r{desc}: [{bar}] {int(progress * 100)}%')
        sys.stdout.flush()
        
        yield item  # Yield the item in the iterable to keep the functionality intact
        #time.sleep(0.1)  # Small delay to simulate work (remove in actual use)
    
    sys.stdout.write('\n')  # New line when complete

# Function to extract and normalize compass directions from the locality string
def extract_compass_direction(locality):
    if not isinstance(locality, str):  # Ensure locality is a string
        return None
    
    compass_patterns = {
        'N': r'\b[Nn]orth\b|\b[Nn]\b',
        'NE': r'\b[Nn]orth[eE]ast\b|\b[Nn][Ee]\b',
        'E': r'\b[Ee]ast\b|\b[Ee]\b',
        'SE': r'\b[Ss]outh[eE]ast\b|\b[Ss][Ee]\b',
        'S': r'\b[Ss]outh\b|\b[Ss]\b',
        'SW': r'\b[Ss]outh[wW]est\b|\b[Ss][Ww]\b',
        'W': r'\b[Ww]est\b|\b[Ww]\b',
        'NW': r'\b[Nn]orth[wW]est\b|\b[Nn][Ww]\b'
    }
    
    for direction, pattern in compass_patterns.items():
        if re.search(pattern, locality):
            return direction
    return None

# Function to extract and normalize distances from the locality string
def extract_distance(locality):
    if not isinstance(locality, str):  # Ensure locality is a string
        return None, None
    
    # Regular expression to find distances with units like km, miles, meters, etc.
    distance_pattern = r'(\d+(\.\d+)?)\s*(km|kilometers|miles|mi|meters|m|feet|ft|yards|yd)'
    
    match = re.search(distance_pattern, locality)
    if match:
        # Extract the number and unit, and normalize the unit
        distance_value = float(match.group(1))
        unit = match.group(3).lower()
        
        if unit in ['kilometers', 'km']:
            unit = 'km'
        elif unit in ['miles', 'mi']:
            unit = 'miles'
        elif unit in ['meters', 'm']:
            unit = 'm'
        elif unit in ['feet', 'ft']:
            unit = 'ft'
        elif unit in ['yards', 'yd']:
            unit = 'yd'
        
        return distance_value, unit
    return None, None

# Function to calculate similarity between two text fields
def compare_fields(field1, field2, method='fuzzy', threshold=80, compass1=None, compass2=None, distance1=None, distance2=None):
    locality_match = False
    if method == 'fuzzy':
        locality_match = fuzz.token_sort_ratio(field1, field2) >= threshold
    elif method == 'cosine':
        vectorizer = TfidfVectorizer().fit_transform([field1, field2])
        cosine_sim = cosine_similarity(vectorizer[0:1], vectorizer[1:2])
        locality_match = cosine_sim[0][0] >= threshold / 100
    
    # Check if compass directions and distances match exactly
    compass_match = compass1 == compass2
    distance_match = distance1 == distance2
    
    return locality_match and compass_match and distance_match

# Modify the find_potential_duplicates function to include compass and distance extraction
def find_potential_duplicates(df, similarity_threshold, method='fuzzy'):
    groups = []
    group_id = 1
    assigned_groups = [-1] * len(df)  # Initialize all records as ungrouped
    
    # Add columns for compass direction and distance
    df['compassDirection'] = None
    df['distance'] = None
    df['distanceUnit'] = None
    
    #for i, row1 in fish_progress_bar(df.iterrows(), total=len(df), desc="Building groups"):
    for i, row1 in df.iterrows():
        if assigned_groups[i] != -1:  # Skip if this record has already been assigned a group
            continue
        current_group = [i]  # Start a new group with this record
        assigned_groups[i] = group_id  # Assign group ID to this record
        
        # Extract compass direction and distance for this record
        compass1 = extract_compass_direction(row1['locality'])
        distance1, unit1 = extract_distance(row1['locality'])
        
        # Save the extracted data to the DataFrame
        df.at[i, 'compassDirection'] = compass1
        df.at[i, 'distance'] = distance1
        df.at[i, 'distanceUnit'] = unit1
        
        for j, row2 in df.iterrows():
            if i >= j or assigned_groups[j] != -1:
                continue  # Skip the same record or already assigned records
            
            # Extract compass direction and distance for the second record
            compass2 = extract_compass_direction(row2['locality'])
            distance2, unit2 = extract_distance(row2['locality'])
            
            # Only compare if both records have matching distance units
            if unit1 == unit2:
                if compare_fields(row1['locality'], row2['locality'], method, similarity_threshold,
                                  compass1=compass1, compass2=compass2,
                                  distance1=(distance1, unit1), distance2=(distance2, unit2)):
                    current_group.append(j)
                    assigned_groups[j] = group_id  # Assign the same group ID to similar records
                    
                    # Save the extracted data to the DataFrame
                    df.at[j, 'compassDirection'] = compass2
                    df.at[j, 'distance'] = distance2
                    df.at[j, 'distanceUnit'] = unit2
        
        groups.append(current_group)  # Add the group to the list
        group_id += 1  # Increment the group ID for the next group
    
    return groups, assigned_groups

# Function to assign sub-groups based on similar eventDate, recordNumber, and habitat values
def assign_sub_groups(df, eventdate_tolerance=3, recordnumber_tolerance=5, habitat_similarity_threshold=80, handle_null_recordnumber='0', handle_null_eventdate='0'):
    sub_groups = [-1] * len(df)
    sub_group_id = 1
    
    # Convert recordNumber to numeric for comparison, setting non-convertible values to NaN
    df['recordNumber'] = pd.to_numeric(df['recordNumber'], errors='coerce')
    
    #for group_id in fish_progress_bar(df['Group_ID'].unique(), desc="Assigning sub-groups"):
    for group_id in df['Group_ID'].unique():
        group_df = df[df['Group_ID'] == group_id]
        for i, row1 in group_df.iterrows():
            if sub_groups[i] != -1:  # Skip if already assigned a sub-group
                continue
            sub_group = [i]
            sub_groups[i] = sub_group_id
            
            for j, row2 in group_df.iterrows():
                if i >= j or sub_groups[j] != -1:
                    continue
                
                # Safely parse eventDate (set to a default if invalid)
                try:
                    date1 = datetime.strptime(row1['eventDate'], '%Y-%m-%d') if pd.notna(row1['eventDate']) else None
                    date2 = datetime.strptime(row2['eventDate'], '%Y-%m-%d') if pd.notna(row2['eventDate']) else None
                except ValueError:
                    date1, date2 = None, None
                
                # Handle eventDate comparison based on the config setting
                if date1 is None or date2 is None:
                    if handle_null_eventdate == '0':
                        date_diff = 0  # Treat nulls as no difference
                    else:
                        date_diff = float('inf')  # Treat nulls as infinite difference
                else:
                    date_diff = abs((date1 - date2).days)

                # Handle recordNumber comparison based on the config setting
                if pd.isna(row1['recordNumber']) or pd.isna(row2['recordNumber']):
                    if handle_null_recordnumber == '0':
                        record_diff = 0  # Treat nulls as no difference
                    else:
                        record_diff = float('inf')  # Treat nulls as infinite difference
                else:
                    record_diff = abs(row1['recordNumber'] - row2['recordNumber'])
                
                # Handle habitat similarity
                habitat_similarity = fuzz.token_sort_ratio(row1['habitat'], row2['habitat']) if pd.notna(row1['habitat']) and pd.notna(row2['habitat']) else 0
                habitat_match = habitat_similarity >= habitat_similarity_threshold
                
                # Check if both date, record number differences are within tolerance, and habitat is similar
                if date_diff <= eventdate_tolerance and record_diff <= recordnumber_tolerance and habitat_match:
                    sub_group.append(j)
                    sub_groups[j] = sub_group_id
            
            sub_group_id += 1  # Increment sub-group ID for the next sub-group
    
    return sub_groups

# Function to load the export configuration file from the script's location
def load_export_config():
    script_dir = os.path.dirname(os.path.realpath(__file__))  # Get the location of the Python script
    config_filename = os.path.join(script_dir, 'export_config.txt')  # Hardcode the config filename
    config = {}
    fields = []
    
    if os.path.exists(config_filename):
        try:
            with open(config_filename, 'r') as file:
                for line in file:
                    line = line.strip()
                    # Skip empty lines and lines starting with '#'
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=')
                        config[key.strip()] = value.strip()
                    else:
                        fields.append(line.strip())
            return config, fields
        except Exception as e:
            print(f"Error loading configuration file: {e}")
            return None, None
    else:
        print(f"Configuration file not found at {config_filename}.")
        return None, None

# Function to filter groups based on allowed collection codes
def filter_by_collection_code(df, allowed_collections):
    allowed_collections = [coll.strip() for coll in allowed_collections.split(',')]
    filtered_df = df.groupby('Group_ID').filter(lambda group: any(group['collectionCode'].isin(allowed_collections)))
    return filtered_df

# Function to prompt user for folder selection and load all CSV files
def load_csv_files_from_folder(folder_path=None):
    if not folder_path:    
        Tk().withdraw()  # Close the root window
        folder_path = askdirectory()  # Ask user to select a folder

    if folder_path:
        csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        if csv_files:
            return [os.path.join(folder_path, f) for f in csv_files], folder_path
        else:
            print("No CSV files found in the selected folder.")
            return None, None
    else:
        print("No folder selected.")
        return None, None

# Function to check if all latitudes and longitudes in a group are identical
def has_identical_coords(group):
    """Check if all records in the group have identical latitude and longitude."""
    return (group['decimalLatitude'].nunique() == 1) and (group['decimalLongitude'].nunique() == 1)

# Function to count allowed collections in each group
def count_allowed_collections(df, allowed_collections):
    """Count the number of records in each group that have collectionCode in the allowed list."""
    allowed_collections = [coll.strip() for coll in allowed_collections.split(',')]
    # Create a new column that checks if the collectionCode is in the allowed_collections list
    df['is_allowed_collection'] = df['collectionCode'].apply(lambda x: x in allowed_collections)
    
    # Group by 'Group_ID' and count the allowed collectionCode matches
    group_counts = df.groupby('Group_ID')['is_allowed_collection'].sum().reset_index()
    group_counts.rename(columns={'is_allowed_collection': 'allowed_collection_count'}, inplace=True)
    
    return group_counts


# Function to count decimalLatitude and decimalLongitude values in each group
def count_coords(df):
    """Count the number of unique decimalLatitude and decimalLongitude values in each group."""
    coord_counts = df.groupby('Group_ID').agg(
        decimalLatitude_count=('decimalLatitude', 'nunique'),
        decimalLongitude_count=('decimalLongitude', 'nunique')
    ).reset_index()
    return coord_counts

# Modify the save_filtered_groups_to_csv function to include compassDirection, distance, and coordinate counts
def save_filtered_groups_to_csv(input_filename, df, group_assignments, sub_group_assignments, min_size, export_columns, allowed_collections):
    df['Group_ID'] = group_assignments  # Add the group ID to the DataFrame
    df['Sub_Group_ID'] = sub_group_assignments  # Add the sub-group ID to the DataFrame
    
    # Add compassDirection and distance to export_columns if not already included
    if 'compassDirection' not in export_columns:
        export_columns.append('compassDirection')
    if 'distance' not in export_columns:
        export_columns.append('distance')
    if 'distanceUnit' not in export_columns:
        export_columns.append('distanceUnit')
    if 'decimalLatitude_count' not in export_columns:
        export_columns.append('decimalLatitude_count')
    if 'decimalLongitude_count' not in export_columns:
        export_columns.append('decimalLongitude_count')
    
    # Filter to only include groups that have more than the specified number of records
    group_counts = df['Group_ID'].value_counts()
    large_groups = group_counts[group_counts > min_size].index
    
    # Exclude records with blank or null localities and identical decimalLatitude and decimalLongitude
    filtered_df = df[
        df['Group_ID'].isin(large_groups) & 
        df['locality'].notnull() & df['locality'].str.strip().ne('')
    ]
    
    # Filter out groups where all latitudes and longitudes are identical
    filtered_df = filtered_df.groupby('Group_ID').filter(lambda x: not has_identical_coords(x))
    
    # Filter by allowed collectionCode
    filtered_df = filter_by_collection_code(filtered_df, allowed_collections)
    
    if not filtered_df.empty:
        # Count the number of allowed collections in each group
        allowed_collection_counts = count_allowed_collections(filtered_df, allowed_collections)
        
        # Count the number of unique decimalLatitude and decimalLongitude values in each group
        coord_counts = count_coords(filtered_df)
        
        # Merge the counts back to the filtered DataFrame
        filtered_df = filtered_df.merge(allowed_collection_counts, on='Group_ID', how='left')
        filtered_df = filtered_df.merge(coord_counts, on='Group_ID', how='left')
        
        # Reorder columns based on the configuration
        #TODO - make an arg over-ride for this
        #if export_columns:
        #    filtered_df = filtered_df[export_columns + ['allowed_collection_count']]
        
        # Sort by allowed collection count, then by Group_ID, Sub_Group_ID, and eventDate
        if 'eventDate' in filtered_df.columns:
            filtered_df.sort_values(by=['allowed_collection_count', 'Group_ID', 'Sub_Group_ID', 'eventDate'], ascending=[False, True, True, True], inplace=True)
        else:
            filtered_df.sort_values(by=['allowed_collection_count', 'Group_ID', 'Sub_Group_ID'], ascending=[False, True, True], inplace=True)
        
        # Automatically create the output filename by appending "-groups.csv"
        output_filename = input_filename.replace('.csv', '-groups.csv')
        
        # Save the filtered DataFrame to the output file
        filtered_df.to_csv(output_filename, index=False)
        print(f"Group data saved to {output_filename}")

        # Save groups with 0 decimalLatitude_count and 0 decimalLongitude_count to an additional file
        coge_groups = filtered_df[(filtered_df['decimalLatitude_count'] == 0) & (filtered_df['decimalLongitude_count'] == 0)]
        if not coge_groups.empty:
            coge_filename = input_filename.replace('.csv', '-CoGe.csv')
            coge_groups.to_csv(coge_filename, index=False)
            print(f"Groups with 0 decimalLatitude_count and 0 decimalLongitude_count saved to {coge_filename}")

        # Save groups with 1 or more decimalLatitude_count or decimalLongitude_count to an additional file
        manual_groups = filtered_df[(filtered_df['decimalLatitude_count'] > 0) | (filtered_df['decimalLongitude_count'] > 0)]
        if not manual_groups.empty:
            manual_filename = input_filename.replace('.csv', '-manual.csv')
            manual_groups.to_csv(manual_filename, index=False)
            print(f"Groups with 1 or more decimalLatitude_count or decimalLongitude_count saved to {manual_filename}")
    else:
        print(f"No groups found with more than {min_size} records and non-blank localities.")

def process_csv(csv_file=None,
    config=None,
    export_columns=None,
    eventdate_tolerance=None, 
    recordnumber_tolerance=None, 
    habitat_similarity_threshold=None,
    similarity_threshold=None,
    min_size=None,
    allowed_collections=None):

    print(f"Processing file: {csv_file}")

    # Load the CSV file
    df = pd.read_csv(csv_file, encoding='ISO-8859-1', low_memory=False)

    # Find duplicate groups based on the user-defined similarity threshold
    groups, group_assignments = find_potential_duplicates(df, similarity_threshold, method='fuzzy')

    # Assign the 'Group_ID' column to the DataFrame before creating sub-groups
    df['Group_ID'] = group_assignments

    # Assign sub-groups based on eventDate, recordNumber, and habitat similarity
    sub_group_assignments = assign_sub_groups(df, eventdate_tolerance=eventdate_tolerance, recordnumber_tolerance=recordnumber_tolerance, habitat_similarity_threshold=habitat_similarity_threshold)

    # Save the filtered groups to the CSV, using the input filename to create the output filename
    save_filtered_groups_to_csv(csv_file, df, group_assignments, sub_group_assignments, min_size, export_columns, allowed_collections)

# Main function
def main():
    # Load the configuration and fields from export_config.txt
    config, export_columns = load_export_config()
    
    if config is None or export_columns is None:
        return
    
    # get command line args
    args = arg_setup()
    print(args['input'])
    input_path = args['input']
    if input_path: 
        csv_files, folder_path = load_csv_files_from_folder(folder_path=input_path)
    else:
        # Load CSV files from the selected folder
        csv_files, folder_path = load_csv_files_from_folder()
    #print(csv_files, folder_path)
    
    if csv_files:
        try:
            # Read tolerances and thresholds from the configuration file
            eventdate_tolerance = int(config.get('eventdate_tolerance', 3))
            recordnumber_tolerance = int(config.get('recordnumber_tolerance', 5))
            habitat_similarity_threshold = int(config.get('habitat_similarity_threshold', 80))
            similarity_threshold = int(config.get('similarity_threshold', 80))
            min_size = int(config.get('min_size', 0))
            allowed_collections = config.get('allowed_collections', '')  # Fetch allowed collections
            
            for csv_file in csv_files:
                process_csv(csv_file=csv_file,
                    config=config,
                    export_columns=export_columns,
                    eventdate_tolerance=eventdate_tolerance, 
                    recordnumber_tolerance=recordnumber_tolerance, 
                    habitat_similarity_threshold=habitat_similarity_threshold,
                    similarity_threshold=similarity_threshold,
                    min_size=min_size,
                    allowed_collections=allowed_collections)
                """
                print(f"Processing file: {csv_file}")
                
                # Load the CSV file
                df = pd.read_csv(csv_file, encoding='ISO-8859-1', low_memory=False)
                
                # Find duplicate groups based on the user-defined similarity threshold
                groups, group_assignments = find_potential_duplicates(df, similarity_threshold, method='fuzzy')
                
                # Assign the 'Group_ID' column to the DataFrame before creating sub-groups
                df['Group_ID'] = group_assignments
                
                # Assign sub-groups based on eventDate, recordNumber, and habitat similarity
                sub_group_assignments = assign_sub_groups(df, eventdate_tolerance=eventdate_tolerance, recordnumber_tolerance=recordnumber_tolerance, habitat_similarity_threshold=habitat_similarity_threshold)
                
                # Save the filtered groups to the CSV, using the input filename to create the output filename
                save_filtered_groups_to_csv(csv_file, df, group_assignments, sub_group_assignments, min_size, export_columns, allowed_collections)
                """
                
        except ValueError:
            print("Invalid input. Please check the configuration values in export_config.txt.")
    else:
        print("No valid CSV files to process.")

import threading
import os
import time
import queue

def process_multiple_csv_files(csv_files, num_threads=4):

    # Load the configuration and fields from export_config.txt
    config, export_columns = load_export_config()
    
    if config is None or export_columns is None:
        return
    
    # get command line args
    args = arg_setup()
    print(args['input'])
    input_path = args['input']
    if input_path: 
        csv_files, folder_path = load_csv_files_from_folder(folder_path=input_path)
    else:
        # Load CSV files from the selected folder
        csv_files, folder_path = load_csv_files_from_folder()
    #print(csv_files, folder_path)
    

    # Read tolerances and thresholds from the configuration file
    eventdate_tolerance = int(config.get('eventdate_tolerance', 3))
    recordnumber_tolerance = int(config.get('recordnumber_tolerance', 5))
    habitat_similarity_threshold = int(config.get('habitat_similarity_threshold', 80))
    similarity_threshold = int(config.get('similarity_threshold', 80))
    min_size = int(config.get('min_size', 0))
    allowed_collections = config.get('allowed_collections', '')  # Fetch allowed collections



    """
    Process multiple CSV files in parallel using threading.
    
    Args:
        csv_files (list): List of CSV file paths to process
        num_threads (int): Number of threads to use
    """
    # Create a queue to hold the files
    file_queue = queue.Queue()
    
    # Put all files in the queue
    for file in csv_files:
        file_queue.put(file)
    
    # Define the worker function
    def worker():
        while not file_queue.empty():
            try:
                # Get a file from the queue
                file = file_queue.get(block=False)
                print(f"Processing {file} in thread {threading.current_thread().name}")
                
                # Process the file using your existing function
                #process_csv(file)
                process_csv(csv_file=file,
                    config=config,
                    export_columns=export_columns,
                    eventdate_tolerance=eventdate_tolerance, 
                    recordnumber_tolerance=recordnumber_tolerance, 
                    habitat_similarity_threshold=habitat_similarity_threshold,
                    similarity_threshold=similarity_threshold,
                    min_size=min_size,
                    allowed_collections=allowed_collections)
                
                # Mark the task as done
                file_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error processing {file}: {e}")
                file_queue.task_done()
    
    # Create and start the threads
    threads = []
    for i in range(min(num_threads, len(csv_files))):
        thread = threading.Thread(target=worker, name=f"Thread-{i+1}")
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("All files have been processed!")

def main_multi():   
    # Measure the execution time
    start_time = time.time()

    # Load the configuration and fields from export_config.txt
    config, export_columns = load_export_config()
    
    if config is None or export_columns is None:
        return
    
    # get command line args
    args = arg_setup()
    print(args['input'])
    input_path = args['input']
    if input_path: 
        csv_files, folder_path = load_csv_files_from_folder(folder_path=input_path)
    else:
        # Load CSV files from the selected folder
        csv_files, folder_path = load_csv_files_from_folder()
    #print(csv_files, folder_path)
    

    available_cores = mp.cpu_count()
    num_threads = max(1, available_cores - 1)
    process_multiple_csv_files(csv_files, num_threads=num_threads)
    elapsed_time = time.time() - start_time
    print(f"Execution completed in {elapsed_time:.2f} seconds")

def main_multi_OLD():
    # Set up command line argument parsing if needed
    # args = arg_setup()
    
    start_time = time.time()
    
    # Set up multiprocessing
    num_cores = mp.cpu_count()
    # Use one less than available to keep system responsive
    num_processes = max(1, num_cores - 1)
    pool = mp.Pool(processes=num_processes)
    
    # Create results directory
    #results_dir = Path('BELS_Grouper_results')
    #results_dir.mkdir(parents=True, exist_ok=True)
    
    print("Starting Grouper with multiprocessing")
    
    # Load the input file
    csv_file = '/media/jbest/data3/BRIT_git/TORCH_georeferencing/data/Texas/panhandle/panhandle_test/occurrences_BELS_metrics.tab'
    print(f"Loading data from {csv_file}")
    df = pd.read_csv(csv_file, low_memory=False, sep='\t')
    
    # Get unique counties
    counties = df['county'].unique()
    print(f'Found {len(counties)} unique counties')
    
    # Create a list of county DataFrames with a progress bar
    print("Preparing data for parallel processing...")
    county_dfs = []
    for county in tqdm(counties, desc="Splitting data by county"):
        county_dfs.append(df[df['county'] == county].copy())
    
    try:
        # Process counties in parallel with progress bar
        print(f"Processing {len(county_dfs)} counties using {num_cores} CPU cores")
        processed_dfs = list(tqdm(pool.imap(process_county, county_dfs), 
                               total=len(county_dfs), 
                               desc="Processing counties"))
        
        # Save results for each county with progress bar
        print("Saving results...")
        for df_county in tqdm(processed_dfs, desc="Saving results"):
            save_county_results(df_county, results_dir)
            
    finally:
        # Clean up
        pool.close()
        pool.join()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"All counties processed successfully in {elapsed_time:.2f} seconds!")

if __name__ == "__main__":
    # Ensure multiprocessing works correctly on all platforms
    #mp.freeze_support()
    #main()
    main_multi()
