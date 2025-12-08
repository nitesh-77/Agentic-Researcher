import os
import json
import requests
import uvicorn
from typing import Type, List
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from fastapi import FastAPI
from pydantic import BaseModel, Field

# LangChain Imports
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool, BaseTool
from langchain.memory import ConversationSummaryBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document  
from langchain_mistralai import ChatMistralAI

# Load environment variables
load_dotenv()
browserless_api_key = os.getenv("BROWSERLESS_API_KEY")
serper_api_key = os.getenv("SERP_API_KEY")
mistral_api_key = os.getenv("MISTRAL_API_KEY")

# 1. SEARCH TOOL
def search(query):
    """Searches Google for the given query using Serper.dev"""
    print(f"Searching for: {query}")
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': serper_api_key,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text

# 2. SCRAPING TOOL
def scrape_website(objective: str, url: str):
    """Scrapes a website with better headers and error handling."""
    print(f"Scraping website: {url}...")
    
    # Define Headers to mimic a real browser (Fixes 403 Forbidden errors)
    headers = {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
    }
    
    # Define Payload
    data = {
        "url": url,
        "rejectRequestPattern": [
            "*.jpg", "*.jpeg", "*.png", "*.gif", "*.svg", "*.css", "*.mp4", "*.woff", "*.woff2"
        ],
        "gotoOptions": {
            "timeout": 20000, 
            "waitUntil": "networkidle2" # Better for SPAs (wait until network is mostly quiet)
        },
        # ADDED: Stealth options to avoid detection
        "stealth": True 
    }
    
    data_json = json.dumps(data)
    post_url = f"https://chrome.browserless.io/content?token={browserless_api_key}"
    
    try:
        response = requests.post(post_url, headers=headers, data=data_json)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Remove junk
            for script in soup(["script", "style", "nav", "footer"]):
                script.extract()
                
            text = soup.get_text(separator=' ', strip=True)
            print(f"Scraped Content Length: {len(text)}")
            
            # Handle empty scrapes (common with some SPAs)
            if len(text) < 100:
                return f"Error: Scraped content was empty. The website {url} might block scrapers."

            if len(text) > 8000:
                return summary(objective, text)
            else:
                return text
        else:
            print(f"Error scraping: {response.status_code}")
            return f"Error: Could not scrape website. Status {response.status_code}"
            
    except Exception as e:
        print(f"Exception during scrape: {e}")
        return f"Error: Technical issue scraping website: {e}"

def summary(objective, content):
    """Summarizes text using Mistral"""
    llm = ChatMistralAI(model="mistral-small-latest", temperature=0, mistral_api_key=mistral_api_key)

    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n"], chunk_size=10000, chunk_overlap=500)
    docs = text_splitter.create_documents([content])
    
    map_prompt = """
    Write a summary of the following text for {objective}:
    "{text}"
    SUMMARY:
    """
    map_prompt_template = ChatPromptTemplate.from_template(map_prompt)

    summary_chain = load_summarize_chain(
        llm=llm,
        chain_type='map_reduce',
        map_prompt=map_prompt_template,
        combine_prompt=map_prompt_template,
        verbose=True
    )

    output = summary_chain.run(input_documents=docs, objective=objective)
    return output

# TOOL DEFINITIONS

class ScrapeWebsiteInput(BaseModel):
    objective: str = Field(description="The objective & task that users give to the agent")
    url: str = Field(description="The url of the website to be scraped")

class ScrapeWebsiteTool(BaseTool):
    name: str = "scrape_website"
    description: str = "useful when you need to get data from a website url, passing both url and objective to the function"
    args_schema: Type[BaseModel] = ScrapeWebsiteInput

    def _run(self, objective: str, url: str):
        return scrape_website(objective, url)

# 3. AGENT SETUP

tools = [
    Tool(
        name="Search",
        func=search,
        description="useful for when you need to answer questions about current events, data. You should ask targeted questions"
    ),
    ScrapeWebsiteTool(),
]

llm = ChatMistralAI(
    model="mistral-small-latest",
    temperature=0,
    mistral_api_key=mistral_api_key
)

memory = ConversationSummaryBufferMemory(
    memory_key="memory", 
    return_messages=True, 
    llm=llm, 
    max_token_limit=1000
)

#  SYSTEM PROMPT
system_prompt = """You are a thorough and accurate AI Researcher.

Your goal is to provide a comprehensive answer to the user's request, backed by specific facts.

CRITICAL INSTRUCTIONS:
1. **Search First**: Find relevant information on the web.
2. **Priority - Verify**: Try to scrape the most relevant URL to get technical details.
3. **Fallback Strategy**: 
   - If the `scrape_website` tool fails or returns an error, YOU MUST switch to using the Search Snippets.
   - However, you must explicitly state: "I could not verify the details from the source documentation, but search results indicate..."
4. **Citations**: 
   - If you use scraped text, cite the URL as [Source: URL].
   - If you use search snippets, cite the URL as [Search Result: URL].

Never return a vague "I apologize" answer. Always give the best information you have, clearly labeled with its source.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="memory"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create Agent
agent = create_tool_calling_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    memory=memory,
    handle_parsing_errors=True
)

# 4. FASTAPI APP
app = FastAPI()

class Query(BaseModel):
    query: str

@app.post("/")
def researchAgent(query: Query):
    query_text = query.query
    content = agent_executor.invoke({"input": query_text})
    return content['output']

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)