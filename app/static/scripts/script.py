from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException,NoSuchElementException
import time
import random



# source,destination,date_from,date_to

TARGET_SITE = "https://www.happyfares.in/?utm_source=Google&campaign_ID=12305358667&pl=&key_word_identifier=happyfares&ad_group_id_identifier=119036993513&gad_source=1&gclid=CjwKCAiA9vS6BhA9EiwAJpnXw_-ZSkoIV7OsWc_cypjmWTjx0_i5LsN3jchfN4Wt16gqmBsTXeZGXBoCHO4QAvD_BwE"
PATH = 'chromedriver-win64/chromedriver.exe'

# journey details
departure_date = "6 01 2025"
source = "lucknow"
destination = "bangalore"
return_date = "7 01 2025"


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
    

    service = Service(PATH, log_output="chromedriver.log")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver



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

def source_selector(source,driver,actions):
    source_xpath = "//input[@placeholder='Select Origin City']"
    source_element = WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,source_xpath))
    )
    source_element.click()
    source_element.send_keys(source)
    time.sleep(1)
    source_element.send_keys(Keys.ENTER)

def destination_selector(destination,driver,actions):
    destination_xpath = "//input[@placeholder='Select Destination City']"
    destination_element = WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,destination_xpath))
    )
    destination_element.click()
    destination_element.send_keys(destination)
    time.sleep(1)
    destination_element.send_keys(Keys.ENTER)


def date_selector(date,driver,xpath,date_type):
    WebDriverWait(driver,5).until(
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
            WebDriverWait(driver,5).until(
                EC.element_to_be_clickable((By.XPATH,date_xpath))
            ).click()
            month_present = True
        except TimeoutException:
            driver.save_screenshot("err.png")
            next_btn_xpath = "//span[@class='right']"
            WebDriverWait(driver,2).until(
                EC.element_to_be_clickable((By.XPATH,next_btn_xpath))
            ).click()
            time.sleep(0.2)

def round_trip(driver):
    roundTrip_xpath = "//label[@for='ROUNDTRIP']"
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,roundTrip_xpath))
    ).click()

    # here automatically selecting round trip offer
    # WebDriverWait(driver,1).until(
    #     EC.presence_of_element_located((By.XPATH,"//label[@for='cbRoundTrip_Fare']"))
    # ).click()
    

confirmBtn_xpath = "//button[@id='FarebtnConfirmOKAction']"

def student_selector(driver):
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,"//label[@for='cbDefence1']"))
    ).click()
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,confirmBtn_xpath))
    ).click()

def defence_selector(driver):
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,"//label[@for='cbDefence']"))
    ).click()
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,confirmBtn_xpath))
    ).click()

def seniorCitizen_selector(driver):
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,"//label[@for='cbDefence2']"))
    ).click()
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,confirmBtn_xpath))
    ).click()

def cheapest_flight(source,destination,departure_date,option,return_date=None,roundTrip=False):
    driver = create_headless_driver()
    
    # go to target site
    driver.get(TARGET_SITE)

    # creating cursor like element
    actions = ActionChains(driver)

    # select one-way flight
    one_way(driver,actions)




    # select direct flight option
    direct_flight(driver,actions)



    # selecting source
    source_selector(source,driver,actions) 
    



    # selecting destination 
    destination_selector(destination,driver,actions)



    # selecting departure date
    departureDate_xpath = "//label[@ng-keyup='DPOnFocus(0);']"
    date_selector(departure_date,driver,departureDate_xpath,"dep")


    # checking for various checkboxes
    if option == "student":
        student_selector(driver)
    elif option == "defence":
        defence_selector(driver)
    elif option == "senior citizen":
        seniorCitizen_selector(driver)
    else:
        pass


    returnDate_xpath = "//label[@ng-keyup='DPOnFocus(1);']"
    if roundTrip:
        round_trip(driver)
        date_selector(departure_date,driver,departureDate_xpath,"dep")
        date_selector(return_date,driver,returnDate_xpath,"ret")

    # clicking Search button
    WebDriverWait(driver,1).until(
        EC.presence_of_element_located((By.XPATH,"//input[@value='Search']"))
    ).click()

    time.sleep(15)
    driver.save_screenshot("results.png")

    # selecting flight info that we need
    try:
        time_elements = WebDriverWait(driver,10).until(
            EC.presence_of_all_elements_located((By.XPATH,"//p[@class='mb-0 lbl-bold ng-binding lbl-huge']"))
        )
        flight_nos = WebDriverWait(driver,10).until(
            EC.presence_of_all_elements_located((By.XPATH,"//p[@class='mb-0 d-inline d-lg-block responsive-bold ng-binding']"))
        )
        prices = WebDriverWait(driver,10).until(
            EC.presence_of_all_elements_located((By.XPATH,'//p[@class="font-weight-600 text-gray lbl-bold roboto_font mb-0 ng-binding lbl-huge"]'))
        )
        seats_available = WebDriverWait(driver,10).until(
            EC.presence_of_all_elements_located((By.XPATH,"//span[@class='text ng-binding']"))
        )
        for i in range(0,5):
            print(f"Flight No: {flight_nos[i].text}")
            print(f"Price: {prices[i].get_attribute("innerHTML")}") # here .text will not work, hence using get_attribute 
            print(f"Take-off at:{time_elements[i*2].text}    Landing At: {time_elements[i*2+1].text}")
            print(f"Seats Available: {seats_available[i].text}")
            print("###############################################")
    except TimeoutException:
        print("No flight available for the given combination. Check inner exception.")
    

    driver.quit()

cheapest_flight(source,destination,departure_date,"student")





