import time
import re
from datetime import datetime
from geopy.geocoders import Nominatim
from pyproj import Transformer
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd

# Funkcja do wczytania pliku ERROR z kodowaniem UTF-8
def load_error_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip()]

# Funkcja pomocnicza: próba konwersji tekstu na float, zwraca None w razie niepowodzenia
def try_float(s):
    try:
        return float(s.strip())
    except:
        return None

# Funkcja parsująca adres (zakładamy format "nazwa;adres" lub "nazwa;adres;postal")
def parse_address(addr_str):
    parts = [p.strip() for p in addr_str.split(";") if p.strip()]
    if len(parts) >= 3:
        nazwa = parts[0]
        ulica = parts[1]
        postal_city = parts[2]
    elif len(parts) == 2:
        nazwa = parts[0]
        subparts = [s.strip() for s in parts[1].split(",") if s.strip()]
        if len(subparts) >= 2:
            ulica = subparts[0]
            postal_city = subparts[1]
        else:
            ulica = parts[1]
            postal_city = ""
    else:
        nazwa = addr_str
        ulica = ""
        postal_city = ""
    ulica = re.sub(r"\bul\s*", "", ulica, flags=re.IGNORECASE).strip()
    postal_parts = postal_city.split()
    if len(postal_parts) >= 2:
        kod_pocz = postal_parts[0]
        miejscowosc = " ".join(postal_parts[1:])
    else:
        kod_pocz = ""
        miejscowosc = postal_city
    ulica_parts = ulica.split()
    if len(ulica_parts) > 1 and ulica_parts[-1].isdigit():
        numer_dom = ulica_parts[-1]
        nazwa_ulicy = " ".join(ulica_parts[:-1])
    else:
        numer_dom = ""
        nazwa_ulicy = ulica
    return {
        "nazwa": nazwa,
        "ulica": nazwa_ulicy,
        "numer_dom": numer_dom,
        "kod_pocz": kod_pocz,
        "miejsco": miejscowosc
    }

# Funkcja generująca warianty adresów na podstawie nowego adresu
def generate_candidate_addresses(new_addr_str):
    parsed = parse_address(new_addr_str)
    nazwa_ulicy = parsed["ulica"]
    numer_dom = parsed["numer_dom"]
    kod_pocz = parsed["kod_pocz"]
    miejscowosc = parsed["miejsco"]
    candidates = [
        f"Dino {nazwa_ulicy} {numer_dom} {kod_pocz} {miejscowosc} Polska",
        f"{nazwa_ulicy} {numer_dom} {kod_pocz} {miejscowosc} Polska",
        f"{miejscowosc} {kod_pocz} {nazwa_ulicy} {numer_dom} Polska",
        f"{kod_pocz} {miejscowosc} {nazwa_ulicy} {numer_dom} Polska"
    ]
    return candidates

# Funkcja geokodująca adres (dla typu 1) – próbuje kolejne warianty i zwraca (punkt, typ) lub (None, None)
def geocode_new_address(new_addr_str, row_index, total_rows):
    candidates = generate_candidate_addresses(new_addr_str)
    geolocator = Nominatim(user_agent="GetLocErrors", timeout=10)
    transformer = Transformer.from_crs("epsg:4326", "epsg:2180", always_xy=True)
    for i, candidate in enumerate(candidates, start=1):
        print(f"[{row_index} / {total_rows}] Próbuję wariant {i}: {candidate}")
        try:
            loc = geolocator.geocode(candidate)
        except Exception as e:
            print(f"[{row_index} / {total_rows}] Błąd geokodowania: {e}")
            loc = None
        if loc:
            print(f"[{row_index} / {total_rows}] Znaleziono: {loc.address} -> {loc.latitude}, {loc.longitude}")
            x, y = transformer.transform(loc.longitude, loc.latitude)
            return Point(x, y), i
        time.sleep(1.5)
    return None, None

