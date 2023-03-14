from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import time
import json
import configparser
import shelve
import logging


driver = webdriver.Chrome()
driver.maximize_window()


logging.basicConfig(level=logging.INFO, filename="logs.log",
    format="%(asctime)s %(levelname)s %(message)s", datefmt='%m.%d.%Y %H:%M:%S', encoding='utf-8')


def log(result_log, value=None):
    if result_log == 'login_yandex_pasport_result_is_good':
        logging.warning(f"login = '{value}' выполнен вход")
    elif result_log == 'login_yandex_pasport_result_is_bad':
        logging.warning(f"login = '{value}' неудалось войти под пользователем")
    elif result_log == 'authentication_check_result_is_bad':
        logging.warning(f"Аккаунт не прошел проверку на аунтификацию wordstat.yandex")
    elif result_log == 'save_result_is_good':
        logging.info(f"Статистика '{value}' записана успешно")
    elif result_log == 'save_result_is_bag':    
        logging.warning(f"Слово '{value}' не сохраненно, неивестная ошибка")
    elif  result_log == 'login_yandex_pasport_result_captcha':
        logging.warning(f"login = {value} найдена капча")
    elif  result_log == 'login_yandex_pasport_result_bad_password':
        logging.warning(f"login = {value} неверный пароль")


class Account:
    # класс получения аккаунта и выдачи следующего в случае неудачной аунтификации
    def __iter__(self):
        self.a = 1
        return self

    def __next__(self):
        config = configparser.ConfigParser() 
        config.read("settings.ini")
        section = [i for i in config] 
        x = self.a 
        self.a += 1
        
        if 0 < (len(section) - 1) >= x:
            return {'login': config[f"{section[x]}"]["login"], 
                    'password': config[f"{section[x]}"]["password"],
                    'section': section[x]}
        else:
            return False


def authentication_wordstat_yandex():
    # функция проверяет аунтификацию на wordstat.yandex.ru
    try:
        authentication_check = driver.find_element(By.XPATH, "//td[@class='b-head-userinfo__exit']")
        authentication_check = authentication_check.text == 'Выход'
        if authentication_check == True: 
            return True
    except NoSuchElementException:
        log('authentication_check_result_is_bad')
        return False
    
    
def authentication_passport_yandex():
    # функция проверяет аунтификацию на passport.yandex.ru
    if 'https://id.yandex.ru/' in driver.current_url:
        return True
    else:
        return False
       
        
def login_yandex_pasport(account_data):
    # аунтификация на passport.yandex.ru
    driver.get('https://passport.yandex.ru/') 
    
    # открываем сохранённые coockie и проверям наличие
    with shelve.open('cookies') as states:
        account_data_has_coockie = account_data['section'] in states
        # если есть coockie к выбранному аккаунту, то добавляем   
        if account_data_has_coockie is True:
            for cookie in states[account_data['section']]:
                driver.add_cookie(cookie)
            driver.get('https://passport.yandex.ru/') 
            time.sleep(2)
            return authentication_passport_yandex() == True

        # иначе логинемся          
        elif account_data_has_coockie is False:
            try:
                time.sleep(1)
                driver.find_element(By.XPATH, "//div[@class='AuthLoginInputToggle-wrapper AuthLoginInputToggle-wrapper_theme_default']//button[@data-type='login']").click()
                time.sleep(1) 
                search_entry = driver.find_element(By.ID, 'passp-field-login')
                search_entry.send_keys(account_data['login'] + Keys.ENTER)
                time.sleep(1)
                search_password = driver.find_element(By.ID, 'passp-field-passwd')
                search_password.send_keys(account_data['password'] + Keys.ENTER)
                
                # записываем coockie для залогиненного аккаунта
                time.sleep(2)
                if authentication_passport_yandex() == True:
                    with shelve.open('cookies') as states:
                        states[account_data['section']] = driver.get_cookies()
                    return True 
                else:
                    log('login_yandex_pasport_result_is_bad', account_data['login'])
                    return False
            except:
                #ищем уведомления о неудачном входе (неверный пароль, капча)
                
                # if  driver.find_element(By.XPATH, "//div[@class='captcha__container']"):
                #     log('login_yandex_pasport_result_captcha')
                # if  driver.find_element(By.ID, 'field:input-passwd:hint'):
                #     log('login_yandex_pasport_result_bad_password')
                return False


def search_wordstat(wordstat):
    # функция поиска статистики по слову и получения статистики
    # возвращает словарь с результатами
    dictionary_stats = {} 
    dictionary_similar_stats = {} 
    driver.get('https://wordstat.yandex.ru/') 
    # проверяем авторизацию, если авторизованны приступаем к поиску
    if authentication_wordstat_yandex() == True:
        time.sleep(2)
        search_input = driver.find_element(By.CLASS_NAME, "b-form-input__input")
        search_input.send_keys(str(wordstat) + Keys.ENTER) 
        driver.find_element(By.XPATH, "//input[@class='b-form-button__input']").click()
        time.sleep(4)
        stats_word = driver.find_elements(By.XPATH, "//div[@class='b-word-statistics__column b-word-statistics__including-phrases'][1]//td[@class='b-word-statistics__td b-word-statistics__td-phrase']")
        stats_count = driver.find_elements(By.XPATH, "//div[@class='b-word-statistics__column b-word-statistics__including-phrases'][1]//td[@class='b-word-statistics__td b-word-statistics__td-number']")
        similar_stats_word = driver.find_elements(By.XPATH, "//div[@class='b-word-statistics__column b-word-statistics__phrases-associations'][1]//td[@class='b-word-statistics__td b-word-statistics__td-phrase']")
        similar_stats_count = driver.find_elements(By.XPATH, "//div[@class='b-word-statistics__column b-word-statistics__phrases-associations'][1]//td[@class='b-word-statistics__td b-word-statistics__td-number']")
        
        for word, number in zip(stats_word, stats_count):
            dictionary_stats[word.text] = number.text
        for word, number in zip(similar_stats_word, similar_stats_count):
            dictionary_similar_stats[word.text] = number.text
        search_input.clear()
        return {'word_stats': dictionary_stats, 'word_similar_stats': dictionary_similar_stats}
    else:
        log('authentication_check_result_is_bad')


def save_result(word, result):
    # сохранение результатов в два файла
    if not result['word_stats']:
        result['word_stats'] = {f'{word}': 'Данные по отсутствуют'}
    if not result['word_similar_stats']:
        result['word_similar_stats'] = {f'{word}': 'Данные по отсутствуют'}
    try:
        with open(f'Статистика по словам {word}.json', 'w', encoding='utf-8',) as fp:
            json.dump(result['word_stats'], fp, ensure_ascii=False, indent=4)
        with open(f'Запросы, похожие на {word}.json', 'w', encoding='utf-8',) as fp:
            json.dump(result['word_similar_stats'], fp, ensure_ascii=False, indent=4)
        log('save_result_is_good', word)
    except:
        log('save_result_is_bad', word)
        

def service(words, account_data):
    login = login_yandex_pasport(account_data)      
    if login == True:
        log('login_yandex_pasport_result_is_good', account_data['login'])
        for word in words:
            result = search_wordstat(word)
            save_result(word, result)     
    elif login == False:
        hello_yandex_words(words, next(myiter))


myclass = Account()
myiter = iter(myclass)  
def hello_yandex_words(words, account_data = next(myiter)):
    service(words, account_data)
