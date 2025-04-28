import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog

def get_folder():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select Folder Containing CSV Files")
    return folder_selected

def combine_csvs(folder_path, suffix):
    all_files = [f for f in os.listdir(folder_path) if f.endswith(suffix)]
    
    if not all_files:
        print(f"No files found with suffix '{suffix}' in {folder_path}")
        return
    
    combined_df = pd.concat([pd.read_csv(os.path.join(folder_path, f)) for f in all_files], ignore_index=True)
    output_file = os.path.join(folder_path, f"combined_{suffix}.csv")
    combined_df.to_csv(output_file, index=False)
    
    print(f"Combined CSV saved as: {output_file}")

def main():
    folder = get_folder()
    if not folder:
        print("No folder selected. Exiting...")
        return
    
    suffix = input("Enter the file suffix (e.g., '-groups.csv'): ").strip()
    combine_csvs(folder, suffix)

if __name__ == "__main__":
    main()
