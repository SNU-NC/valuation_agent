import os
import re
from datetime import datetime
import OpenDartReader
import pandas as pd
from urllib.request import urlopen
from bs4 import BeautifulSoup
from io import StringIO
from langchain_core.documents import Document
from langchain_community.embeddings import ClovaXEmbeddings
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain.output_parsers import CommaSeparatedListOutputParser
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class DartAPIClient:
    """DART API 관련 기능을 처리하는 클래스"""
    
    def __init__(self, api_key):
        self.dart = OpenDartReader(api_key)
        self.current_year = datetime.now().year
    
    def get_corp_code(self, company_name):
        """회사 코드 조회"""
        return self.dart.find_corp_code(self.dart.find_corp_code(company_name))
    
    def get_reports(self, corp_code, start_date=None):
        """보고서 목록 조회"""
        if start_date is None:
            start_date = f'{self.current_year-1}-01-01'
        
        results = self.dart.list(corp_code, start=start_date, kind='A')
        return results.sort_values('rcept_dt', ascending=True)
    
    def get_report_urls(self, filtered_df):
        """보고서 URL 목록 조회"""
        rcept_no_list = list(zip(filtered_df['rcept_no'], filtered_df['report_nm']))
        return [(rcept_no, report_nm, self.dart.sub_docs(rcept_no, '매출 및 수주상황').iloc[0]['url']) 
                for rcept_no, report_nm in rcept_no_list]

class ReportFilter:
    """보고서 필터링 관련 기능을 처리하는 클래스"""
    
    @staticmethod
    def filter_annual_reports(sorted_df):
        """1년치 보고서 필터링"""
        def filter_reports(row):
            latest_report = sorted_df.iloc[-1]['report_nm']
            latest_year = int(re.search(r'\((\d{4})', latest_report).group(1))
            latest_month = int(re.search(r'\.(\d{2})', latest_report).group(1))
            
            year_match = re.search(r'\((\d{4})', row['report_nm'])
            if year_match:
                report_year = int(year_match.group(1))
                report_month = int(re.search(r'\.(\d{2})', row['report_nm']).group(1))
                
                if report_year == latest_year - 1:
                    return report_month >= latest_month
                elif report_year == latest_year:
                    return report_month <= latest_month
                return False
            return False
        
        return sorted_df[sorted_df.apply(filter_reports, axis=1)]

class TableExtractor:
    """HTML 테이블 추출 관련 기능을 처리하는 클래스"""
    
    def __init__(self):
        self.embeddings = ClovaXEmbeddings(
            service_app=True,
            model_name="v2",
            timeout=60
        )
        self.embeddings_filter = EmbeddingsFilter(
            embeddings=self.embeddings,
            k=1
        )
    
    def extract_tables_from_url(self, url):
        """URL에서 테이블 추출"""
        with urlopen(url) as response:
            html_content = response.read().decode('utf-8')
        
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table', border='1')
        
        documents = []
        url_table_df = []
        
        for idx, table in enumerate(tables, 1):
            prev_element = table.find_previous_sibling('table', class_='nb')
            unit_info = prev_element.get_text().strip() if prev_element else "정보 없음"
            unit_info = unit_info.replace("(", "").replace(")", "").replace("단위", "").replace(":", "")
            
            title_element = table.find_previous_sibling('p')
            title = title_element.get_text().strip() if title_element else f"Table {idx}"
            
            html_string = StringIO(str(table))
            df = pd.read_html(html_string)[0]
            url_table_df.append(df)
            
            content = f"제목: {title}\n단위: {unit_info}\n\n{df.to_string()}"
            metadata = {
                'title': title,
                'unit': unit_info,
                'table_index': idx-1
            }
            
            documents.append(Document(
                page_content=content[:3000],
                metadata=metadata
            ))
        
        return documents, url_table_df
    
    def filter_relevant_tables(self, documents):
        """관련 테이블 필터링"""
        if not documents:
            return None
        return self.embeddings_filter.compress_documents(
            documents=documents,
            query="사업부문별 영업실적. 부분 매출유형 품목"
        )

class DataFrameProcessor:
    """데이터프레임 처리 관련 기능을 처리하는 클래스"""
    
    @staticmethod
    def create_result_template(base_df, report_names):
        """결과 템플릿 생성"""
        first_column = base_df.iloc[:, 0]
        first_column = first_column.dropna()
        unique_items = first_column.unique()
        
        template_rows = []
        for item in unique_items:
            row_dict = {'계정': item}
            if not report_names.empty:
                for report_name in report_names:
                    row_dict[report_name] = 0
            template_rows.append(row_dict)
        
        return pd.DataFrame(template_rows)

