# DinoMap-Geocoding-Tools

A collection of Python scripts for processing market data and error correction files, geocoding addresses, and generating shapefiles for the Dino Mapa project.

## Table of Contents

- [Market Data Extraction and Geocoding Script](#market-data-extraction-and-geocoding-script)
  - [Overview](#overview)
  - [Processing Flow](#processing-flow)
  - [Dependencies](#dependencies)
  - [How to Run](#how-to-run)
- [Error SHP Generator Script](#error-shp-generator-script)
  - [Overview](#overview-1)
  - [Processing Flow](#processing-flow-1)
  - [Dependencies](#dependencies-1)
  - [How to Run](#how-to-run-1)
- [Common Considerations](#common-considerations)

---

## Market Data Extraction and Geocoding Script

### Overview

This script processes market data that has been manually extracted from the website and saved into a local HTML file (`site.html`). It performs the following tasks:

1. **HTML Loading and Extraction:**  
   - Reads the local `site.html` file (with proper handling of UTF-8 and fallback encoding).
   - Uses BeautifulSoup to extract a specific `<div>` element with the ID `marketList` and parses its content.

2. **Data Cleaning and File Writing:**  
   - The extracted raw data is saved to an output file with a dynamically generated filename (based on the current date and time).
   - The data is cleaned using regular expressions to remove unwanted abbreviations, periods, and other patterns.
   - Cleaned data is saved to a separate file.

3. **Parsing and Geocoding:**  
   - Parses the cleaned data to extract attributes such as market name, street, postal code, and city.
   - Generates four candidate address variants for geocoding:
     - **Variant 1:** `Dino {street_name} {house_number} {postal_code} {city} Polska`
     - **Variant 2:** `{street_name} {house_number} {postal_code} {city} Polska`
     - **Variant 3:** `{city} {postal_code} {street_name} {house_number} Polska`
     - **Variant 4:** `{postal_code} {city} {street_name} {house_number} Polska`
   - The script iterates through these candidates, printing messages for each attempt. Upon a successful geocode, the candidate variant number (1–4) is stored as an attribute (`type`).

4. **SHP File Generation:**  
   - If geocoding is successful, the script transforms coordinates from EPSG:4326 to EPSG:2180.
   - A GeoDataFrame is constructed (using geopandas) with attributes including:
     - `nazwa` (name)
     - `ulica` (street)
     - `numer_dom` (house number)
     - `kod_pocz` (postal code)
     - `miejsco` (city)
     - `type` (indicating the candidate variant used)
   - The GeoDataFrame is saved as a shapefile with a filename that includes the current date.

### Processing Flow

1. **Load HTML:**  
   - The script reads the `site.html` file, using UTF-8 encoding (with fallback if necessary).

2. **Extract Data:**  
   - Data is extracted from the `<div id="marketList">` element by finding all child elements with a specific class (e.g., `cursor-pointer`).

3. **Clean and Save Data:**  
   - The raw data is written to a timestamped output file.
   - The data is then cleaned and saved to another file, both with dynamically generated names.

4. **Parse Records:**  
   - Each cleaned line is split by a semicolon (`;`) to extract individual attributes.

5. **Generate Candidate Addresses & Geocode:**  
   - For each record, four candidate addresses are generated.
   - The script attempts to geocode these addresses sequentially, printing messages like:  
     `[<row_index> / <total>] Próbuję wariant <i>: <candidate>`  
     `[<row_index> / <total>] Znaleziono: <full_address> -> <latitude>, <longitude>`
   - The successful candidate’s variant number (1–4) is stored as the `type` attribute.

6. **Create and Save SHP:**  
   - Successfully geocoded points are transformed to EPSG:2180.
   - A shapefile is created containing all attributes and geometries.

### Dependencies

- Python packages:
  - `requests`
  - `beautifulsoup4`
  - `geopy`
  - `pyproj`
  - `shapely`
  - `geopandas`
  - `pandas`

Install them with:
```
pip install requests beautifulsoup4 geopy pyproj shapely geopandas pandas
```

### How to Run

1. Place your HTML file (`site.html`) in the same directory as the script.
2. Run the script:
```
python <market_data_script>.py
```


3. The output files (raw data, cleaned data, error log, and the shapefile) will be generated with dynamic timestamps.

---

## Error SHP Generator Script

### Overview

This script generates a shapefile from an error file containing manually verified corrections. The error file contains two types of rows:

1. **Type 1 – Address Correction Row:**  
   - Format:  
     `old_address//new_address (manually corrected)//error_reason`
   - The script extracts attribute data from the old address.
   - It generates four candidate address variants for geocoding the new address (same as in the market data script).
   - The successful candidate’s index (1–4) is recorded as the `type` attribute.

2. **Type 2 – Direct Coordinates Row:**  
   - Format:  
     `old_address//latitude, longitude//error_reason`
   - The script directly uses the provided coordinates (after transforming them from EPSG:4326 to EPSG:2180) and sets the `type` attribute to **4**.

For each record, additional attributes (such as the error reason) are stored. If a record fails to produce a valid geocode (for Type 1), it is logged in a separate error file with a timestamped name.

### Processing Flow

1. **Load Error File:**  
   - The script reads an error file located at:  
     `C:\Users\damia\Desktop\Projekty\done - Dino Mapa\Incorrect_checked.txt`
   - The file is assumed to be encoded in UTF-8.

2. **Parse Lines:**  
   - Each line is split using the delimiter `//`.
   - The script determines if the second part represents a coordinate pair (Type 2) or a new corrected address (Type 1).

3. **Extract Attributes:**  
   - The old address (first part) is parsed to extract attributes like name, street, house number, postal code, and city.

4. **Geocoding (Type 1):**  
   - For rows with a new address, four candidate addresses are generated and geocoded sequentially.
   - Log messages are printed for each attempt in the format:  
     `[<row_index> / <total>] Próbuję wariant <i>: <candidate>`  
     `[<row_index> / <total>] Znaleziono: <full_address> -> <latitude>, <longitude>`
   - The candidate variant number (1–4) is stored as the `type` attribute.

5. **Direct Coordinates (Type 2):**  
   - For rows containing coordinates, these values are transformed to EPSG:2180.
   - The attribute `type` is set to **4**.

6. **SHP File Creation:**  
   - A GeoDataFrame is built using the processed records, including all attributes and geometries.
   - The shapefile is saved with a filename that includes the current date.

7. **Error Logging:**  
   - Any rows that fail to be geocoded are saved to a separate error file with a dynamic timestamp.

### Dependencies

- Python packages:
  - `geopy`
  - `pyproj`
  - `shapely`
  - `geopandas`
  - `pandas`
  - `beautifulsoup4` (if needed for address parsing)

Install them with:
```
pip install geopy pyproj shapely geopandas pandas beautifulsoup4
```

### How to Run

1. Ensure the error file is located at:  
   `C:\Users\damia\Desktop\Projekty\done - Dino Mapa\Incorrect_checked.txt`
2. Run the script:
```
python <error_shp_generator_script>.py
```


3. The script will generate a shapefile (e.g., `errors_<date>.shp`) and, if applicable, an additional error log file (`errors_not_geocoded_<timestamp>.txt`).

---

## Common Considerations

- **Coordinate Transformation:**  
  Both scripts use `pyproj` to transform coordinates from EPSG:4326 (WGS84) to EPSG:2180.

- **Logging:**  
  Unified log messages are printed to the console to display processing progress, candidate geocoding attempts, and success messages.

- **Dynamic Filenames:**  
  Output filenames are dynamically generated using the current date and time to avoid overwriting previous results.

- **Encoding:**  
  All file operations are performed using UTF-8 to ensure correct handling of non-ASCII characters, especially Polish letters.

