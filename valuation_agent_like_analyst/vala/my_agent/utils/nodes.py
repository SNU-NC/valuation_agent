from my_agent.utils.tools import tools

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

llm.bind_tools(tools)