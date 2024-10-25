import os
import pandas as pd
import re
import sys
import time

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

# Function to find potential duplicates based on stateProvince and county fields
def find_potential_duplicates(df):
    groups = []
    group_id = 1
    assigned_groups = [-1] * len(df)  # Initialize all records as ungrouped
    
    # Add columns for compass direction and distance
    df['compassDirection'] = None
    df['distance'] = None
    df['distanceUnit'] = None
    
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
        
        sys.stdout.write(f"\rProcessing state: {row1['stateProvince']}, county: {row1['county']}")
        sys.stdout.flush()
        
        for j, row2 in df.iterrows():
            if i >= j or assigned_groups[j] != -1:
                continue  # Skip the same record or already assigned records
            
            # Only consider records with the same stateProvince and county
            if row1['stateProvince'] == row2['stateProvince'] and row1['county'] == row2['county']:
                current_group.append(j)
                assigned_groups[j] = group_id  # Assign the same group ID to similar records
                
                # Extract compass direction and distance for the second record
                compass2 = extract_compass_direction(row2['locality'])
                distance2, unit2 = extract_distance(row2['locality'])
                
                # Save the extracted data to the DataFrame
                df.at[j, 'compassDirection'] = compass2
                df.at[j, 'distance'] = distance2
                df.at[j, 'distanceUnit'] = unit2
        
        groups.append(current_group)  # Add the group to the list
        group_id += 1  # Increment the group ID for the next group
    
    sys.stdout.write('\n')  # New line when complete
    return groups, assigned_groups

# Function to save the filtered groups to CSV
def save_filtered_groups_to_csv(input_filename, df, group_assignments):
    df['Group_ID'] = group_assignments  # Add the group ID to the DataFrame
    
    # Automatically create the output filename by appending "-groups.csv"
    output_filename = input_filename.replace('.csv', '-groups.csv')
    
    # Save the filtered DataFrame to the output file
    df.to_csv(output_filename, index=False)
    print(f"Group data saved to {output_filename}")

# Main function
def main():
    # Specify the input CSV file
    input_filename = input("Please enter the path to the input CSV file: ")  # Replace with the actual file path
    
    try:
        # Load the CSV file
        df = pd.read_csv(input_filename, encoding='ISO-8859-1', low_memory=False)
        
        # Find duplicate groups based on the same stateProvince and county
        groups, group_assignments = find_potential_duplicates(df)
        
        # Save the filtered groups to the CSV
        save_filtered_groups_to_csv(input_filename, df, group_assignments)
        
    except ValueError:
        print("Invalid input. Please check the input CSV file.")

if __name__ == "__main__":
    main()
