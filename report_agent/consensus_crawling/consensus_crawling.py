from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.support.ui import Select
import pandas as pd
import os
from tqdm import tqdm
from selenium.common.exceptions import TimeoutException

# KOSPI 종목 리스트 불러오기
kospi_df = pd.read_csv('report_agent/consensus_crawling/kospi_list.csv')

# 결과를 저장할 파일 경로
result_file = 'report_agent/consensus_crawling/consensus_result.csv'

# 이미 수집된 데이터가 있다면 불러오기
if os.path.exists(result_file):
    result_df = pd.read_csv(result_file)
    # 이미 수집된 종목코드 리스트
    completed_codes = result_df['종목코드'].astype(str).tolist()
    print(f"이미 수집된 종목 수: {len(completed_codes)}")
else:
    result_df = pd.DataFrame(columns=['종목코드', '종목명', '직전분기_매출액_컨센서스'])
    completed_codes = []
    print("새로운 데이터 수집을 시작합니다.")

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--headless')  # 헤드리스 모드 활성화
    return webdriver.Chrome(options=options)

def get_consensus_batch(driver, code, company_name):
    try:
        wait = WebDriverWait(driver, 5)  # 타임아웃 시간 단축
        
        # 네이버 금융 메인 페이지로 이동
        driver.get("https://finance.naver.com/")
        
        # 검색창에 종목코드 입력
        search_input = wait.until(EC.presence_of_element_located((By.ID, "stock_items")))
        search_input.clear()
        search_input.send_keys(code)
        
        # 첫 번째 결과 클릭
        first_result = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a._au_real_list")))
        first_result.click()
        
        # 종목분석 탭 클릭
        analysis_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.tab6")))
        analysis_tab.click()
        
        # iframe 전환
        iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#coinfo_cp")))
        driver.switch_to.frame(iframe)
        
        # 컨센서스 링크 클릭
        consensus_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '컨센서스')]")))
        consensus_link.click()
        
        driver.switch_to.default_content()
        
        # iframe 다시 전환
        iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#coinfo_cp")))
        driver.switch_to.frame(iframe)
        
        # 분기 탭 클릭
        quarter_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#tab_Sup2")))
        quarter_tab.click()
        
        # 매출액 선택
        select_element = wait.until(EC.presence_of_element_located((By.ID, "itemSupItem")))
        select = Select(select_element)
        select.select_by_value("121000")
        
        # 검색 버튼 클릭
        search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[onclick*='conGubun3']")))
        search_button.click()
        
        # 결과 가져오기
        time.sleep(0.5)  # 최소한의 대기 시간
        rows = driver.find_elements(By.CSS_SELECTOR, "tr")
        expected_value = None
        
        for row in rows:
            try:
                header = row.find_element(By.CSS_SELECTOR, "th.c0")
                if "발표직전(E)" in header.text:
                    value_cell = row.find_element(By.CSS_SELECTOR, "td.c5.line.num")
                    expected_value = float(value_cell.text.replace(',', ''))
                    break
            except:
                continue
                
        return expected_value
        
    except TimeoutException:
        tqdm.write(f"\n시간 초과 ({code} - {company_name})")
        return None
    except Exception as e:
        tqdm.write(f"\n오류 발생 ({code} - {company_name}): {e}")
        return None

# 남은 작업 계산
remaining_df = kospi_df[~kospi_df['종목코드'].astype(str).isin(completed_codes)]
total_remaining = len(remaining_df)

# 드라이버 초기화 (한 번만 실행)
driver = setup_driver()

try:
    # 메인 실행 코드
    for idx, row in tqdm(remaining_df.iterrows(), total=total_remaining, desc="컨센서스 수집 진행률"):
        code = str(row['종목코드']).zfill(6)
        
        tqdm.write(f"처리 중: {code} - {row['종목명']}")
        consensus_value = get_consensus_batch(driver, code, row['종목명'])
        
        # 결과 데이터프레임에 추가
        new_row = {
            '종목코드': code,
            '종목명': row['종목명'],
            '직전분기_매출액_컨센서스': consensus_value
        }
        result_df.loc[len(result_df)] = new_row
        
        # 매 10개 종목마다 결과 저장
        if idx % 10 == 0:
            result_df.to_csv(result_file, index=False)
        
        # 최소한의 대기 시간
        time.sleep(1)

finally:
    # 마지막 저장 및 드라이버 종료
    result_df.to_csv(result_file, index=False)
    driver.quit()

print("\n모든 종목의 컨센서스 수집이 완료되었습니다.")