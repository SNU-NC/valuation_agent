from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool
import yfinance as yf
from yahooquery import search
from deep_translator import GoogleTranslator
from langchain_openai import ChatOpenAI
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.prompts import PromptTemplate



tavily_search_tool = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=True,
    # include_domains=[...],
    # exclude_domains=[...],
    # name="...",            # overwrite default tool name
    #description="search action을 수행합니다.",     # overwrite default tool description
    # args_schema=...,       # overwrite default args_schema: BaseModel
)

# 한글 문자 범위를 이용해 한글 포함 여부 확인
def contains_korean(text):
    for char in text:
        if '\uac00' <= char <= '\ud7a3' or '\u3131' <= char <= '\u318e':
            return True
    return False

def get_ticker(company_name):
    try:            
        # 한글 포함 여부 확인
        is_korean = contains_korean(company_name)
        if is_korean:
            # 회사명을 영어로 번역
            translated = GoogleTranslator(source='auto', target='en').translate(company_name)
            
            # 번역된 이름으로 검색
            results = search(translated)
        else:
            results = search(company_name)
            
        # KSC 거래소 심볼 먼저 찾기
        for quote in results['quotes']:
            if quote['exchange'] == 'KSC':
                return quote['symbol']
        
        # KSC가 없으면 첫 번째 심볼 반환
        if results['quotes']:
            return results['quotes'][0]['symbol']
        
        return None
            
    except Exception as e:
        print(f"Error translating or searching for {company_name}: {e}")
        return None

@tool
def find_price_tool(company: str) -> str:
    """기업의 어제 종가를 찾습니다."""
    ticker = get_ticker(company)
    if ticker is None:
        return None 
    else:
        ticker = yf.Ticker(ticker)
        last_price = ticker.info["regularMarketPreviousClose"]
        return {"어제 종가":last_price}
    
@tool
def find_PER_tool(company: str) -> str:
    """기업의 현재 PER를 찾습니다."""
    ticker = get_ticker(company)
    if ticker is None:
        return None
    else:
        ticker = yf.Ticker(ticker)
        earning_ttm = 0
        for i in range(4):
            earning_ttm += ticker.quarterly_income_stmt.loc['Net Income Common Stockholders'][i]
        trailingPERttm = ticker.info["marketCap"]/earning_ttm
        return {"PER":trailingPERttm}
    
@tool
def find_EPS_tool(company: str) -> str:
    """기업의 현재 EPS을 yfinance를 통해 확인하고 계산합니다."""
    ticker = get_ticker(company)
    if ticker is None:
        return None
    else:
        ticker = yf.Ticker(ticker)
        earning_ttm = 0
        for i in range(4):
            earning_ttm += ticker.quarterly_income_stmt.loc['Net Income Common Stockholders'][i]
        EPSttm = earning_ttm/ticker.info["sharesOutstanding"]
        return {"EPS":EPSttm}


# ============================== find_peer를 위한 사전 설정 시작==============================
# find_peer 함수에 사용되는 모델
sub_llm = ChatOpenAI(model="gpt-4o", temperature=0)

response_schemas = [
    ResponseSchema(name="answer", description="사용자의 질문에 대한 답변, 파이썬 리스트 형식이어야 함."),
    ]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

# 출력 형식 지시사항을 파싱합니다.
format_instructions = output_parser.get_format_instructions()
prompt = PromptTemplate(
    # 사용자의 질문에 최대한 답변하도록 템플릿을 설정합니다.
    template="answer the users question as best as possible.\n{format_instructions}\n{question}",
    # 입력 변수로 'question'을 사용합니다.
    input_variables=["question"],
    # 부분 변수로 'format_instructions'을 사용합니다.
    partial_variables={"format_instructions": format_instructions},
)

chain = prompt | sub_llm | output_parser  # 프롬프트, 모델, 출력 파서를 연결
# ============================== find_peer를 위한 사전 설정 끝==============================

def find_peer(company: str) -> list[str]:
    prompt = PromptTemplate(
    # 사용자의 질문에 최대한 답변하도록 템플릿을 설정합니다.
    template="answer the users question as best as possible.\n{format_instructions}\n{question}",
    # 입력 변수로 'question'을 사용합니다.
    input_variables=["question"],
    # 부분 변수로 'format_instructions'을 사용합니다.
    partial_variables={"format_instructions": format_instructions},
    )
    chain = prompt | sub_llm | output_parser  # 프롬프트, 모델, 출력 파서를 연결
    peer_list = chain.invoke({"question": f"{company}와 사업구조가 비슷하고, 같은 산업 혹은 섹터에 속한 경쟁사는?"})
    return peer_list


@tool
def find_peer_PERs_tool(company: str):
    """기업과 동종 업계의 Peer Group PER 평균을 찾습니다."""
    ticker = get_ticker(company)
    peer_list = find_peer(company)['answer']
    if ticker is None:
        return None
    
    peer_pers = {}
    for peer in peer_list:
        ticker = get_ticker(peer)
        if ticker is None:
            continue
        elif ".KS" in ticker:
            ticker = yf.Ticker(ticker)
            earning_ttm = 0
            for i in range(4):
                earning_ttm += ticker.quarterly_income_stmt.loc['Net Income Common Stockholders'][i]
            trailingPERttm = ticker.info.get("marketCap")/earning_ttm
            if trailingPERttm <0 :
                continue
            peer_pers[peer] = trailingPERttm
        else:
            ticker = yf.Ticker(ticker)
            earning_ttm = 0
            for i in range(4):
                earning_ttm += ticker.quarterly_income_stmt.loc['Net Income Common Stockholders'][i]
            trailingPERttm = ticker.info.get("marketCap")/earning_ttm*0.7 # 외국 주식의 경우 PER을 30% 할인
            if trailingPERttm <0 :
                continue
            peer_pers[peer] = trailingPERttm
    
    average_peer_per = sum(peer_pers.values()) / len(peer_pers)

    return {
        "Peer PERs": peer_pers,
        "Peer list": peer_list,
        "Average Peer PER": average_peer_per
    }


tools = [tavily_search_tool, find_price_tool, find_PER_tool, find_peer_PERs_tool, find_EPS_tool]

