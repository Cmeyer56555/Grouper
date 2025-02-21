import os
import pandas as pd
from tkinter import Tk, filedialog

def combine_csvs():
    # Hide the root Tkinter window
    Tk().withdraw()

    # Prompt user for folder location
    folder_path = filedialog.askdirectory(title="Select Folder with CSV Files")
    if not folder_path:
        print("No folder selected. Exiting.")
        return

    # Initialize a list to hold dataframes
    csv_list = []
    headers = None

    # Loop through files in the selected folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            file_path = os.path.join(folder_path, file_name)

            # Read the CSV
            df = pd.read_csv(file_path)

            # Use headers from the first CSV
            if headers is None:
                headers = df.columns
            else:
                df.columns = headers  # Ensure subsequent CSVs use the same headers

            csv_list.append(df)

    if not csv_list:
        print("No CSV files found in the folder. Exiting.")
        return

    # Concatenate all dataframes
    combined_df = pd.concat(csv_list, ignore_index=True)

    # Save combined CSV
    output_path = os.path.join(folder_path, "combined_output.csv")
    combined_df.to_csv(output_path, index=False)

    print(f"Combined CSV saved as {output_path}")

if __name__ == "__main__":
    combine_csvs()
