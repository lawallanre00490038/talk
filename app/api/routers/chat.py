import uuid
from fastapi import APIRouter, HTTPException

from app.chatbot.agent import graph
from app.chatbot.schema import ChatRequest, ChatResponse


router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  """
  Sends a message to the Llama-3 agent. 
  
  - **message**: The user's query.
  - **thread_id**: Acts as the unique **User ID** or **Session ID**. 
    If provided, the agent will remember previous context from this ID. 
    If null, a new session is created.
  """
  try:
    # thread_id allows for session-based memory
    config = {"configurable": {"thread_id": request.thread_id or str(uuid.uuid4())}}
    
    input_message = {"messages": [("user", request.message)]}
    result = await graph.ainvoke(input_message, config)
    
    # Get the final message from the history
    final_answer = result["messages"][-1].content
    
    return ChatResponse(
        response=final_answer,
        thread_id=config["configurable"]["thread_id"]
    )
  except Exception as e:
    raise HTTPException(status_status=500, detail=str(e))