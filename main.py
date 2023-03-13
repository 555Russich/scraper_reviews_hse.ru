import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import openpyxl

from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import (
    ActionChains,
    ScrollOrigin
)

URLS_TO_SCRAP = {
    'requests': [
        'https://tabiturient.ru/vuzu/hse/?ysclid=le4h34qcoq776294321',
        'https://proverili.ru/moskva/niu-vshe/otzyvi?page=64',
        'https://www.spr.ru/moskva/vuzi/reviews/visshaya-shkola-ekonomiki-1025.html',
        'https://otzov-mf.ru/vshe-otzyvy-studentov/?ysclid=le4gxk8b4g227276693'
    ],
    'selenium': [
        'https://yandex.ru/maps/org/vysshaya_shkola_ekonomiki/1074710983/reviews/?ll=37.648297%2C55.753636&z=13',
        'https://yandex.ru/maps/org/niu_vshe_fakultet_kompyuternykh_nauk/198179712679/reviews/?ll=37.650026%2C55.754029&z=13',
        'https://yandex.ru/maps/org/niu_vshe_fakultet_prava/1764146603/reviews/?ll=37.650026%2C55.754029&mode=search&sll=37.650026%2C55.754029&sspn=0.120163%2C0.062925&tab=reviews&text=%D0%9D%D0%98%D0%A3%20%D0%92%D0%A8%D0%AD&z=13',
        'https://yandex.ru/maps/org/niu_vshe_fakultet_ekonomicheskikh_nauk/193095271964/reviews/?ll=37.650026%2C55.754029&mode=search&sll=37.650026%2C55.754029&sspn=0.120163%2C0.062925&tab=reviews&text=%D0%9D%D0%98%D0%A3%20%D0%92%D0%A8%D0%AD&z=13',
        'https://yandex.ru/maps/org/shkola_dizayna_niu_vshe/1765867878/reviews/?from=tabbar&ll=37.537063%2C55.765807&mode=search&sll=37.537063%2C55.765652&source=serp_navig&tab=reviews&text=%D0%BD%D0%B8%D1%83%20%D0%B2%D1%88%D1%8D&z=11',
        'https://yandex.ru/maps/org/niu_vshe_institut_kommunikatsionnogo_menedzhmenta/1293982154/reviews/?from=tabbar&ll=37.632993%2C55.761405&mode=search&sll=37.537063%2C55.765652&source=serp_navig&tab=reviews&text=%D0%BD%D0%B8%D1%83%20%D0%B2%D1%88%D1%8D&z=11',
    ]
}

DATA_SAMPLE: dict = {
    'website': None,
    'author': None,
    'faculty': None,
    'date': None,
    'views': None,
    'tonality': None,
    'rating': None,
    'likes': None,
    'dislikes': None,
    'link': None,
    'text': None,
}

HEADERS_BY_WEBSITE: dict[str, dict] = {
    'tabiturient.ru': {
        'authority': 'tabiturient.ru',
        'accept': 'text/html, */*; q=0.01',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest'
    },
    'proverili.ru': {
        'authority': 'proverili.ru',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    },
    'spr.ru': {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
    }
}


