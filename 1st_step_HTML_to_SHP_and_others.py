import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from pyproj import Transformer
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd

# Funkcja wczytująca zawartość pliku HTML z obsługą kodowania UTF-8
def load_html(file_path):
    with open(file_path, "rb") as file:
        raw_data = file.read()
    try:
        text = raw_data.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_data.decode("cp1250")
    return text

# Funkcja ekstrakcji danych z DIV o id="marketList"
def extract_data_from_div(html):
    soup = BeautifulSoup(html, "html.parser")
    market_div = soup.find("div", id="marketList")
    extracted_data = []
    if market_div:
        market_entries = market_div.find_all("div", class_=lambda x: x and "cursor-pointer" in x)
        for entry in market_entries:
            details = entry.find_all("div", class_="text-center")
            if len(details) >= 3:
                name = details[0].get_text(strip=True)
                address = details[1].get_text(strip=True)
                postal_city = details[2].get_text(strip=True)
            else:
                name = details[0].get_text(strip=True) if len(details) > 0 else ""
                address = details[1].get_text(strip=True) if len(details) > 1 else ""
                postal_city = ""
            extracted_data.append(f"{name};{address};{postal_city}")
    return extracted_data

# Funkcja zapisująca dane do pliku
def save_to_file(data, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        if isinstance(data, list):
            file.write("\n".join(data))
        else:
            file.write(data)

# Funkcja czyszcząca tekst (usunięcie skrótów, kropek itp.)
def clean_text(text):
    text = re.sub(r"\b\w{1,3}\.", "", text)
    text = text.replace(".", "")
    text = re.sub(r"/.*", "", text)
    text = re.sub(r"\b\d{1,2}-(go|tego)\b", "", text)
    return text.strip()

# Funkcja parsująca dane i przygotowująca rekordy do geokodowania
def parse_and_geocode_data(input_lines):
    records = []
    original_addresses = []
    for line in input_lines:
        parts = [clean_text(part.strip()) for part in line.strip().split(";")]
        original_addresses.append(line.strip())
        if len(parts) != 3:
            print(f"Nieprawidłowy format wiersza: {line}")
            continue

        nazwa, ulica, postal_city = parts

        # Usunięcie "ul." z nazwy ulicy
        ulica = re.sub(r"\bul\s*", "", ulica, flags=re.IGNORECASE).strip()

        # Podział na kod pocztowy i miejscowość
        postal_parts = postal_city.split()
        kod_pocztowy = postal_parts[0] if len(postal_parts) >= 2 else ""
        miejscowosc = " ".join(postal_parts[1:]) if len(postal_parts) >= 2 else postal_city

        # Podział ulicy na numer domu i nazwę ulicy
        ulica_parts = ulica.split()
        if len(ulica_parts) > 1 and ulica_parts[-1].isdigit():
            numer_domu = ulica_parts[-1]
            nazwa_ulicy = " ".join(ulica_parts[:-1])
        else:
            numer_domu = ""
            nazwa_ulicy = ulica

        # Generowanie 4 wariantów adresów
        candidate_addresses = [
            f"Dino {nazwa_ulicy} {numer_domu} {kod_pocztowy} {miejscowosc} Polska",
            f"{nazwa_ulicy} {numer_domu} {kod_pocztowy} {miejscowosc} Polska",
            f"{miejscowosc} {kod_pocztowy} {nazwa_ulicy} {numer_domu} Polska",
            f"{kod_pocztowy} {miejscowosc} {nazwa_ulicy} {numer_domu} Polska"
        ]

        records.append({
            "nazwa": nazwa,
            "ulica": nazwa_ulicy,
            "numer_dom": numer_domu,
            "kod_pocz": kod_pocztowy,
            "miejsco": miejscowosc,
            "adresy": candidate_addresses
        })
    return records, original_addresses

# Funkcja geokodująca rekordy i zapisująca informację, który wariant adresu został użyty
def geocode_records(records, original_addresses, total_records):
    geolocator = Nominatim(user_agent="GetLoc", timeout=10)
    transformer = Transformer.from_crs("epsg:4326", "epsg:2180", always_xy=True)
    
    geoms = []
    attributes = {
        "nazwa": [],
        "ulica": [],
        "numer_dom": [],
        "kod_pocz": [],
        "miejsco": [],
        "type": []  # kolumna do zapisu numeru wariantu
    }
    errors = []
    
    for index, (rec, orig_addr) in enumerate(zip(records, original_addresses), start=1):
        found = False
        candidate_type = None
        for i, adres in enumerate(rec["adresy"], start=1):
            print(f"[{index} / {total_records}] Próbuję wariant {i}: {adres}")
            try:
                loc = geolocator.geocode(adres)
            except Exception as e:
                print(f"Błąd geokodowania: {e}")
                loc = None

            if loc:
                print(f"Znaleziono: {loc.address} -> {loc.latitude}, {loc.longitude}")
                x, y = transformer.transform(loc.longitude, loc.latitude)
                geoms.append(Point(x, y))
                candidate_type = i
                found = True
                break  # zatrzymujemy próbę przy pierwszym sukcesie
        if found:
            attributes["nazwa"].append(rec["nazwa"])
            attributes["ulica"].append(rec["ulica"])
            attributes["numer_dom"].append(rec["numer_dom"])
            attributes["kod_pocz"].append(rec["kod_pocz"])
            attributes["miejsco"].append(rec["miejsco"])
            attributes["type"].append(candidate_type)
        else:
            print(f"Nie znaleziono adresu dla: {rec['adresy'][0]}")
            errors.append(orig_addr)
        time.sleep(1.5)
    return attributes, geoms, errors

def main():
    # Dynamiczne generowanie nazw plików
    now = datetime.now()
    timestamp = now.strftime("%d_%m_%Y_%H_%M")
    date_only = now.strftime("%d_%m_%Y")
    raw_filename = f"outputRaw_{timestamp}.txt"
    clean_filename = f"outputCleaned_{timestamp}.txt"
    error_filename = f"invalid_locs_{timestamp}.txt"
    shp_filename = f"dino_{date_only}.shp"

    # Wczytanie pliku "site.html"
    html_content = load_html("site.html")
    if not html_content:
        print("Plik site.html nie został znaleziony lub jest pusty.")
        return

    # Ekstrakcja danych z HTML
    raw_data_list = extract_data_from_div(html_content)
    save_to_file(raw_data_list, raw_filename)
    print(f"Surowe dane zapisane do {raw_filename}")
    
    # Czyszczenie danych
    cleaned_data = []
    for line in raw_data_list:
        parts = line.split(";")
        cleaned_parts = [clean_text(part) for part in parts]
        cleaned_line = ";".join(cleaned_parts)
        cleaned_data.append(cleaned_line)
    
    save_to_file(cleaned_data, clean_filename)
    print(f"Oczyszczone dane zapisane do {clean_filename}")
    
    # Dla testu przetwarzamy tylko pierwsze 50 rekordów
    # cleaned_data = cleaned_data[:50]
    
    # Parsowanie i przygotowanie rekordów do geokodowania
    records, original_addresses = parse_and_geocode_data(cleaned_data)
    total_records = len(cleaned_data)
    
    # Geokodowanie rekordów
    attributes, geoms, errors = geocode_records(records, original_addresses, total_records)
    
    if errors:
        save_to_file(errors, error_filename)
        print(f"Błędne dane zapisane do {error_filename}")
    
    # Zapis danych do pliku SHP, jeśli są poprawne współrzędne
    if geoms:
        df = pd.DataFrame(attributes)
        gdf = gpd.GeoDataFrame(df, geometry=geoms, crs="epsg:2180")
        gdf.to_file(shp_filename, driver="ESRI Shapefile", encoding="utf-8")
        print(f"Plik SHP zapisany jako {shp_filename}")
    else:
        print("Brak poprawnych danych – nie zapisano pliku SHP.")

if __name__ == "__main__":
    main()
