from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import json
import sys
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import urllib.request

proxy_support = urllib.request.ProxyHandler({'http': 'http://brd-customer-hl_ef20981d-zone-web_unlocker_test:r8yjzk22g9ep@brd.superproxy.io:22225',
                                             'https': 'http://brd-customer-hl_ef20981d-zone-web_unlocker_test:r8yjzk22g9ep@brd.superproxy.io:22225'})
opener = urllib.request.build_opener(proxy_support)
urllib.request.install_opener(opener)

def convert_date(date_str):
    date_object = datetime.strptime(date_str, "%d %b %Y")
    return date_object.strftime("%Y-%m-%d")

result = {
    "ticker_code" : [],
    "company" : [],
    "listing_date" : [],
    "price" : [],
    "sector" : [],
    "number_of_shares_offered" : [],
    "percent_of_total_shares" : []
}

for i in range(1,2):
    url = f'https://e-ipo.co.id/en/ipo/index?page={i}&per-page=12&query=&sort=-updated_at&status_id=5&view=list'
    with urllib.request.urlopen(url) as response:
        html = response.read()
        print(html)
    soup = BeautifulSoup(html, 'html.parser')
    names = []
    names_class = soup.find_all(class_="margin-left10 colorwhite")
    for name in names_class:
        company_name, symbol = name.get_text().replace(" Sharia", "").replace(")", "").split(' (')
        result["ticker_code"].append(symbol.replace("Closed", ""))
        result["company"].append(company_name)
    notopmargins = soup.find_all("p", class_="notopmargin")
    nobottommargins = soup.find_all(class_="nobottommargin")
    for top, bottom in zip(notopmargins, nobottommargins):
        if bottom.get_text() == "Sector": result["sector"].append(top.get_text())
        elif bottom.get_text() == "Final Price": result["price"].append(top.get_text())
        elif bottom.get_text() == "Listing Date": result["listing_date"].append(top.get_text())
        elif bottom.get_text() == "Stock Offered": result["number_of_shares_offered"].append(top.get_text())
    buttons = soup.find_all(class_="button button-3d button-small notopmargin button-rounded button-dirtygreen")
    for button in buttons:
        href = button.get("href")
        new_url = f"https://e-ipo.co.id{href}"
        with urllib.request.urlopen(new_url) as response:
            html_detail = response.read()
            soup_detail = BeautifulSoup(html_detail, 'html.parser')
            page = soup_detail.find("div", class_="panel-body panel-scroll")
            result["percent_of_total_shares"].append(page.find_all("p")[-3].get_text())

ipo = pd.DataFrame(result)
ipo['number_of_shares_offered'] = ipo['number_of_shares_offered'].str.replace(' Lot', '').str.replace(',', '', regex=True).astype(float)
ipo['price'] = ipo['price'].str.replace('IDR', '').str.replace("\xa0", "").str.replace(',', '', regex=True).astype(float)
ipo['listing_date'] = ipo['listing_date'].apply(convert_date)
ipo['listing_date'] = pd.to_datetime(ipo['listing_date'])
# today_date = datetime.now()
# ipo = ipo[ipo['listing_date'] > today_date]
ipo['listing_date'] = ipo['listing_date'].dt.strftime('%Y-%m-%d')
ipo['funded_in_idr'] = ipo['number_of_shares_offered'] * ipo['price'] * 100

ipo.to_csv("ipo.csv",index = False)

upcoming_ipo_json = ipo.to_dict(orient='records')
with open('upcoming_ipo.json', 'w') as json_file:
    json.dump(upcoming_ipo_json, json_file, indent=4)