def scrap_website(url: str) -> list[dict]:
    data = []

    if url == 'https://tabiturient.ru/vuzu/hse/?ysclid=le4h34qcoq776294321':
        data_to_send = {
            'vuzid': 'hse',
            'limit': 1_000_000,
            'sortby': 3,
            'sortby2': None,
        }

        response = requests.post(
            url='https://tabiturient.ru/ajax/ajsliv.php',
            headers=HEADERS_BY_WEBSITE['tabiturient.ru'],
            data=data_to_send
        )
        assert response.status_code == 200, f'{response.status_code=}'
        soup = BeautifulSoup(response.text, 'lxml')

        for div_review in soup.find_all('div', class_='mobpadd20-2'):
            data_to_fill = DATA_SAMPLE.copy()
            data_to_fill['website'] = 'tabiturient.ru'

            divs_upper = div_review.find_all('div', 'table-cell-4')
            tds_of_first_div = divs_upper[0].find_all('td')

            smile_number = tds_of_first_div[0].find('img').get('src')[-5]
            if smile_number == '1':
                data_to_fill['tonality'] = 'Positive'
            elif smile_number == '2':
                data_to_fill['tonality'] = 'Negative'
            elif smile_number == '3':
                data_to_fill['tonality'] = 'Neutral'

            data_to_fill['author'] = tds_of_first_div[2].find('b').text.replace(':', '').strip()
            data_to_fill['views'] = int(tds_of_first_div[4].span.text.replace(' ', ''))
            data_to_fill['date'] = tds_of_first_div[-1].find('span', class_='font2').text.replace('\n', '')

            data_to_fill['faculty'] = divs_upper[1].find('b').text if divs_upper[1].find('b') else None

            data_to_fill['text'] = div_review.find(
                'div', {'style': 'text-align:justify;', "class": 'font2'}
            ).get_text().replace('...Показать полностью...', '')

            data_to_fill['likes'] = int(div_review.find('table', class_='like p10like').find('b').text)
            data_to_fill['link'] = div_review.find('a').get('href')

            data.append(data_to_fill)
    elif url == 'https://proverili.ru/moskva/niu-vshe/otzyvi?page=64':
        last_page = -1
        params = {'page': 1}

        while params['page'] != last_page + 1:
            response = requests.get(
                url='https://proverili.ru/moskva/niu-vshe/otzyvi',
                headers=HEADERS_BY_WEBSITE['proverili.ru'],
                params=params
            )
            assert response.status_code == 200, f'{response.status_code=}'
            soup = BeautifulSoup(response.text, 'lxml')

            if last_page == -1:
                last_page = int(soup.find('div', class_='paginate-block').find_all('li')[-2].get('data-page'))

            for div_review in soup.find_all('div', class_='review-item'):
                data_to_fill = DATA_SAMPLE.copy()
                data_to_fill['website'] = 'proverili.ru'

                data_to_fill['author'] = div_review.find('div', 'review-user h4').text
                data_to_fill['rating'] = len(div_review.find('div', class_='review-stars')
                                             .find_all('i', class_='fa fa-star fill'))
                data_to_fill['date'] = div_review.find('div', class_='descriptor mt-1').text
                data_to_fill['likes'] = int(div_review.find('div', {'data-type': 'like'}).text)
                data_to_fill['dislikes'] = int(div_review.find('div', {'data-type': 'unlike'}).text)
                data_to_fill['link'] = f'https://proverili.ru/moskva/niu-vshe/otzyvi?page={params["page"]}'
                data_to_fill['text'] = div_review.find('div', class_='text-read mt-2').text
                data.append(data_to_fill)

            print(f'Scrapped {len(data)} reviews | page={params["page"]} | {url=}')
            params['page'] += 1
    elif url == 'https://www.spr.ru/moskva/vuzi/reviews/visshaya-shkola-ekonomiki-1025.html':
        params = {
            'ajax': 1,
            'action': 'loadReviewsList',
            'id_firm': 1025,
            'id_net': 0,
            'page': 0
        }

        while True:
            response = requests.get(
                url='https://www.spr.ru/page/reviews/',
                headers=HEADERS_BY_WEBSITE['spr.ru'],
                params=params
            )
            assert response.status_code == 200, f'{response.status_code}'
            d = response.json()

            if d['count'] == 0:
                break

            if d.get('content'):
                soups_to_scrap = BeautifulSoup(d['content'], 'lxml')
            else:
                soups_to_scrap = [BeautifulSoup(d['positive'], 'lxml'), BeautifulSoup(d['negative'], 'lxml')]

            for soup in soups_to_scrap:
                for div_review in soup.find_all('div', {'data-review': re.compile('.+')}):
                    data_to_fill = DATA_SAMPLE.copy()
                    data_to_fill['website'] = 'spr.ru'

                    if 'reviewPositive' in div_review.get('class'):
                        data_to_fill['tonality'] = 'Positive'
                    elif 'reviewNegative' in div_review.get('class'):
                        data_to_fill['tonality'] = 'Negative'

                    data_to_fill['author'] = div_review.find('span', class_='reviewAuthor').text.strip()
                    # data_to_fill['date'] = datetime.strptime(
                    #     div_review.find('span', class_='reviewDate').text, '%d.%m.%Y'
                    # ).strftime('%d %B %Y')
                    data_to_fill['date'] = div_review.find('span', class_='reviewDate').text

                    data_to_fill['text'] = div_review.find('div', class_='reviewTitleText').text +\
                                           div_review.find('p', class_='reviewText').text
                    likes_res = re.search(
                        r'^\d+(?= Полезно)',
                        div_review.find('a', class_='reviewToDoEl like').span.text.strip()
                    )
                    if likes_res:
                        data_to_fill['likes'] = int(likes_res.group(0))
                    else:
                        data_to_fill['likes'] = 0

                    data_to_fill['link'] = 'https://www.spr.ru/page/reviews/?id_review=' + \
                                           re.search(r'(?<=\{"id":)\d+', div_review.get('data-review')).group(0)
                    data.append(data_to_fill)

            params['page'] += 1
    elif url == 'https://otzov-mf.ru/vshe-otzyvy-studentov/?ysclid=le4gxk8b4g227276693':
        response = requests.get(url)
        assert response.status_code, f'{response.status_code=}'
        soup = BeautifulSoup(response.text, 'lxml')

        for div_class in ('itric', 'neitral', 'pozitive'):
            for blockquote_review in soup.find('div', class_=div_class).find_all('blockquote'):
                data_to_fill = DATA_SAMPLE.copy()
                data_to_fill['website'] = 'otzov-mf.ru'

                if div_class == 'itric':
                    data_to_fill['tonality'] = 'Negative'
                if div_class == 'neitral':
                    data_to_fill['tonality'] = 'Neutral'
                if div_class == 'pozitive':
                    data_to_fill['tonality'] = 'Positive'

                data_to_fill['author'] = blockquote_review.p.text
                data_to_fill['text'] = blockquote_review.find_next_sibling('p').get_text()

                data_to_fill['link'] = blockquote_review.find('a').get('src') \
                    if blockquote_review.find('a') else None

                data.append(data_to_fill)
    return data


