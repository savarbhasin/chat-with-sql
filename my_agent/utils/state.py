from typing_extensions import TypedDict

class AgentState(TypedDict):
    sql_query: str
    question:str
    user_id: str
    query_rows: int
    attempts: int
    relevance: str
    sql_error:bool
    result: str
