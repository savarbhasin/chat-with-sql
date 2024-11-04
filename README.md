# SQL Agent with LangChain, LangGraph, and PostgreSQL

This project implements an intelligent SQL Agent that interprets natural language questions, translates them into SQL queries, executes them on a PostgreSQL database, and formats results in a readable format. Using `LangChain` and `LangGraph`, this agent exemplifies agentic workflows for database interactions, leveraging structured prompts, relevance checks, and error handling to provide smooth, human-like conversations with a SQL database.

## Key Features

- **Agentic Workflow with LangGraph**: This project utilizes `LangGraph`'s `StateGraph` to design a modular, agentic workflow, seamlessly managing steps like user validation, relevance checks, SQL generation, and execution.
- **Natural Language to SQL Translation**: Converts human queries into SQL statements using structured prompts from `LangChain` based on the database schema.
- **Relevance Check**: Determines if a user question is relevant to the database schema; if not, it generates playful responses.
- **Human-Readable Results**: SQL results are processed into concise, understandable summaries for improved UX.
- **Database Connection Pooling**: Manages connections efficiently using a PostgreSQL connection pool.
- **Dynamic Query Rewriting**: Attempts question rephrasing and SQL regeneration if an error occurs, ensuring high query accuracy.
