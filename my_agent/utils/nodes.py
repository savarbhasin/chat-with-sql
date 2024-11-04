from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from state import AgentState
from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser
from psycopg2 import pool
import os
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig


load_dotenv();

connection_string = os.getenv('DATABASE_URL')

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
connection_pool = pool.SimpleConnectionPool(1,  10,  connection_string)

if connection_pool:
    print("Connection pool created successfully")

conn = connection_pool.getconn()

# get the cursor
cur = conn.cursor()


def get_table_schema():
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cur.fetchall()
    
    schema = ""
    for table in tables:
        table_name = table[0]
        schema += f"Table: {table_name}\n"
        
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name='{table_name}'
        """)
        columns = cur.fetchall()
        
        for column in columns:
            col_name, data_type, is_nullable, col_default = column
            schema += f"  Column: {col_name} - Type: {data_type}, Nullable: {is_nullable}, Default: {col_default}\n"
        
        cur.execute(f"""
            SELECT tc.constraint_name, kcu.column_name, tc.constraint_type 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu 
            ON tc.constraint_name = kcu.constraint_name 
            WHERE tc.table_name = '{table_name}' AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
        """)
        constraints = cur.fetchall()
        
        for constraint in constraints:
            constraint_name, column_name, constraint_type = constraint
            if constraint_type == 'PRIMARY KEY':
                schema += f"  Primary Key: {column_name}\n"
            elif constraint_type == 'FOREIGN KEY':
                schema += f"  Foreign Key: {column_name} (constraint: {constraint_name})\n"
                
    return schema

def sql_to_human_readable(state: AgentState):
    sql_query = state["sql_query"]
    result = state["result"]
    query_rows = state.get("query_rows", [])
    sql_error = state["sql_error"]

    prompt = PromptTemplate.from_template("""Given a SQL query result, your job is to convert the SQL query result into a human readable format. 
                                          Make it concise and understandable.
                                          Use clear natural language.
    <sql_query>{sql_query}</sql_query>
    <query_rows>{query_rows}</query_rows>
    <result>{result}</result>
    <sql_error>{sql_error}</sql_error>
    Human Readable Result: """)
    llm = ChatOpenAI()
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"sql_query":sql_query, "query_rows":query_rows, "result":result, "sql_error":sql_error})
    state["result"] = response
    print('sql to human readable: ' + response)
    return state

class ConvertToSQL(BaseModel):
    sql_query: str = Field(description="SQL query to be executed")

def convert_question_to_sql(state:AgentState):
    question = state["question"]
    schema = get_table_schema()
    prompt = PromptTemplate.from_template("""Given a question and schema of a database, your job is to convert the question into a SQL query. <schema>{schema}</schema> <question>{question}</question> SQL Query:""")
    structured_llm= ChatOpenAI().with_structured_output(ConvertToSQL)
    chain = prompt | structured_llm 
    response = chain.invoke({"question":question, "schema":schema})
    state["sql_query"] = response.sql_query
    print('Converting question to SQL: ' + response.sql_query)
    return state

def execute_sql(state: AgentState):
    sql_query = state["sql_query"].strip()
    try:
        formatted_res = ""
        
        if sql_query.lower().startswith("select"):
            cur.execute(sql_query)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            
            if rows:
                state["query_rows"] = [dict(zip(cols, row)) for row in rows]
                formatted_res = "\n".join([str(row) for row in state["query_rows"]])
            else:
                state["query_rows"] = []
                formatted_res = "No rows found"
        
        # Non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
        else:
            cur.execute(sql_query)
            conn.commit()  
            state["query_rows"] = 0  
            formatted_res = f"Query executed successfully. Affected rows: {cur.rowcount}"

        state["result"] = formatted_res
        state["sql_error"] = False

    except Exception as e:
        print("Exception while running:", str(e))  
        state["result"] = f"Error executing query: {str(e)}"
        state["sql_error"] = True

    return state

def sql_to_human_readable(state: AgentState):
    sql_query = state["sql_query"]
    result = state["result"]
    query_rows = state.get("query_rows", [])
    sql_error = state["sql_error"]

    prompt = PromptTemplate.from_template("""Given a SQL query result, your job is to convert the SQL query result into a human readable format. 
                                          Make it concise and understandable.
                                          Use clear natural language.
    <sql_query>{sql_query}</sql_query>
    <query_rows>{query_rows}</query_rows>
    <result>{result}</result>
    <sql_error>{sql_error}</sql_error>
    Human Readable Result: """)
    llm = ChatOpenAI()
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"sql_query":sql_query, "query_rows":query_rows, "result":result, "sql_error":sql_error})
    state["result"] = response
    print('sql to human readable: ' + response)
    return state

def get_curr_user(state:AgentState, config:RunnableConfig):
    user_id = config["configurable"].get("session_id", None)
    if(user_id is None):
        state["user_id"] = "No user found"
        print("Specify user id in config")
        return state
    state["user_id"] = user_id
    return state

    from langgraph.graph import StateGraph, END, START

class CheckRelevance(BaseModel):
    relevance: str = Field(
        description="Indicates whether the question is related to the database schema. 'relevant' or 'not_relevant'."
    )

def check_relevance(state:AgentState, config:RunnableConfig):
    question = state["question"]
    schema = get_table_schema()
    print('Checking relevance of the question')
    prompt = PromptTemplate.from_template("""Given the schema of a postgresql database. Your job is to identify whether the question is related to the schema or not.
        Respond with 'relevant' or 'not_relevant' only, no other response.
        Schema: {schema}
        Question: {question}
        Response:""")
    llm = ChatOpenAI()
    print("Schema: \n", schema)
    structured_llm = llm.with_structured_output(CheckRelevance)
    chain = prompt | structured_llm
    response = chain.invoke({"schema":schema, "question":question})
    state["relevance"] = response.relevance
    print("Relevance: " , response.relevance)
    return state

class RewriteQuestion(BaseModel):
    question: str = Field(description="Rewritten question")

def rewritten_question(state:AgentState):
    question = state["question"]
    prompt = PromptTemplate.from_template("""Given a question, your job is to rewrite the question in a more clear and concise manner to enable precise SQL queries.
    Question: {question}
    Rewritten Question:""")
    llm = ChatOpenAI().with_structured_output(RewriteQuestion)
    chain = prompt | llm 
    response = chain.invoke({"question":question})
    state["question"] = response.question
    state["attempts"] += 1
    print('rewriting question: ' + response.question)
    return state

def not_relevant_response(state:AgentState):
    prompt = PromptTemplate.from_template("""Generate a funny playful response as the question is not relevant to the database schema. Be creative and have fun.""")
    llm = ChatOpenAI(temperature=0.8)
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({})
    state["result"] = response
    print('not relevant response:' + response)
    return state

def end_iteration(state:AgentState):
    state["result"]  = "Please try again. Maximum attempts reached."
    return state

def relevance_route(state:AgentState):
    if(state["relevance"] == "relevant"):
        return "convert_to_sql"
    else:
        return "not_relevant_response"

def check_attempts(state:AgentState):
    if(state["attempts"] > 3):
        return "end_iteration"
    return "convert_to_sql"

def check_error(state: AgentState):
    if(state["sql_error"] == True):
        return "rewritten_question"
    return "sql_to_human_readable"