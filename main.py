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
import time
from bs4 import BeautifulSoup


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
chrome_options = Options()
# options = [
#     "--headless",
#     f"--user-agent={user_agent}"
# ]
# for option in options:
#     chrome_options.add_argument(option)

# run in  github action
# driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),options=chrome_options)

# run in local
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=chrome_options)
wait = WebDriverWait(driver, 10)

url = "https://e-ipo.co.id/en/ipo/closed"
driver.get(url)

table_element = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="w0"]/div[1]/table')))
table = driver.find_element(By.XPATH, '//*[@id="w0"]/div[1]/table')

table_data = []
for row in table.find_elements(By.TAG_NAME, 'tr'):
    row_data = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, 'td')]
    table_data.append(row_data)

df = pd.DataFrame(table_data)
df.columns = ['ticker_code','company', 'status','listing_date','price','funded_in_idr']
df.dropna(inplace=True)
df['price'] = df['price'].apply(lambda x: x.replace(',', '') if ',' in x else x).astype(float)
df['funded_in_idr'] = df['funded_in_idr'].apply(lambda x: x.replace(',', '') if ',' in x else x).astype(float)

df['listing_date'] = pd.to_datetime(df['listing_date'], format='%d-%m-%Y')
today_date = datetime.now().date()
df = df[df['listing_date'].dt.date > today_date]

def extract_company_info():
    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'col-md-8')))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        company_info_divs = soup.find('div', {'class': 'col-md-8'})

        data = {}
        current_key = None
        current_value = []

        for element in company_info_divs.find_all(['h5', 'p']):
            if element.name == 'h5':
                if current_key is not None:
                    data[current_key] = ', '.join(current_value)
                current_key = element.text
                current_value = []
            elif element.name == 'p':
                if element.find('br'):
                    br_text = ', '.join(element.stripped_strings)
                    current_value.append(br_text)
                else:
                    current_value.append(element.text)

        if current_key is not None:
            data[current_key] = ', '.join(current_value)

        return data
    except Exception as e:
        print(f"Error extracting company info: {str(e)}")
        return {}


company_info_list = []
for index, row in df.iterrows():
    try:
        url = "https://e-ipo.co.id/en/ipo/closed"
        driver.get(url)

        company_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, row['company'])))
        company_link.click()

        more_info_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, 'More Info')))
        more_info_button.click()

        company_info = extract_company_info()
        company_info_list.append(company_info)

        time.sleep(5)

    except Exception as e:
        print(f"Error processing {row['company']}: {str(e)}")

driver.quit()

detail_df = pd.DataFrame(company_info_list)

result_df = pd.merge(df, detail_df, left_on='ticker_code', right_on='Ticker Code', how='inner')

result_df.drop(columns='Ticker Code', inplace=True)

result_df.rename(columns={
    'Sector': 'sector',
    'Subsector': 'sub_sector',
    'Line Of Business': 'line_of_business',
    'Company Overview': 'company_overview',
    'Address': 'address',
    'Website': 'website',
    'Number of shares offered': 'number_of_shares_offered',
    "% of Total Shares": 'percent_of_total_shares',
    'Participant Admin': 'participant_admin',
    'Underwriter(s)': 'underwriter'
}, inplace=True)

result_df['number_of_shares_offered'] = result_df['number_of_shares_offered'].str.replace(' shares', '').str.replace(',', '', regex=True).astype(float)

result_df.to_csv('upcoming_ipo.csv',index=False)