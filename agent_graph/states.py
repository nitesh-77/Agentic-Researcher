from typing import TypedDict, List, Dict, Optional
from langchain_core.documents import Document

class AgentState(TypedDict):
    """
    State management for the LangGraph agent
    """
    # User input
    query: str

    # Planning phase
    sub_topics: List[str]
    current_sub_topic_index: int

    # Research phase
    search_results: List[Dict]
    current_urls: List[str]

    # Content storage
    documents: List[Document]
    scraped_content: List[Dict]

    # Writing phase
    report: str
    report_draft: str

    # Control flow
    loop_count: int
    max_loops: int

    # Metadata
    session_id: str
    start_time: str

    # Quality metrics
    urls_scraped: int
    search_queries_made: int