import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from tools.search import SearchTool
from tools.scraper import ScraperTool

from .global_state import get_global_state
from .states import AgentState

load_dotenv()

class AgentNodes:
    """Node functions for the LangGraph agent"""

    def __init__(self):
        # 1. Initialize the LLM 
        self.llm = ChatMistralAI(
            model="mistral-small-latest",
            temperature=0,
            mistral_api_key=os.getenv("MISTRAL_API_KEY")
        )
        
        # 2. Initialize Tools
        self.search_tool = SearchTool()
        self.scraper_tool = ScraperTool()
        
        # 3. Initialize Text Splitter (With the Network Bug fix included)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len, 
            separators=["\n\n", "\n", " ", ""]
        )

    def plan_node(self, state: AgentState) -> AgentState:
        """Break down query into sub-topics"""
        print("🎯 Planning node: Breaking down query into sub-topics")

        system_prompt = """You are a research planning expert. Break down the user's query into 3-5 specific sub-topics that need to be researched.

Before answering, think: "What are the key aspects of this topic that need separate investigation?"

Return only a JSON array of sub-topics, nothing else."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Query: {query}")
        ])

        chain = prompt | self.llm
        result = chain.invoke({"query": state["query"]})

        try:
            sub_topics = json.loads(result.content.strip())
            if not isinstance(sub_topics, list):
                sub_topics = [state["query"]]  # Fallback
        except:
            sub_topics = [state["query"]]  # Fallback

        state["sub_topics"] = sub_topics
        state["current_sub_topic_index"] = 0
        print(f"📋 Plan created: {sub_topics}")

        return state

    def research_node(self, state: AgentState) -> AgentState:
        """Search for information on current sub-topic"""
        print(f"🔍 Research node: Working on sub-topic {state['current_sub_topic_index'] + 1}")

        if state["current_sub_topic_index"] >= len(state["sub_topics"]):
            return state

        current_topic = state["sub_topics"][state["current_sub_topic_index"]]

        # If need to re-phrase the search (loop > 0), add context
        if state["loop_count"] > 0:
            current_topic = f"{current_topic} - additional research needed"

        search_query = f"{state['query']} : {current_topic}"
        print(f"🔎 Searching for: {search_query}")

        # Perform search using the combined query
        raw_results = self.search_tool.search(search_query, num_results=10)
        
        filtered_results = self.search_tool.filter_quality_urls(raw_results)

        state["search_queries_made"] += 1
        state["search_results"] = filtered_results

        print(f"📊 Found {len(filtered_results)} quality URLs")

        # Select top URLs for scraping (at least 2, max 5)
        urls_to_scrape = [r["link"] for r in filtered_results[:5]]
        state["current_urls"] = urls_to_scrape

        return state

    def scrape_node(self, state: AgentState) -> AgentState:
        """Scrape content from URLs and add to ChromaDB"""
        print(f"🕷️ Scrape node: Processing {len(state['current_urls'])} URLs")

        global_state = get_global_state()
        
        scraped_content = []

        for url in state["current_urls"]:
            try:
                print(f"🌐 Scraping: {url}")
                result = self.scraper_tool.scrape(url, state["sub_topics"][state["current_sub_topic_index"]])
                scraped_content.append(result)

                # Add successful scrapes to ChromaDB
                if result["status"] == "success":
                    chunks = self.text_splitter.split_text(result["content"])

                    documents = [
                        Document(
                            page_content=chunk,
                            metadata={
                                "source": url,
                                "title": result["title"],
                                "scraped_at": result["scraped_at"],
                                "chunk_index": i
                            }
                        )
                        for i, chunk in enumerate(chunks)
                    ]

                    global_state.add_documents(documents)
                    state["urls_scraped"] += 1
                    state["documents"].extend(documents)

                    print(f"✅ Added {len(documents)} chunks to ChromaDB")

                elif result["status"] in ["error", "timeout", "minimal"]:
                    print(f"⚠️  Using fallback for {url}: {result['status']}")

            except Exception as e:
                print(f"❌ Error scraping {url}: {e}")
                continue

        state["scraped_content"] = scraped_content
        return state

    def write_node(self, state: AgentState) -> AgentState:
        """Generate report based on collected information"""
        print("📝 Write node: Generating research report")

        global_state = get_global_state()
        
        # Query ChromaDB for relevant content
        relevant_docs = global_state.similarity_search(
            state["query"],
            k=min(10, len(state["documents"]))
        )

        # Format sources for the prompt
        sources_text = ""
        for doc in relevant_docs:
            source = doc.metadata.get("source", "Unknown")
            title = doc.metadata.get("title", "Unknown")
            content = doc.page_content[:500]  # Truncate for context
            sources_text += f"Source: {title} ({source})\nContent: {content}\n---\n"

        system_prompt = """You are a technical research writer. Create a comprehensive report based on the provided sources.

CRITICAL GUIDELINES:
1. Use only the information from the provided sources
2. Include specific citations: [Source: Title (URL)]
3. Structure the report with clear sections
4. If sources were limited or had issues, mention this explicitly
5. Focus on technical accuracy and recent information

Before writing, briefly outline your approach in a sentence or two."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """
Query: {query}

Relevant Sources:
{sources}

Write a comprehensive research report:
""")
        ])

        chain = prompt | self.llm
        result = chain.invoke({
            "query": state["query"],
            "sources": sources_text
        })

        state["report_draft"] = result.content
        print(f"📄 Report draft created ({len(result.content)} characters)")

        return state

    def review_node(self, state: AgentState) -> AgentState:
        """Review report quality and decide next action"""
        print("👁️ Review node: Evaluating report quality")

        system_prompt = """You are a research quality reviewer. Evaluate if the report is substantial and complete.

Return ONLY one of these values:
- "COMPLETE" if the report is comprehensive and well-supported
- "NEED_MORE_RESEARCH" if the report is too brief or lacks detail
- "SOURCES_INSUFFICIENT" if available sources were limited

Be objective and strict about quality."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Review this report:\n\n{report}")
        ])

        chain = prompt | self.llm
        decision = chain.invoke({"report": state["report_draft"]})

        print(f"📊 Review decision: {decision.content.strip()}")

        if "COMPLETE" in decision.content.upper():
            state["report"] = state["report_draft"]
            state["current_sub_topic_index"] = len(state["sub_topics"])  # Signal completion
        elif state["loop_count"] >= state["max_loops"] - 1:
            print("⚠️  Max loops reached, forcing completion")
            state["report"] = state["report_draft"] + "\n\n*Note: Research was limited due to source availability.*"
            state["current_sub_topic_index"] = len(state["sub_topics"])
        else:
            # Need more research - move to next sub-topic or re-search current one
            state["current_sub_topic_index"] += 1
            state["loop_count"] += 1
            if state["current_sub_topic_index"] >= len(state["sub_topics"]):
                state["current_sub_topic_index"] = 0  # Loop back to first sub-topic

        return state