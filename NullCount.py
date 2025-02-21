import pandas as pd

def count_null_collectioncode(csv_file):
    try:
        # Try reading the CSV file with different encoding options
        df = pd.read_csv(csv_file, dtype=str, encoding='latin1')  # Use 'latin1' to handle unusual characters

        # Identify records with empty or null collectionCode
        missing_collectioncode = df['collectionCode'].isna() | (df['collectionCode'] == '')

        # Count records with missing collectionCode
        null_count = missing_collectioncode.sum()

        # Count how many of these have a valid institutionCode
        substitute_counts = df.loc[missing_collectioncode, 'institutionCode'].value_counts()

        print(f"Number of records with null or empty 'collectionCode': {null_count}")
        print("Substituting with 'institutionCode' counts:")
        print(substitute_counts)
        
        return null_count, substitute_counts.to_dict()
    except UnicodeDecodeError:
        print("Encoding error: Try opening the file in Excel and saving it as a UTF-8 CSV.")

if __name__ == "__main__":
    file_path = input("Enter the CSV file path: ")
    count_null_collectioncode(file_path)
