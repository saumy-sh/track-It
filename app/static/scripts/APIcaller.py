import requests

url = "https://expedia13.p.rapidapi.com/api/v1/flight/search-one-way"

def search_flight(source,destination,date,adults,cabin_class="COACH"):
    querystring = {"originAirportCode":source,"destinationAirportCode":destination,"departDate":date,"flightsCabinClass":cabin_class,"adults":adults}

    headers = {
        "x-rapidapi-key": "8ac6e5577bmsh6227bc32fdb9aebp163a8djsn3ad61cc2d0c0",
        "x-rapidapi-host": "expedia13.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring).json()

    result = []
    # results format: [flight logo url, fligh name and flight no, price, take-off time - land time(duration with tag), takeoff terminal, landing terminal, date, booking_url]

    for data in response["data"]:
        info = data["journeys"][0]["legs"][0]
        flight_no = info["additionalInfo"][1]
        price = data["pricingInformation"]["mainPrice"]["completeText"]
        date = data["preloadedInfo"]["journeyDate"]
        flight_time_with_duration = data["preloadedInfo"]["durationAndStops"]
        flight_url = data["airlines"][0]["image"]["url"]
        booking_url = data["prices"][0]["bookingURL"][0]["url"]
        takeoff_from = info["fromAirport"]
        landing_at = info["toAirport"]

        print(flight_no,price,flight_url,date,takeoff_from,landing_at,flight_time_with_duration,booking_url)
        result.append([flight_url,flight_no,price,flight_time_with_duration,takeoff_from,landing_at,date,booking_url])
        print("############################################")


    return result