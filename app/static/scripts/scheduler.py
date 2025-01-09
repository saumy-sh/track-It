from script import price_tracker,create_headless_driver
from app import mongo
from flask_mail import Message
from app import mail
tracker_data = mongo.db.usersearch.find()
results = []
for data in tracker_data:
    print(data)
    driver = create_headless_driver()
    results.append(price_tracker(driver,data))
    driver.quit()
    print(results)


try:
    for data in results:
        if data != None:
            if not data["stale"]:
                print(data)
                mongo.db.usersearch.update_one({"flight_no":data["prev_flight_no"]},
                                                {"$set":{
                                                    "price":data["price"],
                                                    "flight_no":data["flight_no"],
                                                    "take_off":data["take_off"],
                                                    "landing_at":data["landing_at"],
                                                    "price_change":data["price_change"],
                                                    "terminal_takeoff":data["terminal_takeoff"],
                                                    "terminal_landing":data["terminal_landing"],
                                                    "duration":data["duration"],
                                                    "take_off_date":data["take_off_date"],
                                                    "landing_date":data["landing_date"]
                                                    }
                                                })
                
                if data["trackCheap"]:
                    subject = f"✨ Hot Deal Alert! ✈️ Cheapest Flight on {data['date']}: {data['flight_no']} from {data['source']} to {data['destination']}! 💸"
                elif data["price_change"] == "up":
                    subject = f"Price Spike Alert! 🚀 Flight {data['flight_no']} from {data['source']} to {data['destination']} Just Got More Expensive! 💰"
                elif data["price_change"] == "down":
                    subject = f"Great News! ✈️ Flight {data['flight_no']} from {data['source']} to {data['destination']} is Now Cheaper! 🎉"
                else:
                    pass
                cleaned_price = data['price'].replace('\\u20b9', '₹')
                message_body = f"""
                Flight Details ✈️

                Flight Number: {data['flight_no']}
                Route: {data['source']} ➡️ {data['destination']}
                Date: {data['date']}
                Take Off Time: {data['take_off']} {data['take_off_date']}
                Landing Time: {data['landing_at']} {data['landing_date']}
                Take Off Terminal: {data['terminal_takeoff']}
                Landing Terminal: {data['terminal_landing']}

                Current Price: 💸{cleaned_price}💸

                Safe travels! ✈️
                """                            
                recipient_mail = [data["email"]]
                msg = Message(
                    subject=subject,
                    recipients = recipient_mail,
                    body=message_body
                )
                mail.send(msg)
                print(f"Mail sent to {recipient_mail} :)")
            else:
                mongo.db.usersearch.delete_one({
                    "date":data["date"],
                    "flight_no":data["flight_no"]
                })
except Exception as e:
    print(f"An error occured:{e}")