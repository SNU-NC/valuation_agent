from langgraph.prebuilt import create_react_agent
from datetime import datetime
from my_agent.utils.tools import tools
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm.bind_tools(tools)

today = datetime.now().strftime("%Y-%m-%d")

prompt = f"""항상 {today}를 기준으로 확인 및 예상합니다.
기업의 매출을 책임지는 주요 사업부 리스트와 주요 사업부의 수익 창출 방법 설명 그리고 그 사업부의 매출 비중을 확인.
사업부별로 매출이나 이익에 주요한 영향을 미칠 수 있는 뉴스(사업부 관련 뉴스)를 확인.
한국 경제에 영향을 미치기 때문에 사업부 매출과 이익에 영향을 줄 수 있는 거시 경제 관련 뉴스(거시 경제 뉴스)를 확인.
한국 경제 혹은 기업에 영향을 미치기 때문에 사업부 매출과 이익에 영향을 줄 수 있는 정치 관련 뉴스(정치 뉴스)를 확인.
사업부 관련 뉴스, 거시 경제 뉴스, 정치 뉴스를 기반으로 사업부별 매출을 예상.
예상한 사업부별 매출을 기반으로 기업의 목표 PER을 설정
(사업부별 매출이 좋을 것으로 예상되거나, 매출 성장 가능성이 높으면 목표 PER을 높게 설정,
사업부별 매출이 나쁠 것으로 예상되거나, 매출 성장 가능성이 낮으면 목표 PER을 낮게 설정,
현재 PER보다 peer PER이 너무 높거나 낮으면 peer PER을 고려하지 않고 목표 PER을 설정,
peer PER 평균을 목표 PER과 같이 보여주기, 
peer PER 평균을 이루는 peer가 어떤 기업인지 항상 명시).
목표 PER을 현재 PER과 비교.
목표 PER을 현재 EPS를 곱하여 목표 주가를 설정.
목표 주가를 어제 종가와 비교.
모든 정보를 토대로 기업의 가치를 평가하고 투자의견 제시.
투자의견을 제시할 때 목표주가와 어제 종가의 차이가 크지 않다면 '보류'라고 제시.
"""

graph = create_react_agent(llm, tools=tools,state_modifier=prompt)


