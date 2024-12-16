import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import itertools
import os

# Parameters
group_similarity_threshold = 80  # Threshold for fuzzy matching similarity

# Prompt user for the input CSV file location
input_csv = input("Please enter the path to the CSV file: ")
output_csv = os.path.splitext(input_csv)[0] + '-grouped.csv'

# Load CSV file
df = pd.read_csv(input_csv)

# Ensure required columns are present
if 'locality' not in df.columns or 'recordedBy' not in df.columns:
    raise ValueError("The CSV file must contain 'locality' and 'recordedBy' columns.")

# Prepare a list to store group assignments
group_assignments = [-1] * len(df)
current_group = 0

# Iterate over all pairs of entries to assign groups
for i, j in itertools.combinations(range(len(df)), 2):
    if group_assignments[i] == -1 and group_assignments[j] == -1:
        # Compare both "locality" and "recordedBy" fields
        locality_similarity = fuzz.token_set_ratio(df.at[i, 'locality'], df.at[j, 'locality'])
        recorded_by_similarity = fuzz.token_set_ratio(df.at[i, 'recordedBy'], df.at[j, 'recordedBy'])
        
        # Assign to the same group if similarity exceeds threshold
        if locality_similarity >= group_similarity_threshold and recorded_by_similarity >= group_similarity_threshold:
            group_assignments[i] = group_assignments[j] = current_group
            current_group += 1
    elif group_assignments[i] != -1 and group_assignments[j] == -1:
        # Assign j to the same group as i if they match
        locality_similarity = fuzz.token_set_ratio(df.at[i, 'locality'], df.at[j, 'locality'])
        recorded_by_similarity = fuzz.token_set_ratio(df.at[i, 'recordedBy'], df.at[j, 'recordedBy'])
        
        if locality_similarity >= group_similarity_threshold and recorded_by_similarity >= group_similarity_threshold:
            group_assignments[j] = group_assignments[i]
    elif group_assignments[i] == -1 and group_assignments[j] != -1:
        # Assign i to the same group as j if they match
        locality_similarity = fuzz.token_set_ratio(df.at[i, 'locality'], df.at[j, 'locality'])
        recorded_by_similarity = fuzz.token_set_ratio(df.at[i, 'recordedBy'], df.at[j, 'recordedBy'])
        
        if locality_similarity >= group_similarity_threshold and recorded_by_similarity >= group_similarity_threshold:
            group_assignments[i] = group_assignments[j]

# Assign ungrouped items a new group
for idx, group in enumerate(group_assignments):
    if group == -1:
        group_assignments[idx] = current_group
        current_group += 1

# Add group assignments to DataFrame and save to CSV
df['group'] = group_assignments
df.to_csv(output_csv, index=False)

print(f"Grouped entries have been saved to '{output_csv}'")
