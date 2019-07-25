import requests, os
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time, bs4, sys, sqlite3



options = webdriver.FirefoxOptions()
options.headless = False
driver = webdriver.Firefox()

url = 'https://www.dns-shop.ru/catalog/markdown/'
city_list = ['Красноярск']

def choose_city(town):
    driver.get(url)

    # Кликаем на выбор города
    driver.find_element_by_xpath\
        ('/html/body/header/div[2]/div/div[1]/ul[1]/li[1]/div/div[2]/a[2]').click() # Сделать нормальный xpath

    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//div[@class="search-field"]/input')))
    search_field = driver.find_element_by_xpath('//div[@class="search-field"]/input')
    search_field.send_keys(town) # Долго думает перед переходом. Если будет время, подумать как ускорить
    driver.find_element_by_link_text(town).click()

    WebDriverWait(driver, 30).until(EC.text_to_be_present_in_element(
        (By.XPATH, '//div[@class="navbar-menu"]/div/div/ul/li/div/div'), town))
    driver.get(url)
    soup = bs4.BeautifulSoup(driver.page_source, 'lxml')
    count_of_items = soup.find('div', class_='page-content-container').find('span').get_text().strip().replace(' ', '')
    count_of_items = int(count_of_items[:count_of_items.find('товар')])
    count_of_pages = (count_of_items - 20) // 20 if (count_of_items - 20) % 20 == 0 else (count_of_items - 20) // 20 + 1

    return count_of_pages # число страниц, начиная со второй



# Узнать, сколько раз мне получать данные страниц
# Выдавать правильный url




def data_to_base(page_url): # Получаем данные для базы с одной страницы
    driver.get(page_url)
    soup = bs4.BeautifulSoup(driver.page_source, 'lxml')
    # Обновление инфы об общем числе товаров
    count_of_items = soup.find('div', class_='page-content-container').find('span').get_text().strip().replace(' ', '')
    count_of_items = int(count_of_items[:count_of_items.find('товар')])
    count_of_pages = (count_of_items - 20) // 20 if (count_of_items - 20) % 20 == 0 else (count_of_items - 20) // 20 + 1

    list_of_blocks = soup.find_all('div', class_='product')
    data_to_base = []

    for block in list_of_blocks:
        name = block.find('div', class_='item-name').find('a').get_text()
        link = 'https://www.dns-shop.ru' + block.find('div', class_='item-name').find('a').get('href')

        curr_price = int(block.find('div', class_='price_g').find('span').get_text().replace(' ', ''))

        try:
            old_price = int(block.find('div', class_='markdown-price-old').get_text().replace(' ', ''))
            diff = old_price - curr_price
        except AttributeError:
            old_price = None
            diff = None

        id = link[41:-1]

        data_to_base.append(
            (id, name, link, old_price, curr_price, diff))

    return data_to_base, count_of_pages



def update_base(data, name_of_table):
    conn = sqlite3.connect("markdown_base.db")  # или :memory: чтобы сохранить в RAM
    cursor = conn.cursor()

    try:
        # Создание таблицы
        cursor.execute(f"""CREATE TABLE {name_of_table}
                              (id text PRIMARY KEY, name text, link text, old_price integer,
                               curr_price integer, diff integer)
                           """)

        # Вставляем данные в таблицу
        cursor.executemany(f"INSERT INTO {name_of_table} VALUES (?,?,?,?,?,?)", data)

    except sqlite3.OperationalError:
        pass


    cursor.execute(f"SELECT id, curr_price FROM {name_of_table}")

    id_list = cursor.fetchall()

    count_of_update = 0
    count_of_insert = 0

    markdown_list = []
    new_item_list = []

    for data_id in data:
        for table_data in id_list:
            if data_id[0] == table_data[0]: # сравнивается строка новых данных (data_id) с каждой строкой из таблицы
                if data_id[4] != table_data[1]:
                    cursor.execute(f"UPDATE {name_of_table} SET old_price=?, curr_price=?, diff=? WHERE id=?",
                                   (data_id[3], data_id[4], data_id[5], data_id[0]))
                    markdown_list.append(data_id)
                    count_of_update += 1
                    break
                else: break

        if data_id[0] != table_data[0]:
            cursor.execute(f"INSERT INTO {name_of_table} VALUES (?,?,?,?,?,?)", data_id)
            new_item_list.append(data_id)
            count_of_insert += 1

    print('Добавлено ' + str(count_of_insert) + '.\nОбновлено ' + str(count_of_update) + '.')
    print(new_item_list)
    print(markdown_list)

    # Сохраняем изменения
    conn.commit()
    conn.close()

    return new_item_list, markdown_list





def get_city_data(city):
    count_of_pages = choose_city(city)

    for i in range(count_of_pages + 1):

        if i == 0:
            page_url = url
        else:
            page_url = url + '?offset=' + str(i * 20)

        data, count_of_pages = data_to_base(page_url) # получаем данные для базы
        update_base(data, city) # запись в базу




def main():
    for city in city_list:
        get_city_data(city)



if __name__ == '__main__':
    main()


