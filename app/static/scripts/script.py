from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException,NoSuchElementException,WebDriverException
import time
import random

returnDate_xpath = "//label[@ng-keyup='DPOnFocus(1);']"



# source,destination,date_from,date_to

TARGET_SITE = "https://www.happyfares.in/?utm_source=Google&campaign_ID=12305358667&pl=&key_word_identifier=happyfares&ad_group_id_identifier=119036993513&gad_source=1&gclid=CjwKCAiA9vS6BhA9EiwAJpnXw_-ZSkoIV7OsWc_cypjmWTjx0_i5LsN3jchfN4Wt16gqmBsTXeZGXBoCHO4QAvD_BwE"
PATH = 'app/static/scripts/chromedriver-win64/chromedriver.exe'
RETRY_ATTEMPT = 3


def date_optimiser(date):
    year,month,day = date.split("-")
    day = int(day)
    return f"{day} {month} {year}"

def extract_number(price_str):
    """
    Extracts the numeric value from a currency string and removes commas.

    :param price_str: The string containing the currency value (e.g., "₹ 5,546.00")
    :return: A float representing the numeric value
    """
    # Remove any non-numeric characters except periods and commas
    numeric_part = ''.join(char for char in price_str if char.isdigit() or char == '.')
    # Remove commas
    numeric_part = numeric_part.replace(',', '')
    return float(numeric_part)




def create_headless_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")  # Recommended for Docker
    chrome_options.add_argument("--disable-dev-shm-usage")  # Avoid shared memory issues
    chrome_options.add_argument("--disable-gpu")  # Optional for performance
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-notifications")

    service = Service(PATH, log_output="chromedriver.log")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


#####################for solving skyscanner captcha#######################
def solve_captcha(driver):
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    time.sleep(5)
    captcha_solved = False
    counter = 6
    current_url = driver.current_url
    print(driver.get_cookies())
    print(f"current url: {current_url}")
    print("################STARTING##################")
    while not captcha_solved:
        try:
            # Access shadow DOM and then click-hold it
            shadow_host = driver.find_element(By.ID, "px-captcha")  # Replace with the shadow host selector
            
            actions = ActionChains(driver)
            actions.move_to_element(shadow_host).perform()
            time.sleep(random.uniform(1.5,2.5))
            actions.click_and_hold().perform()
            time.sleep(random.uniform(counter,counter+1))
            actions.release(shadow_host).perform()
            driver.save_screenshot(f"screenshot{counter}.png")
            time.sleep(5)
            driver.save_screenshot(f"afterwards{counter}.png")
            if current_url != driver.current_url:
                captcha_solved = True
        except TimeoutException and NoSuchElementException:
            captcha_solved = True
        counter += 1
    print("#################DONE#####################")
    time.sleep(5)
#######################################################################      


def one_way(driver,actions):
    
    oneWay_xpath = "//span[@class='font-weight-600 bgoneway text-uppercase CL']"
    try:
        oneWay_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH,oneWay_xpath))
        )
        actions.move_to_element(oneWay_element).double_click().perform()
        time.sleep(0.5)
    except TimeoutException:
        driver.save_screenshot("check.png")

def direct_flight(driver,actions):
    directFlight_xpath = "//input[@id='cbDirectFlight']"
    directFlight_element = WebDriverWait(driver,5).until(
        EC.presence_of_element_located((By.XPATH,directFlight_xpath))
    )
    actions.move_to_element(directFlight_element).click().perform()
    time.sleep(1)

def source_selector(source,driver):
    
    source_xpath = "//input[@placeholder='Select Origin City']"
    source_element = WebDriverWait(driver,5).until(
        EC.presence_of_element_located((By.XPATH,source_xpath))
    )
    source_element.click()
    source_element.send_keys(source)
    time.sleep(1)
    source_element.send_keys(Keys.ENTER)

