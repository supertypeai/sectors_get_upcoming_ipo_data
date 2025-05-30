from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import sys
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import urllib.request
import translators as ts
import os
import logging
from imp import reload
from dotenv import load_dotenv
load_dotenv()

def initiate_logging(LOG_FILENAME):
    reload(logging)

    formatLOG = '%(asctime)s - %(levelname)s: %(message)s'
    logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO, format=formatLOG)
    logging.info('Program started')

def convert_date(date_str):
    date_object = datetime.strptime(date_str, "%d %b %Y")
    return date_object.strftime("%Y-%m-%d")

def extract_company_info(new_url):
    try:
        with urllib.request.urlopen(new_url) as response:
            html_detail = response.read()
        soup_detail = BeautifulSoup(html_detail, 'html.parser')
        company_info_divs = soup_detail.find("div", class_="panel-body panel-scroll")

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

def translate_to_english(text):
    translated_text = ts.translate_text(text, translator="google", from_language='id',to_language='en')
    return translated_text

if __name__ == '__main__':
    LOG_FILENAME = 'scraper.log'
    initiate_logging(LOG_FILENAME)

    try:
        try:
            proxy = os.environ.get("proxy")

            proxy_support = urllib.request.ProxyHandler({'http': proxy,'https': proxy})
            opener = urllib.request.build_opener(proxy_support)
            urllib.request.install_opener(opener)
        except Exception as e:
            raise Exception("Error setting up proxy: {str(e)}")
            
        result = {
            "ticker_code" : [],
            "company" : [],
            "book_building_period" : [],
            "book_building_price_range" : [],
            "sector" : [],
            "sub_sector":[],
            "line_of_business_id":[],
            "company_overview_id":[],
            "address": [],
            "website": [],
            "number_of_shares_offered" : [],
            "percent_of_total_shares": [],
            "participant_admin": [],
            "underwriter": [],
            "updated_on": [],
        }

        try:
            url = f'https://e-ipo.co.id/en/ipo/index?per-page=&query=&sort=-updated_at&status_id=2&view=list'
            with urllib.request.urlopen(url) as response:
                html = response.read()
                print(html)
            soup = BeautifulSoup(html, 'html.parser')
        except Exception as e:
            raise Exception(f"Error fetching data: {str(e)}")

        try:
            names = []
            names_class = soup.find_all(class_="margin-left10 colorwhite")
            for name in names_class:
                company_name, symbol = name.get_text().replace("Sharia", "").replace(")", "").split(' (')
                result["ticker_code"].append(symbol.replace("Closed", "").replace("Book Building",""))
                result["company"].append(company_name)

            notopmargins = soup.find_all("p", class_="notopmargin")
            nobottommargins = soup.find_all(class_="nobottommargin")
            for top, bottom in zip(notopmargins, nobottommargins):
                if bottom.get_text() == "Sector": result["sector"].append(top.get_text())
                elif bottom.get_text() == "Book Building Period": result["book_building_period"].append(top.get_text())
                elif bottom.get_text() == "Book Building Price Range": result["book_building_price_range"].append(top.get_text())
                elif bottom.get_text() == "Stocks Offered": result["number_of_shares_offered"].append(top.get_text())
        except Exception as e:
            raise Exception(f"Error extracting data: {str(e)}")
        
        try:
            # click details
            buttons = soup.find_all(class_="button button-3d button-small notopmargin button-rounded button-dirtygreen")
            for button in buttons:
                href = button.get("href")
                new_url = f"https://e-ipo.co.id{href}"
                company_info = extract_company_info(new_url)
                print(company_info)
                result["sub_sector"].append(company_info['Subsector'])
                result["line_of_business_id"].append(company_info['Line Of Business'])
                result["company_overview_id"].append(company_info['Company Overview'])
                result["address"].append(company_info['Address'])
                result["website"].append(company_info['Website'])
                result["percent_of_total_shares"].append(float(company_info['% of Total Shares']))
                result["participant_admin"].append(company_info['Participant Admin'])
                result["underwriter"].append(company_info['Underwriter(s)'])
                now = datetime.now()
                result["updated_on"].append(now.strftime("%Y-%m-%d %H:%M:%S"))
            ipo = pd.DataFrame(result)
        except Exception as e:
            raise Exception(f"Error retrieve company: {str(e)}")

        try:
            if ipo.empty:
                print("There's no upcoming ipo")
            else:
                ipo['number_of_shares_offered'] = ipo['number_of_shares_offered'].str.replace(' Lot', '').str.replace(',', '', regex=True).astype(float)
                ipo['book_building_price_range'] = ipo['book_building_price_range'].str.replace('IDR', '').str.replace("\xa0", "").str.replace(',', '', regex=True).astype(str)
                ipo['company_overview'] = ipo['company_overview_id'].apply(translate_to_english)
                ipo['line_of_business'] = ipo['line_of_business_id'].apply(translate_to_english)
                ipo.drop(columns=['line_of_business_id','company_overview_id'], inplace=True)
                ipo = ipo[['updated_on','ticker_code','company','book_building_period','book_building_price_range','sector','sub_sector','line_of_business','company_overview','address','website','number_of_shares_offered','percent_of_total_shares','participant_admin','underwriter']]

                existing_ipo_data = pd.read_csv('https://raw.githubusercontent.com/supertypeai/sectors_get_upcoming_ipo_data/main/ipo.csv')
                ipo_history_data = pd.concat([existing_ipo_data, ipo])

                ipo_history_data['updated_on'] = pd.to_datetime(ipo_history_data['updated_on'])
                six_months_prior = now - relativedelta(months=6)
                ipo_history_data = ipo_history_data[(ipo_history_data['updated_on'] >= six_months_prior) & (ipo_history_data['updated_on'] <= now)]
                ipo_history_data = ipo_history_data.sort_values(by='updated_on').drop_duplicates(subset='ticker_code', keep='last')
                ipo_history_data.to_csv("ipo.csv",index = False)

                ipo.drop(columns=['updated_on'], inplace=True)

                upcoming_ipo_json = ipo.to_dict(orient='records')

                with open('upcoming_ipo.json', 'w') as json_file:
                    json.dump(upcoming_ipo_json, json_file, indent=4)
        except Exception as e:
            raise Exception(f"Error processing data: {str(e)}")
        logging.info(f"Finish scrape {len(ipo['ticker_code'])} upcoming ipo data")
            
    except Exception as e:
        logging.info(f'Program finished with error: {str(e)}')
        raise Exception(f"Error: {str(e)}")