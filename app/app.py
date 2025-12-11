import os
import sys

# Add the parent directory to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import chainlit as cl
from typing import Dict, Any
from dotenv import load_dotenv

from agent_graph import run_research_agent
from agent_graph.global_state import get_global_state, cleanup_global_state
from utils.graph_viz import KnowledgeGraphGenerator
from utils.pdf_gen import PDFGenerator

load_dotenv()

# Initialize global utilities
graph_generator = KnowledgeGraphGenerator()
pdf_generator = PDFGenerator()

@cl.on_chat_start
async def on_chat_start():
    """Initialize a new research session"""

    # Clear previous session's vector store
    global_state = get_global_state()
    global_state.clear_vectorstore()

    # Generate unique session ID
    session_id = str(uuid.uuid4())[:8]
    cl.user_session.set("session_id", session_id)

    # Set initial mode to research
    cl.user_session.set("mode", "research")
    cl.user_session.set("research_complete", False)

    # Send welcome message
    await cl.Message(
        content="🤖 **Agentic Researcher is ready!**\n\n"
                "I'll help you conduct deep, verifiable technical research. "
                "Just type your research question below and I'll:\n\n"
                "🔍 Search for relevant sources\n"
                "🕷️ Scrape detailed content\n"
                "📊 Generate interactive knowledge graphs\n"
                "📝 Create comprehensive reports with citations\n"
                "💬 Enable follow-up Q&A with your research data\n\n"
                "**Ready when you are!** 🚀"
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages"""

    session_id = cl.user_session.get("session_id")
    mode = cl.user_session.get("mode", "research")
    research_complete = cl.user_session.get("research_complete", False)

    print(f"📝 Message received in {mode} mode: {message.content}")

    if mode == "research" and not research_complete:
        await handle_research_mode(message, session_id)
    else:
        await handle_chat_mode(message, session_id)

async def handle_research_mode(message: cl.Message, session_id: str):
    """Handle research mode - run the full research pipeline"""

    query = message.content.strip()

    # Create status message
    status_msg = cl.Message(
        content="🤔 **Planning your research...**\n\n"
                "*Breaking down your query into focused sub-topics...*"
    )
    await status_msg.send()

    try:
        # Initialize async callback handler for LangChain
        async_callback = cl.AsyncLangchainCallbackHandler(
            stream_final_answer=False
        )

        # Run research agent with callback
        cl.user_session.set("callback", async_callback)

        # Set content first, then update
        status_msg.content = "🔍 **Searching the web...**\n\n*Filtering quality sources and identifying relevant URLs...*"
        await status_msg.update()

        # Run research
        result = run_research_agent(query, session_id)

        if not result.get("success"):
            status_msg.content = f"❌ **Research failed:** {result.get('error', 'Unknown error')}"
            await status_msg.update()
            return

        # Update status
        status_msg.content = "📝 **Writing comprehensive report...**\n\n*Creating detailed analysis with citations...*"
        await status_msg.update()

        report = result["report"]
        metadata = result["metadata"]

        # Send final report
        status_msg.content = (
            f"✅ **Research Complete!**\n\n"
            f"*Generated comprehensive report with {metadata.get('urls_scraped', 0)} sources scraped, "
            f"{metadata.get('search_queries', 0)} search queries executed*\n\n"
            f"📊 **Report:**\n\n{report}"
        )
        await status_msg.update()

        # Generate knowledge graph
        graph_msg = cl.Message(
            content="🕸️ **Generating interactive knowledge graph...**"
        )
        await graph_msg.send()

        try:
            graph_path = graph_generator.generate_interactive_graph(report, session_id)

            # Send graph as attachment
            elements = [
                cl.File(
                    name="knowledge_graph.html",
                    path=graph_path,
                    display="inline"
                )
            ]

            graph_msg.content = "🎯 **Interactive Knowledge Graph Generated!**\n\n*Drag to move nodes, scroll to zoom, hover for details*"
            graph_msg.elements = elements
            await graph_msg.update()

        except Exception as e:
            graph_msg.content = f"⚠️ **Knowledge graph generation failed:** {str(e)}"
            await graph_msg.update()

        # Generate PDF report
        pdf_msg = cl.Message(
            content="📄 **Generating PDF report...**"
        )
        await pdf_msg.send()

        try:
            pdf_path = pdf_generator.generate_pdf(report, session_id, f"Research Report - {query[:50]}")

            if pdf_path:
                elements = [
                    cl.File(
                        name="research_report.pdf",
                        path=pdf_path,
                        display="inline"
                    )
                ]

                pdf_msg.content = "📋 **PDF Report Generated!**\n\n*Download your complete research report with citations*"
                pdf_msg.elements = elements
                await pdf_msg.update()
            else:
                pdf_msg.content = "⚠️ **PDF generation failed**"
                await pdf_msg.update()

        except Exception as e:
            pdf_msg.content = f"⚠️ **PDF generation failed:** {str(e)}"
            await pdf_msg.update()

        # Switch to chat mode
        cl.user_session.set("research_complete", True)
        cl.user_session.set("mode", "chat")

        # Send transition message
        await cl.Message(
            content="🎯 **Expert Chat Mode Activated!**\n\n"
                    "*Your research data is now loaded in memory. Ask me anything about:*\n\n"
                    "• Specific details from the report\n"
                    "• Comparisons between different sources\n"
                    "• Technical clarifications\n"
                    "• Source citations for specific claims\n\n"
                    "**What would you like to explore further?** 💬"
        ).send()

    except Exception as e:
        status_msg.content = f"❌ **Research error:** {str(e)}"
        await status_msg.update()
        print(f"Error in research mode: {e}")

async def handle_chat_mode(message: cl.Message, session_id: str):
    """Handle chat mode - RAG-based Q&A with research data"""

    query = message.content.strip()

    # Initialize callback for streaming
    callback = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True
    )

    status_msg = cl.Message(
        content="🤔 **Analyzing your question...**\n\n*Searching through collected research data...*"
    )
    await status_msg.send()

    try:
        # Get global state
        global_state = get_global_state()

        doc_count = global_state.get_document_count()
        if doc_count == 0:
            status_msg.content = "⚠️ **No research data found**\n\n*Please run a research query first, then we can chat about the findings.*"
            await status_msg.update()
            return

        # Search for relevant documents
        relevant_docs = global_state.similarity_search(query, k=5)

        if not relevant_docs:
            status_msg.content = "🔍 **No relevant information found**\n\n*Try rephrasing your question or ask about specific aspects of the research.*"
            await status_msg.update()
            return

        # Format context from relevant documents
        context_parts = []
        sources = set()

        for i, doc in enumerate(relevant_docs):
            content = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
            source = doc.metadata.get("title", "Unknown")
            source_url = doc.metadata.get("source", "")

            context_parts.append(f"**Source {i+1}: {source}**\n{content}")
            sources.add(f"{source} ({source_url})")

        context = "\n\n---\n\n".join(context_parts)
        sources_list = "\n".join(f"• {source}" for source in sources)

        # Create follow-up prompt
        system_prompt = """You are an expert research assistant. Answer the user's question based ONLY on the provided research context.

GUIDELINES:
1. Be specific and detailed using the provided sources
2. Always cite sources using [Source: Title] format
3. If information isn't available, say so clearly
4. Maintain technical accuracy
5. Use clear, concise language

Context from research:
{context}"""

        # Query the model
        from langchain.prompts import ChatPromptTemplate
        from langchain_mistralai import ChatMistralAI
        
        # Re-initialize LLM for chat to ensure fresh context
        chat_llm = ChatMistralAI(
            model="mistral-small-latest",
            temperature=0,
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            callbacks=[callback]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Question: {question}\n\nBased on the research context provided above, please answer:")
        ])

        chain = prompt | chat_llm

        # Generate answer
        answer = await chain.ainvoke({
            "context": context,
            "question": query
        })

        status_msg.content = f"💡 **Answer:**\n\n{answer.content}\n\n**Sources referenced:**\n{sources_list}"
        await status_msg.update()

    except Exception as e:
        status_msg.content = f"❌ **Error processing question:** {str(e)}"
        await status_msg.update()
        print(f"Error in chat mode: {e}")