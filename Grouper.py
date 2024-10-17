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
        time.sleep(0.1)  # Small delay to simulate work (remove in actual use)
    
    sys.stdout.write('\n')  # New line when complete

# Function to calculate similarity between two text fields
def compare_fields(field1, field2, method='fuzzy', threshold=80):
    if method == 'fuzzy':
        return fuzz.token_sort_ratio(field1, field2) >= threshold
    elif method == 'cosine':
        vectorizer = TfidfVectorizer().fit_transform([field1, field2])
        cosine_sim = cosine_similarity(vectorizer[0:1], vectorizer[1:2])
        return cosine_sim[0][0] >= threshold / 100
    else:
        raise ValueError("Method should be 'fuzzy' or 'cosine'")

# Function to find potential duplicate records and group them into groups
def find_potential_duplicates(df, similarity_threshold, method='fuzzy'):
    groups = []
    group_id = 1
    assigned_groups = [-1] * len(df)  # Initialize all records as ungrouped
    
    for i, row1 in fish_progress_bar(df.iterrows(), total=len(df), desc="Building groups"):
        if assigned_groups[i] != -1:  # Skip if this record has already been assigned a group
            continue
        current_group = [i]  # Start a new group with this record
        assigned_groups[i] = group_id  # Assign group ID to this record
        
        for j, row2 in df.iterrows():
            if i >= j or assigned_groups[j] != -1:
                continue  # Skip the same record or already assigned records
            if compare_fields(row1['recordedBy'], row2['recordedBy'], method, similarity_threshold) and \
               compare_fields(row1['locality'], row2['locality'], method, similarity_threshold):
                current_group.append(j)
                assigned_groups[j] = group_id  # Assign the same group ID to similar records
        
        groups.append(current_group)  # Add the group to the list
        group_id += 1  # Increment the group ID for the next group
    
    return groups, assigned_groups

# Function to assign sub-groups based on similar eventDate and recordNumber values
def assign_sub_groups(df, eventdate_tolerance=3, recordnumber_tolerance=5, handle_null_recordnumber='0', handle_null_eventdate='0'):
    sub_groups = [-1] * len(df)
    sub_group_id = 1
    
    # Convert recordNumber to numeric for comparison, setting non-convertible values to NaN
    df['recordNumber'] = pd.to_numeric(df['recordNumber'], errors='coerce')
    
    for group_id in fish_progress_bar(df['Group_ID'].unique(), desc="Assigning sub-groups"):
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
                
                # Check if both date and record number differences are within tolerance
                if date_diff <= eventdate_tolerance and record_diff <= recordnumber_tolerance:
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

# Function to filter groups based on allowed institutions
def filter_by_institution(df, allowed_institutions):
    allowed_institutions = [inst.strip() for inst in allowed_institutions.split(',')]
    filtered_df = df.groupby('Group_ID').filter(lambda group: any(group['institutionCode'].isin(allowed_institutions)))
    return filtered_df

# Function to prompt user for folder selection and load all CSV files
def load_csv_files_from_folder():
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

# Function to count allowed institutions in each group
def count_allowed_institutions(df, allowed_institutions):
    """Count the number of records in each group that have institutionCode in the allowed list."""
    allowed_institutions = [inst.strip() for inst in allowed_institutions.split(',')]
    # Create a new column that checks if the institutionCode is in the allowed_institutions list
    df['is_allowed_institution'] = df['institutionCode'].apply(lambda x: x in allowed_institutions)
    
    # Group by 'Group_ID' and count the allowed institutionCode matches
    group_counts = df.groupby('Group_ID')['is_allowed_institution'].sum().reset_index()
    group_counts.rename(columns={'is_allowed_institution': 'allowed_institution_count'}, inplace=True)
    
    return group_counts

# Function to save filtered groups to a new CSV file with sorting by allowed institution counts
def save_filtered_groups_to_csv(input_filename, df, group_assignments, sub_group_assignments, min_size, export_columns, allowed_institutions):
    df['Group_ID'] = group_assignments  # Add the group ID to the DataFrame
    df['Sub_Group_ID'] = sub_group_assignments  # Add the sub-group ID to the DataFrame
    
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
    
    # Filter by allowed institutionCode
    filtered_df = filter_by_institution(filtered_df, allowed_institutions)
    
    if not filtered_df.empty:
        # Count the number of allowed institutions in each group
        allowed_institution_counts = count_allowed_institutions(filtered_df, allowed_institutions)
        
        # Merge the counts back to the filtered DataFrame
        filtered_df = filtered_df.merge(allowed_institution_counts, on='Group_ID', how='left')
        
        # Reorder columns based on the configuration
        if export_columns:
            filtered_df = filtered_df[export_columns + ['allowed_institution_count']]
        
        # Sort by allowed institution count, then by Group_ID, Sub_Group_ID, and eventDate
        if 'eventDate' in filtered_df.columns:
            filtered_df.sort_values(by=['allowed_institution_count', 'Group_ID', 'Sub_Group_ID', 'eventDate'], ascending=[False, True, True, True], inplace=True)
        else:
            filtered_df.sort_values(by=['allowed_institution_count', 'Group_ID', 'Sub_Group_ID'], ascending=[False, True, True], inplace=True)
        
        # Automatically create the output filename by appending "-groups.csv"
        output_filename = input_filename.replace('.csv', '-groups.csv')
        
        # Save the filtered DataFrame to the output file
        filtered_df.to_csv(output_filename, index=False)
        print(f"Group data saved to {output_filename}")
    else:
        print(f"No groups found with more than {min_size} records and non-blank localities.")

# Main function
def main():
    # Load the configuration and fields from export_config.txt
    config, export_columns = load_export_config()
    
    if config is None or export_columns is None:
        return
    
    # Load CSV files from the selected folder
    csv_files, folder_path = load_csv_files_from_folder()
    
    if csv_files:
        try:
            # Read tolerances and thresholds from the configuration file
            eventdate_tolerance = int(config.get('eventdate_tolerance', 3))
            recordnumber_tolerance = int(config.get('recordnumber_tolerance', 5))
            similarity_threshold = int(config.get('similarity_threshold', 80))
            min_size = int(config.get('min_size', 2))
            allowed_institutions = config.get('allowed_institutions', '')  # Fetch allowed institutions
            
            for csv_file in csv_files:
                print(f"Processing file: {csv_file}")
                
                # Load the CSV file
                df = pd.read_csv(csv_file, encoding='ISO-8859-1', low_memory=False)
                
                # Find duplicate groups based on the user-defined similarity threshold
                groups, group_assignments = find_potential_duplicates(df, similarity_threshold, method='fuzzy')
                
                # Assign the 'Group_ID' column to the DataFrame before creating sub-groups
                df['Group_ID'] = group_assignments
                
                # Assign sub-groups based on eventDate and recordNumber
                sub_group_assignments = assign_sub_groups(df, eventdate_tolerance=eventdate_tolerance, recordnumber_tolerance=recordnumber_tolerance)
                
                # Save the filtered groups to the CSV, using the input filename to create the output filename
                save_filtered_groups_to_csv(csv_file, df, group_assignments, sub_group_assignments, min_size, export_columns, allowed_institutions)
                
        except ValueError:
            print("Invalid input. Please check the configuration values in export_config.txt.")
    else:
        print("No valid CSV files to process.")

if __name__ == "__main__":
    main()
