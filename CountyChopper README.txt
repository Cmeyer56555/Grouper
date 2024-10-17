
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

🐄