def data_to_excel(filename: str, data: list[dict]):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    columns = list(data[0].keys())
    worksheet.append(columns)

    for d in data[1:]:
        worksheet.append(list(d.values()))

    workbook.save(filename)


class Browser:
    def __init__(self):
        self.driver = self.get_driver()

    @staticmethod
    def get_driver():
        options = webdriver.ChromeOptions()
        # fake user agent
        options.add_argument(
            'user-agent=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0'
        )
        # disable web driver mode
        options.add_argument('--disable-blink-features=AutomationControlled')
        # headless mode
        # options.add_argument('--headless=new')
        # maximized window
        options.add_argument('--start-maximized')
        # upload webdriver from Chrome Driver Manager

        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

    def scrap(self, url: str):
        data = []
        self.driver.get(url)
        time.sleep(2)

        tab_reviews = self.driver.find_element(By.CLASS_NAME, "tabs-select-view__title._name_reviews")
        if tab_reviews.get_attribute('aria-selected') == 'false':
            tab_reviews.click()
            time.sleep(2)

        count_reviews_available = int(self.driver.find_elements(By.CLASS_NAME, 'tabs-select-view__counter')[1].text)
        count_reviews_detected = 0

        while count_reviews_detected != count_reviews_available:
            ActionChains(self.driver).scroll_to_element(
                self.driver.find_elements(By.CLASS_NAME, 'business-review-view__info')[-1]
            ).perform()

            ActionChains(self.driver).scroll_from_origin(
                scroll_origin=ScrollOrigin(
                    origin=self.driver.find_elements(By.CLASS_NAME, 'business-review-view__info')[-1],
                    x_offset=0,
                    y_offset=0
                ),
                delta_x=0,
                delta_y=3000
            ).perform()

            time.sleep(1)
            count_reviews_detected = len(self.driver.find_elements(By.CLASS_NAME, 'business-review-view__info'))

        faculty = self.driver.find_element(By.XPATH, '//h1[@itemprop="name"]').text

        for div_review in self.driver.find_elements(By.CLASS_NAME, 'business-review-view__info'):
            data_to_fill = DATA_SAMPLE.copy()
            data_to_fill['website'] = 'yandex.ru'
            data_to_fill['faculty'] = faculty

            ActionChains(self.driver).scroll_to_element(div_review).perform()
            data_to_fill['author'] = div_review.find_element(By.XPATH, './/span[@itemprop="name"]').text

            try:
                user_id = re.search(
                    r'(?<=user/).+$',
                    div_review.find_element(
                        By.XPATH, './/a[@class="business-review-view__user-icon"]'
                    ).get_attribute('href')
                ).group(0)
                data_to_fill['link'] = f'https://yandex.ru/web-maps/org/1074710983/reviews' \
                                       f'?reviews[publicId]={user_id}&utm_source=review'
            except (AttributeError, TypeError):
                pass

            data_to_fill['rating'] = int(float(div_review.find_element(
                By.XPATH, './/meta[@itemprop="ratingValue"]'
            ).get_attribute('content')))

            data_to_fill['date'] = datetime.fromisoformat(
                div_review.find_element(By.XPATH, './/meta[@itemprop="datePublished"]').get_attribute('content')
            ).strftime('%d.%m.%y')
            
            data_to_fill['text'] = div_review.find_element(
                By.XPATH, './/span[@class="business-review-view__body-text"]'
            ).text

            try:
                data_to_fill['likes'] = int(div_review.find_element(
                    By.XPATH, './/span[@aria-label="Поставить лайк"]/'
                              'following-sibling::div[@class="business-reactions-view__counter"]'
                ).text)
            except NoSuchElementException:
                data_to_fill['likes'] = 0

            try:
                data_to_fill['dislikes'] = int(div_review.find_element(
                    By.XPATH, './/span[@aria-label="Поставить дизлайк"]/'
                              'following-sibling::div[@class="business-reactions-view__counter"]'
                ).text)
            except NoSuchElementException:
                data_to_fill['dislikes'] = 0

            data.append(data_to_fill)
            print(f'Scraped {len(data)}/{count_reviews_available}')
        return data


def main():
    all_data = []
    browser = Browser()
    try:
        for lib, urls in URLS_TO_SCRAP.items():
            for url in urls:
                if lib == 'requests':
                    data = scrap_website(url)
                elif lib == 'selenium':
                    data = browser.scrap(url)
                all_data += data
                print(f'Scrapped {len(data)} from {url=}')
        data_to_excel('hse_reviews.xlsx', all_data)
    finally:
        browser.driver.quit()


if __name__ == '__main__':
    main()