# Funkcja przetwarzająca pojedynczy wiersz z pliku błędów
def process_error_line(line, row_index, total_rows):
    parts = [p.strip() for p in line.split("//") if p.strip()]
    # Jeśli mamy trzy elementy, rozróżniamy typ wiersza:
    if len(parts) == 3:
        second = parts[1]
        coords = [try_float(x) for x in second.split(",")]
        # Jeśli uda się sparsować dwie liczby, traktujemy to jako wiersz z koordynatami
        if len(coords) == 2 and all(c is not None for c in coords):
            addr_attrs = parse_address(parts[0])
            # Ustawiamy type = 4 (zgodnie z wymaganiem, aby typ był między 1 a 4)
            candidate_type = 4
            lat, lon = coords
            transformer = Transformer.from_crs("epsg:4326", "epsg:2180", always_xy=True)
            x, y = transformer.transform(lon, lat)
            pt = Point(x, y)
            return {
                "attrs": addr_attrs,
                "point": pt,
                "type": candidate_type,
                "error": parts[2]
            }
        else:
            # W przeciwnym razie traktujemy to jako wiersz z nowym adresem
            new_addr = parts[1]
            pt, candidate_type = geocode_new_address(new_addr, row_index, total_rows)
            addr_attrs = parse_address(parts[0])
            return {
                "attrs": addr_attrs,
                "point": pt,
                "type": candidate_type if candidate_type is not None else -1,
                "error": parts[2]
            }
    else:
        print(f"[{row_index} / {total_rows}] Nieznany format wiersza: {line}")
        return None

def main():
    # Stała ścieżka do pliku ERROR
    error_path = r"C:\Users\damia\Downloads\test2\Incorrect_checked.txt"
    lines = load_error_file(error_path)
    
    features = []
    error_lines_failed = []
    total = len(lines)
    
    for idx, line in enumerate(lines, start=1):
        print(f"Przetwarzam wiersz {idx} / {total}")
        result = process_error_line(line, idx, total)
        if result is None or result["point"] is None:
            print(f"[{idx} / {total}] Nie udało się przetworzyć wiersza: {line}")
            error_lines_failed.append(line)
            continue
        attrs = result["attrs"]
        attrs["type"] = result["type"]
        attrs["error"] = result["error"]
        features.append((attrs, result["point"]))
    
    if not features:
        print("Brak poprawnych danych – nie tworzę pliku SHP.")
        return

    all_attrs = {
        "nazwa": [],
        "ulica": [],
        "numer_dom": [],
        "kod_pocz": [],
        "miejsco": [],
        "type": [],
        "error": []
    }
    geoms = []
    for attrs, pt in features:
        all_attrs["nazwa"].append(attrs.get("nazwa", ""))
        all_attrs["ulica"].append(attrs.get("ulica", ""))
        all_attrs["numer_dom"].append(attrs.get("numer_dom", ""))
        all_attrs["kod_pocz"].append(attrs.get("kod_pocz", ""))
        all_attrs["miejsco"].append(attrs.get("miejsco", ""))
        all_attrs["type"].append(attrs.get("type", ""))
        all_attrs["error"].append(attrs.get("error", ""))
        geoms.append(pt)
    
    df = pd.DataFrame(all_attrs)
    gdf = gpd.GeoDataFrame(df, geometry=geoms, crs="epsg:2180")
    
    now = datetime.now()
    date_only = now.strftime("%d_%m_%Y")
    shp_filename = f"errors_{date_only}.shp"
    
    gdf.to_file(shp_filename, driver="ESRI Shapefile", encoding="utf-8")
    print(f"Plik SHP utworzony: {shp_filename}")
    
    if error_lines_failed:
        timestamp = now.strftime("%d_%m_%Y_%H_%M")
        err_filename = f"errors_not_geocoded_{timestamp}.txt"
        with open(err_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(error_lines_failed))
        print(f"Niegeokodowane wiersze zapisane do: {err_filename}")

if __name__ == "__main__":
    main()
