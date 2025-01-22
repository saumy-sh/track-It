import requests

url = "https://expedia13.p.rapidapi.com/api/v1/flight/search-one-way"

def search_flight(source,destination,date,adults,cabin_class="COACH"):
    querystring = {"originAirportCode":source,"destinationAirportCode":destination,"departDate":date,"flightsCabinClass":cabin_class,"adults":adults}

    headers = {
        "x-rapidapi-key": "8ac6e5577bmsh6227bc32fdb9aebp163a8djsn3ad61cc2d0c0",
        "x-rapidapi-host": "expedia13.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring).json()
    print(response)
    result = []
    # results format: [flight logo url, fligh name and flight no, price, duration, takeoff terminal, landing terminal, takeoff time, landing time, date, booking_url]

    if "data" in response:
        for data in response["data"]:
            info = data["journeys"][0]["legs"][0]
            flight_no = info["additionalInfo"][1]
            price = data["pricingInformation"]["mainPrice"]["completeText"]
            date = data["preloadedInfo"]["journeyDate"]
            duration = data["journeys"][0]["durationAndStops"]
            flight_url = data["airlines"][0]["image"]["url"]
            booking_url = data["prices"][0]["bookingURL"][0]["url"]
            takeoff_from = info["fromAirport"]
            landing_at = info["toAirport"]
            takeoff_time = info["departure"]
            landing_time = info["arrival"]



            # print(flight_no,price,flight_url,date,takeoff_from,landing_at,duration,booking_url)
            result.append([flight_url,flight_no,price,duration,takeoff_from,landing_at,takeoff_time,landing_time,date,booking_url])
            # print("############################################")
    else:
        result = "null"


    return result