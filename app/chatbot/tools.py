import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch

load_dotenv()

# Best practice: limit results to keep context window clean
tavily_tool = TavilySearch(
  tavily_api_key=os.getenv("TAVILY_API_KEY"),
  max_results=3
)
tools = [tavily_tool]
