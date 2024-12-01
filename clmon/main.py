import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import json
import os
import sys

def load_credentials():
    try:
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            
        config_path = os.path.join(application_path, 'credentials.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config['userid'], config['password']
    except Exception as e:
        print(f"설정 파일 읽기 오류: {e}")
        return None, None

userid, password = load_credentials()
if not userid or not password:
    raise Exception("credentials.json 파일에서 인증 정보를 읽을 수 없습니다.")

options = uc.ChromeOptions()
driver = uc.Chrome(options=options)

driver.get('https://www.classting.com/')

WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "로그인")]'))).click()
WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@id="sign-in-id"]'))).click()

def send_keys_safely(element, text):
    try:
        element.clear()
        element.send_keys(text)
    except Exception as e:
        print(f"입력 오류: {e}")
        driver.execute_script("arguments[0].value = arguments[1];", element, text)

username_field = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, 'username')))
send_keys_safely(username_field, userid)

password_field = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, 'password')))
send_keys_safely(password_field, password)

WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'submit-button'))).click()

time.sleep(1)

script = 'return document.querySelector("#__NEXT_DATA__").textContent'
raw_json = driver.execute_script(script)
parsed_data = json.loads(raw_json)
access_token = parsed_data['props']['pageProps']['session']['accessToken']

print('엑세스 토큰:', access_token)

driver.get('https://ai.classting.com/subjects/5/units-with-keywords/259/keywords')

WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div/div[2]/div[2]/div[3]/div/button'))).click()

wait = WebDriverWait(driver, 10)
wait.until(lambda driver: len(driver.window_handles) > 1)

handles = driver.window_handles
driver.switch_to.window(handles[-1])

wait.until(lambda driver: 'ai.classting.com/learning-viewer/cat-assessment/' in driver.current_url)

ctab = driver.current_url
print('최종 URL:', ctab)

catid = ctab.split("cat-assessment/")[1].split("/")[0] if "cat-assessment/" in ctab else None
print('cat id: ', catid)

headers = {
    "accept": "application/json",
    "authorization": f"Bearer {access_token}",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "referer": "https://ai.classting.com/"
}

answer_mapping = {
    '170688': 's.정보 기술',
    '170692': 's.직업',
    '170694': 'm.//*[@id="root"]/div/main/div/article/section[2]/div/div/div[2]/fieldset/div/button[4]',
    '233741': 'm.//*[@id="root"]/div/main/div/article/section[2]/div/div/div[2]/fieldset/div/button[4]',
    '233745': 's.정보 기술'
}

count = 0

def solve_quiz(driver, headers, answer_mapping, catid, handles, wait):
    global count
    try:
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        response = requests.get(
            f"https://clapi.classting.com/v1/cats/{catid}/next-quiz",
            headers=headers
        )
        
        if response.status_code == 400:
            print("400 에러 발생 - 새로운 문제 세트로 전환")
            
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div[4]/button')
            )).click()
            
            time.sleep(2)
            driver.switch_to.window(handles[0])
            
            start_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '/html/body/div[2]/div/div[2]/div[2]/div[3]/div/button')
            ))
            start_button.click()
            
            time.sleep(2)
            wait.until(lambda driver: len(driver.window_handles) > 1)
            new_handles = driver.window_handles
            driver.switch_to.window(new_handles[-1])
            
            time.sleep(2)
            wait.until(lambda driver: 'ai.classting.com/learning-viewer/cat-assessment/' in driver.current_url)
            ctab = driver.current_url
            new_catid = ctab.split("cat-assessment/")[1].split("/")[0]
            print('새로운 cat id:', new_catid)
            
            return True, new_catid

        response.raise_for_status()
        quiz_data = response.json()
        
        quiz_id = str(quiz_data.get('id'))
        answer = answer_mapping.get(quiz_id, '답안을 찾을 수 없습니다')
        
        print('퀴즈 데이터:', json.dumps(quiz_data, indent=2, ensure_ascii=False))
        print('\n퀴즈 ID:', quiz_id)
        count += 1
        print(f'{count}번째 답안:', answer)
        
        if answer.startswith('m.'):
            xpath = answer[2:]
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
        elif answer.startswith('s.'):
            text_answer = answer[2:]
            input_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="question-text-field"]'))
            )
            send_keys_safely(input_field, text_answer)
        
        time.sleep(1.5)
        submit_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="paginate-submit-button"]'))
        )
        driver.execute_script("arguments[0].click();", submit_button)
        
        time.sleep(1.5)
        next_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/footer/div/button[2]'))
        )
        driver.execute_script("arguments[0].click();", next_button)
        
        return True, catid
        
    except Exception as e:
        print('오류:', e)
        return False, catid

while True:
    try:
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        success, catid = solve_quiz(driver, headers, answer_mapping, catid, handles, wait)
        if not success:
            print('풀이 중 오류 발생')
            break
        time.sleep(2)
    except Exception as e:
        print(f'예상치 못한 오류 발생: {e}')
        time.sleep(3)
        continue

driver.quit()