def destination_selector(destination,driver):
    destination_xpath = "//input[@placeholder='Select Destination City']"
    destination_element = WebDriverWait(driver,5).until(
        EC.presence_of_element_located((By.XPATH,destination_xpath))
    )
    destination_element.click()
    destination_element.send_keys(destination)
    time.sleep(1)
    destination_element.send_keys(Keys.ENTER)


def date_selector(date,driver,xpath,date_type):
    WebDriverWait(driver,20).until(
        EC.presence_of_element_located((By.XPATH,xpath))
    ).click()
    time.sleep(0.5)
    month_present = False
    day,month,year = date.split()
    if date_type == "dep":
        date_xpath = f'//td[@id="spnselectdate_{day}{month}{year}0"]'
    else:
        date_xpath = f'//td[@id="spnselectdate_{day}{month}{year}1"]'
    while not month_present:
        try:
            date_element = WebDriverWait(driver,15).until(
                EC.presence_of_element_located((By.XPATH,date_xpath))
            )
            date_element.click()
            month_present = True
        except TimeoutException:
            driver.save_screenshot("err.png")
            next_btn_xpath = "//span[@class='right']"
            next_btn_elmnt = WebDriverWait(driver,5).until(
                EC.presence_of_element_located((By.XPATH,next_btn_xpath))
            )
            next_btn_elmnt.click()
            time.sleep(0.2)

def round_trip(driver):
    roundTrip_xpath = "//label[@for='ROUNDTRIP']"
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,roundTrip_xpath))
    ).click()

    

confirmBtn_xpath = "//button[@id='FarebtnConfirmOKAction']"

def student_selector(driver):
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,"//label[@for='cbDefence1']"))
    ).click()
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,confirmBtn_xpath))
    ).click()

def defence_selector(driver):
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,"//label[@for='cbDefence']"))
    ).click()
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,confirmBtn_xpath))
    ).click()

def seniorCitizen_selector(driver):
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,"//label[@for='cbDefence2']"))
    ).click()
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,confirmBtn_xpath))
    ).click()

def doctorNurses_selector(driver):
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,"//label[@for='cbDefence3']"))
    ).click()
    WebDriverWait(driver,3).until(
        EC.presence_of_element_located((By.XPATH,confirmBtn_xpath))
    ).click()

