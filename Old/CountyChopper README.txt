
CountyChopper.py

 ***Overview***
This script chops up a large state-sized ocurrences.csv into smaller county-sized csv files, and is intended for use with Grouper.  Downloading one large file is easier than downloading and managing dozens of smaller county files. This method also catches variants that  (Atoka, Atoka Co., Atoka County) that a strict TORCH search might miss.

 ***county_list.txt***
 This external file defines which counties will be included in the output. 

Example:

Adair
Alfalfa
Atoka
Beaver
Beckham
Blaine
Bryan
Caddo
Canadian


After selecting the CSV file:
The script reads the CSV using pd.read_csv().
The essential columns stateProvince, county, institutionCode, and locality must exist in the CSV for the script to work. If these columns are missing, the script will raise an error.

2. Normalization of County Names
The county names are normalized using the normalize_county_name() function, which converts them to lowercase and removes suffixes like "county" or "co." This ensures consistency for later filtering.

3. Whitelist/Blacklist Filtering for institutionCode
The institutionCode is converted to a string for consistency.
Whitelist Filtering: Records with an institutionCode in the whitelist are separated out. These records bypass all other filters and are always included in the final output.

Blacklist Filtering: Records with an institutionCode in the blacklist are excluded completely. These records are removed from the dataset before further filtering.

4. Filtering for locality
The script applies a filter to include only records with a non-null locality field, unless the institutionCode is in the whitelist.
Null Locality Handling: If a record has a null locality and the institutionCode is on the whitelist, the record is still included.

5. Filtering for coordinateUncertaintyInMeters
The script filters out any records where coordinateUncertaintyInMeters is null or greater than the threshold (set in the configuration file). This ensures that only records with an acceptable level of coordinate uncertainty are included.

6. Filtering for georeferencedBy and georeferenceRemarks (Toggleable)
georeferencedBy Filter (if enabled): The script excludes records where the georeferencedBy field is null, ensuring that only records with a valid georeferencer are included.

georeferenceRemarks Filter (if enabled): The script excludes records where the georeferenceRemarks field is null.

7. Blacklist Filtering for georeferenceSources
The script filters out any records where the georeferenceSources field matches any value from the georeferenceSourcesBlacklist.

8. Blacklist Filtering for georeferenceVerificationStatus
The script filters out records where the georeferenceVerificationStatus matches any value in the georeferenceVerificationStatusBlacklist.

9. Substring Filtering for georeferenceRemarks
For the georeferenceRemarks field, the script performs a substring search using .str.contains(). This method checks if any of the blacklist strings appear anywhere within the georeferenceRemarks field, even as part of a larger string.
If any blacklist string is found within the georeferenceRemarks field, that record is excluded.

10. Combining Whitelisted and Filtered Data
After all filters are applied to the dataset, the script combines the records that were separated earlier (i.e., those from the whitelist that bypassed all other filters) with the records that passed all the filters.

11. Final State and County Filtering
The final dataset is filtered to include only records where:
The stateProvince field matches the state specified in the configuration file.
The normalized_county field matches one of the counties listed in the configuration file.

12. Exporting the Data
The filtered data is then grouped by county, and a separate CSV file is created for each county, named as <state>_<county>.csv.
The output files are saved in a folder named after the selected state.
Summary of Filtering Flow:
Whitelist: Records in the whitelist are saved immediately, bypassing all other filters.
Blacklist: Records in the blacklist are excluded entirely.
Locality Check: Exclude records with null locality unless in the whitelist.
coordinateUncertaintyInMeters: Exclude records with too much uncertainty.
georeferencedBy and georeferenceRemarks: Optionally exclude records with null values.
georeferenceSourcesBlacklist: Exclude records matching blacklist sources.
georeferenceVerificationStatusBlacklist: Exclude records matching blacklist statuses.
georeferenceRemarksBlacklist: Exclude records where georeferenceRemarks contains any blacklist term.
Final Filter: Keep records matching the selected state and counties.