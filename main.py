from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import pandas as pd
from datetime import datetime
import logging
logging.basicConfig(level=logging.ERROR)


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
chrome_options = Options()
options = [
    "--headless",
    f"--user-agent={user_agent}"
]
for option in options:
    chrome_options.add_argument(option)

driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),options=chrome_options)
wait = WebDriverWait(driver, 10)

url = "https://e-ipo.co.id/en/ipo/closed"
driver.get(url)

table_element = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="w0"]/div[1]/table')))
table = driver.find_element(By.XPATH, '//*[@id="w0"]/div[1]/table')

table_data = []
for row in table.find_elements(By.TAG_NAME, 'tr'):
    row_data = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, 'td')]
    table_data.append(row_data)

driver.quit()

df = pd.DataFrame(table_data)
df.columns = ['ticker_code','company', 'status','listing_date','price','funded_in_idr']
df.dropna(inplace=True)
df['price'] = df['price'].apply(lambda x: x.replace(',', '') if ',' in x else x).astype(float)
df['funded_in_idr'] = df['funded_in_idr'].apply(lambda x: x.replace(',', '') if ',' in x else x).astype(float)

df['listing_date'] = pd.to_datetime(df['listing_date'], format='%d-%m-%Y')
today_date = datetime.now().date()
df = df[df['listing_date'].dt.date > today_date]


df.to_csv('upcoming_ipo.csv',index=False)