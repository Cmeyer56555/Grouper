 ><(((º>   Grouper.py  ><(((º>

***Executive Summary***
This python script goes through a folder of exported herbarium CSV files and finds groups of similar locations, collector names, collector #s, and collection dates. These groups make it easier to leverage both new and existing georeferencing.

***Groups and Subgroups***
Grouper finds "groups" and "subgroups." The idea here is to give two levels of confidence that the records are in the same place.
-Group: similar locality AND similar recordedby (collector) values
-Subgroup: locality, collector, AND close eventDate (collection date) and recordNumber (coll#)

***Filtering***
The script doesn't save ALL groups to the export CSV. The script filters out:
-groups where all records have identical latitude and longitude (they're already done)
-groups with blank localities (nothing to work with)
-groups that don't have at least ONE record on the "allowed_institutions" list. (we only want records we can potentially change)
-groups smaller than the min_size set in export_config.txt (we want to focus on more impactful groups)

***Getting Started***
This script is intended to work with "occurences.csv" files downloaded from TORCH. You'll want to TORCH's default Search tool (not occurence managment). Grouper is designed to help propogate coordinates from other institutions, so can select which institutions you want in this step. It will run on large 40k+ datasets, but it will be slow. Grouper can queue up a whole folder of CSVs at a time, so I recommend subdividing by counties. (For a quick way to do this, check out StateChopper.py).

Once you've got your input CSVs, name them something useful and put them all in a single folder. 

***Configuration Setup***
The script uses a configuration file (export_config.txt). is file must be located in the same directory as the Python script. 

eventdate_tolerance: Maximum number of days allowed between any two records' eventDate to be considered for the same sub-group.

recordnumber_tolerance: Maximum allowed difference between any two records' recordNumber to be considered for the same sub-group. Null records are treated as a difference of 0, so they do not disqualify a record from a subgroup.

similarity_threshold: The minimum fuzzy matching or cosine similarity score for records to be considered duplicates (range: 0-100).

min_size: Minimum number of records required for a group to be processed.

allowed_institutions: Comma-separated list of institutionCodes. Groups have to have at least one record from an instituion on this list. This list also controls how groups are ordered in the export CSV; groups with more records at these institution codes come first.

handle_null_recordnumber: This controls how null recordNumber values are handled. 0 means a null value will always pass the subgroup check, "inf" means a null will always fail the subgroup check.

handle_null_eventdate: This controls how null eventDate values are handled. 0 means a null value will always pass the subgroup check, "inf" means a null will always fail the subgroup check.


Export CSV fields: this is the list of fields that will populate the export CSV. The field at the top of the list is the leftmost column.

Here's a sample export_config.txt:

eventdate_tolerance=3
recordnumber_tolerance=10
similarity_threshold=95
min_size=3
allowed_institutions=BRIT,ACU,BCNWR,HSU,TAC,TCSW,NLU,VDB
handle_null_recordnumber=0  # Treat null recordNumber "0" for ignore, "inf" for always fail
handle_null_eventdate=inf   # Treat null eventDate "0" for ignore, "inf" for always fail

# Fields for export CSV (one field per line)
Group_ID
Sub_Group_ID
id
institutionCode
catalogNumber
recordedBy
associatedCollectors
recordNumber
eventDate
habitat
country
stateProvince
county
municipality
locality
locationRemarks
decimalLatitude
decimalLongitude
geodeticDatum
coordinateUncertaintyInMeters
verbatimCoordinates
georeferencedBy
georeferenceProtocol
georeferenceSources
georeferenceVerificationStatus
georeferenceRemarks

***Running the Script**
Open the command line in the folder containing Grouper.py
Type in "python Grouper.py"
Select the folder containing the raw occurences.csv files.
Be patient, watch the fish swim.

Processing file: D:/Grouper/oklahoma_counties\OK_Cimarron.csv
Building groups: [                             ><(((º>           ] 74%

***What's next***
The output is a CSV with a -groups.csv suffix. It'll contain the fields you specified, along with columns for group number, subgroup number, and allowed_institution_count. Both group and subgroup numbers are just unique serial numbers. Allowed_institution_count is a count of the number of entries that contain an institutionCode specified in the config file. It's intended to prioritize high-impact groups that you can actually change, rather than large groups that only have one entry from your institution.