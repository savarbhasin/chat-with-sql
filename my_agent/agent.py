from my_agent.utils.state import AgentState
from langgraph.graph import StateGraph, END
from my_agent.utils.nodes import get_curr_user, check_relevance, convert_question_to_sql, execute_sql, sql_to_human_readable, rewritten_question, not_relevant_response, end_iteration, relevance_route,check_error,check_attempts


workflow = StateGraph(AgentState)



workflow.add_node("get_curr_user", get_curr_user)
workflow.add_node("check_relevance", check_relevance)
workflow.add_node("convert_to_sql", convert_question_to_sql)
workflow.add_node("execute_sql", execute_sql)
workflow.add_node("sql_to_human_readable", sql_to_human_readable)
workflow.add_node("rewritten_question", rewritten_question)
workflow.add_node("not_relevant_response", not_relevant_response)
workflow.add_node("end_iteration", end_iteration)

workflow.add_edge("get_curr_user", "check_relevance")
workflow.add_conditional_edges("check_relevance", relevance_route,
        {"convert_to_sql": "convert_to_sql", 
         "not_relevant_response": "not_relevant_response"}
    )

workflow.add_edge("convert_to_sql", "execute_sql")
workflow.add_conditional_edges("execute_sql", check_error,
                  {
                      "rewritten_question": "rewritten_question",
                    "sql_to_human_readable": "sql_to_human_readable"
                  })
workflow.add_conditional_edges("rewritten_question", check_attempts,{
    "end_iteration": "end_iteration",
    "convert_to_sql": "convert_to_sql"
})

workflow.add_edge("sql_to_human_readable", END)
workflow.add_edge("not_relevant_response", END)
workflow.add_edge("end_iteration", END)

workflow.set_entry_point("get_curr_user")

app = workflow.compile()