def cheapest_flight(source,destination,departure_date,option,direct=False):
    results = {"value":"null"}
    try:
        driver = create_headless_driver()
        # go to target site
        driver.get(TARGET_SITE)
        driver.implicitly_wait(10)
        # creating cursor like element
        actions = ActionChains(driver)

        # select one-way flight
        one_way(driver,actions)




        # select direct flight option
        if direct:
            direct_flight(driver,actions)



        # selecting source
        source_selector(source,driver) 
        



        # selecting destination 
        destination_selector(destination,driver)



        # selecting departure date
        departureDate_xpath = "//label[@ng-keyup='DPOnFocus(0);']"
        date_selector(departure_date,driver,departureDate_xpath,"dep")


        # checking for various checkboxes
        if option == "student":
            student_selector(driver)
        elif option == "defence":
            defence_selector(driver)
        elif option == "senior_citizen":
            seniorCitizen_selector(driver)
        elif option == "doctors_nurses":
            doctorNurses_selector(driver)
        else:
            print("No option selected")


        

        # clicking Search button
        WebDriverWait(driver,2).until(
            EC.presence_of_element_located((By.XPATH,"//input[@value='Search']"))
        ).click()

        
        # selecting flight info that we need
        try:
            time_elements = WebDriverWait(driver,30).until(
                EC.presence_of_all_elements_located((By.XPATH,"//p[@class='mb-0 lbl-bold ng-binding lbl-huge']"))
            )
            # print(f"time_elements: {time_elements}")

            flight_nos = WebDriverWait(driver,30).until(
                EC.presence_of_all_elements_located((By.XPATH,"//p[@class='mb-0 d-inline d-lg-block responsive-bold ng-binding']"))
            )

            # print(f"flight_nos:{flight_nos}")
            prices = WebDriverWait(driver,30).until(
                EC.presence_of_all_elements_located((By.XPATH,'//p[@class="font-weight-600 text-gray lbl-bold roboto_font mb-0 ng-binding lbl-huge"]'))
            )
            # print(f"prices:{prices}")
            # seats_available = WebDriverWait(driver,10).until(
            #     EC.presence_of_all_elements_located((By.XPATH,"//span[@class='text ng-binding']"))
            # )


            num = len(flight_nos)
            print("time:",len(time_elements))
            print("flights:",num)
            
            result_value = []
            if num > 10 or len(time_elements) > 2*num:
                num = min(10,len(time_elements)//2)
            print(num)
            # results format: [flight_no with flight name, price, take-off time, land time]
            for i in range(0,num):
                result_value.append([flight_nos[i].text,prices[i].get_attribute("innerHTML"),time_elements[i*2].text,time_elements[i*2+1].text])
                print(f"Flight No: {flight_nos[i].text}")
                print(f"Price: {prices[i].get_attribute("innerHTML")}") # here .text will not work, hence using get_attribute 
                print(f"Take-off at:{time_elements[i*2].text}    Landing At: {time_elements[i*2+1].text}")
                # print(f"Seats Available: {seats_available[i].text}")
                print("###############################################")
        
            results["value"] = result_value
        except TimeoutException:
            driver.save_screenshot("err.png")
            results["value"] = "null"
        driver.quit()
        return results["value"]
        

    except WebDriverException:
        results["value"] = "error"
        driver.quit()
        return results["value"]
    
    
    
# tracker for flight prices
def price_tracker(driver,tracker_data):
    
    try:
        
        driver.get(TARGET_SITE)
        driver.implicitly_wait(10)
        # creating cursor like element
        actions = ActionChains(driver)

        # select one-way flight
        one_way(driver,actions)
        print("one")
        # selecting source
        source_selector(tracker_data["source"],driver) 
        print("two")
        # selecting destination 
        destination_selector(tracker_data["destination"],driver)
        print("three")
        # selecting departure date
        departureDate_xpath = "//label[@ng-keyup='DPOnFocus(0);']"
        date_selector(date_optimiser(tracker_data["date"]),driver,departureDate_xpath,"dep")
        print("four")
        # clicking Search button
        WebDriverWait(driver,2).until(
            EC.presence_of_element_located((By.XPATH,"//input[@value='Search']"))
        ).click()

        # selecting flight info that we need
        
        # print(f"time_elements: {time_elements}")
        print("five")
        time.sleep(10)
        flight_nos = WebDriverWait(driver,30).until(
            EC.presence_of_all_elements_located((By.XPATH,"//p[@class='mb-0 d-inline d-lg-block responsive-bold ng-binding']"))
        )
        print("six")
        # print(f"flight_nos:{flight_nos}")
        prices = WebDriverWait(driver,30).until(
            EC.presence_of_all_elements_located((By.XPATH,'//p[@class="font-weight-600 text-gray lbl-bold roboto_font mb-0 ng-binding lbl-huge"]'))
        )
        print("seven")
        num = len(flight_nos)
        print("flights:",num)
        
        for i in range(0,num):
            print(flight_nos[i].text)
            if tracker_data["flight_no"] == flight_nos[i].text:
                print("found")
                float_price_new = extract_number(prices[i].get_attribute("innerHTML"))
                float_price_old = extract_number(tracker_data["price"])
                if float_price_new > float_price_old:
                    tracker_data["price"] = prices[i].get_attribute("innerHTML")
                    tracker_data["price_change"]="up"
                    return tracker_data
                elif float_price_new < float_price_old:
                    tracker_data["price"] = prices[i].get_attribute("innerHTML")
                    tracker_data["price_change"]="down"
                    return tracker_data
                else:
                    tracker_data["price_change"]="neutral"
                    return tracker_data
                
        


    except Exception as e:
        print(f"A big error occured:{e}")
        
        return "error"
    








