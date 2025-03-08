# importing geopy library
from geopy.geocoders import Nominatim
loc = Nominatim(user_agent="GetLoc")

getLoc = loc.geocode("Genarała Władysława Andersa 30A 42-600 Tarnowskie Góry")

if getLoc:
    print(getLoc.address)
    print(getLoc.latitude, ",", getLoc.longitude)
else:
    print("Brak!")


# geolocator = Nominatim(user_agent="GetLoc")  # Możesz podać inną nazwę, np. "my_app"
# location = geolocator.reverse((51.35676080907038, 16.1717930131456), exactly_one=True)

# print(location.address)
