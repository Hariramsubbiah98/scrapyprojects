import scrapy
import os
import json
import re
from sqlalchemy.orm import sessionmaker
from models import Product, db_connect, create_table

class KengoSpider(scrapy.Spider):
    name = "kengos"

    def __init__(self, *args, **kwargs):
        super(KengoSpider, self).__init__(*args, **kwargs)
        engine = db_connect()
        create_table(engine)
        self.Session = sessionmaker(bind=engine)

    def start_requests(self):
        try:
            with open('input.txt', 'r') as file:
                urls = [line.strip() for line in file if line.strip()]
            
            for index, url in enumerate(urls, start=1):
                yield scrapy.Request(url=url, callback=self.parse, meta={'page_number': index})
        except FileNotFoundError:
            self.log("input.txt file not found")
        except Exception as e:
            self.log(f"Error reading input.txt: {e}")

    def parse(self, response):
        product_title = response.xpath('//*[@id="shopify-section-template--17031766376671__main"]/div/div/safe-sticky/h1/text()').get()
        script_content = response.xpath('//script[contains(text(), \'@type": "Product\')]/text()').get()
        
        product_data = {
            'title': product_title,
            'product_id': 'Unknown ID',
            'sku': None,
            'gtin': []
        }

        if script_content:
            try:
                start_index = script_content.find('{')
                end_index = script_content.rfind('}') + 1
                json_str = script_content[start_index:end_index]
                json_data = json.loads(json_str)

                product_data['product_id'] = json_data.get('productID', 'Unknown ID')
                product_data['sku'] = json_data.get('sku')

                if 'offers' in json_data:
                    for offer in json_data['offers']:
                        product_data['gtin'].append(offer.get('gtin'))

            except json.JSONDecodeError:
                self.log("Error decoding JSON from script content")
        else:
            self.log("JSON data not found in the script tag")

        self.log(f"Extracted product data: {product_data}")

        self.save_to_db(product_data)
        
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", product_title)

        os.makedirs('cache', exist_ok=True)
        html_filename = f"cache/page_{response.meta['page_number']}.html"
        
        with open(html_filename, 'wb') as fh:
            fh.write(response.body)
        
        self.log(f"Saved HTML file {html_filename}")

        os.makedirs('output', exist_ok=True)
        json_filename = f"output/{sanitized_title}.json"
        
        with open(json_filename, 'w', encoding='utf-8') as fh:
            json.dump(product_data, fh, ensure_ascii=False, indent=4)
        
        self.log(f"Saved JSON file {json_filename}")

    def save_to_db(self, data):
        session = self.Session()
        try:
            for gtin in data['gtin']:
                product = Product(
                    title=data['title'],
                    product_id=data['product_id'],
                    sku=data['sku'],
                    gtin=gtin
                )
                session.add(product)
            session.commit()
        except Exception as e:
            session.rollback()
            self.log(f"Error saving to database: {e}")
        finally:
            session.close()
