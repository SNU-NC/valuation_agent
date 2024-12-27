from yahooquery import search
from deep_translator import GoogleTranslator
from typing import List
import pandas as pd

# 한글 문자 범위를 이용해 한글 포함 여부 확인
def _contains_korean(text):
    for char in text:
        if '\uac00' <= char <= '\ud7a3' or '\u3131' <= char <= '\u318e':
            return True
    return False

def get_ticker(company_name):
    try:            
        # 한글 포함 여부 확인
        is_korean = _contains_korean(company_name)
        if is_korean:
            # 회사명을 영어로 번역
            translated = GoogleTranslator(source='auto', target='en').translate(company_name)
            
            # 번역된 이름으로 검색
            results = search(translated)
        else:
            results = search(company_name)
            
        # KSC, NYSE, NASDAQ, AMEX, JPX, HKG 순서로 찾기
        for quote in results['quotes']:
            if quote['exchange'] == 'KSC': # 한국
                return quote['symbol'].split(".")[0]
            elif quote['exchange'] == 'NYQ': # NYSE
                return quote['symbol'].split(".")[0]
            elif quote['exchange'] == 'NMS': # NASDAQ
                return quote['symbol'].split(".")[0]
            elif quote['exchange'] == 'JPX': # 일본
                return quote['symbol'].split(".")[0]
            elif quote['exchange'] == 'HKG': # 홍콩
                return quote['symbol'].split(".")[0]
            else:
                continue
        
        # KSC, NYSE, NASDAQ, AMEX에 없으면 None 반환
        return None
    except Exception as e:
        print(f"Error translating or searching for {company_name}: {e}")
        return None
    
def extract_segment(income_stmt_cum: pd.DataFrame) -> List[str]:
    segments = []
    for item in income_stmt_cum.iloc[:, 0]:
        if item == '영업수익':
            break
        segments.append(item)
    return segments

def yoy_calculator(income_stmt_cum: pd.DataFrame) -> pd.Series:
    present_quarter = income_stmt_cum.iloc[:,1+4]
    year_ago_quarter = income_stmt_cum.iloc[:,1]
    yoy = ((present_quarter - year_ago_quarter) / year_ago_quarter) * 100
    return yoy