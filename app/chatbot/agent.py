import os
from typing import Annotated, Literal, TypedDict
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver 
from langgraph.prebuilt import ToolNode
from .tools import tools
from dotenv import load_dotenv

load_dotenv()

# Define the state of the graph
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize the model and bind tools
llm = ChatGroq(
  api_key=os.getenv("GROQ_API_KEY"),
  model="llama-3.1-8b-instant", 
  temperature=0
)
llm_with_tools = llm.bind_tools(tools)
memory = MemorySaver()

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Routing logic: check if the LLM wants to use a tool
def route_tools(state: State) -> Literal["tools", "__end__"]:
    msg = state["messages"][-1]
    if msg.tool_calls:
        return "tools"
    return "__end__"

# Build the Graph
workflow = StateGraph(State)

workflow.add_node("agent", chatbot)
workflow.add_node("tools", ToolNode(tools))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", route_tools)
workflow.add_edge("tools", "agent") # Loop back after tool use


# Compile the graph

graph = workflow.compile(checkpointer=memory)