class FinancialAnalyzer:
    """재무 데이터 분석을 총괄하는 메인 클래스"""
    
    def __init__(self, dart_api_key):
        self.dart_client = DartAPIClient(dart_api_key)
        self.table_extractor = TableExtractor()
        self.llm = ChatOpenAI(temperature=0)
        self.parser = CommaSeparatedListOutputParser()
    
    def create_analysis_chain(self):
        """분석용 LLM 체인 생성"""
        prompt_template = """
        주어진 테이블 데이터에서 사업 부문별 ({partition_list}) 가장 최근 분기 및 기수의 값들을 추출하여 숫자만으로 구성된 리스트를 생성해주세요.

        추출 방법:
        1. 테이블에서 각 사업 부문의 행을 찾습니다
        2. 가장 오른쪽 열(최근 기수)의 값을 확인합니다
        3. 각 부문별 숫자를 partition_list의 순서대로 배열합니다

        예시1:
        사업 부문 예시: [DS부문, SX부문, SDC, 기타]
        출력: [1304441, 449021, 213158, 159705]

        예시2:
        사업 부문 예시: [충당금적립전이익, 제충당금전입액, 제충당급환입액, 범인세비용]
        출력: [250000, 25000, 275000, 329999]

        테이블 데이터:
        {table_data}
        
        {format_instructions}
        
        반드시 partition_list의 순서대로 숫자만 추출하여 쉼표로 구분된 리스트를 생성해주세요.
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["partition_list", "table_data"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        return LLMChain(llm=self.llm, prompt=prompt)
    
    def analyze_company(self, company_name):
        """회사 재무 데이터 분석 실행"""
        # 회사 코드 조회
        corp_code = self.dart_client.get_corp_code(company_name)
        
        # 보고서 조회 및 필터링
        reports_df = self.dart_client.get_reports(corp_code)
        filtered_df = ReportFilter.filter_annual_reports(reports_df)
        
        # 보고서 URL 조회
        report_urls = self.dart_client.get_report_urls(filtered_df)
        for rcept_no, report_nm, url in report_urls:
            print(f"보고서: {report_nm}")
            print (f"URL: {url}\n" )
        
        # 테이블 처리
        filtered_tables_idx = []
        total_tables = []
        total_table_df = []
        
        for _, _, url in report_urls:
            tables, url_table_df = self.table_extractor.extract_tables_from_url(url)
            total_tables.append(tables)
            total_table_df.append(url_table_df)
            
            if tables:
                filtered_tables = self.table_extractor.filter_relevant_tables(tables)
                if filtered_tables:
                    filtered_tables_idx.append(filtered_tables[0].metadata['table_index'])
        
        # 결과 데이터프레임 생성
        col_names = filtered_df['report_nm'].str.replace("[기재정정]", "").str.replace("(", "").str.replace(")", "")
        base_df = total_table_df[0][filtered_tables_idx[0]]
        result_df = DataFrameProcessor.create_result_template(base_df, col_names)
        
        # 데이터 추출 및 결과 데이터프레임 업데이트
        chain = self.create_analysis_chain()
        partition_list = list(result_df.iloc[:, 0])
        
        for i in range(len(filtered_tables_idx)):
            dest_df = total_table_df[i][filtered_tables_idx[i]]
            try:
                response = chain.invoke({
                    'partition_list': partition_list,
                    "table_data": dest_df.to_string()
                })
                parsed_values = self.parser.parse(response['text'])
                for row_idx in range(min(len(parsed_values), len(result_df))):
                    try:
                        numeric_value = float(str(parsed_values[row_idx]).replace(',', ''))
                        result_df.loc[row_idx, col_names[i]] = numeric_value
                    except ValueError as ve:
                        print(f"숫자 변환 실패 ({parsed_values[row_idx]}): {ve}")
                
                if len(parsed_values) > len(result_df):
                    print(f"경고: {len(parsed_values) - len(result_df)}개의 추가 값이 무시되었습니다.")
                    
            except Exception as e:
                print(f"처리 에러 ({col_names[i]}): {e}")
        
        result_df['단위'] = total_tables[0][filtered_tables_idx[0]].metadata['unit']
        return result_df

def main():
    """메인 실행 함수"""
    DART_API_KEY = "4925a6e6e69d8f9138f4d9814f56f371b2b2079a"
    
    analyzer = FinancialAnalyzer(DART_API_KEY)
    company_name = input("분석할 회사 이름을 입력하세요: ")
    result = analyzer.analyze_company(company_name)
    print("\n분석 결과:")
    print(result)

if __name__ == "__main__":
    main() 