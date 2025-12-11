from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .states import AgentState
from .nodes import AgentNodes

class ResearchGraph:
    """LangGraph implementation for the research agent"""

    def __init__(self):
        self.nodes = AgentNodes()
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """Create and configure the research graph"""

        # Initialize the graph with our state
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("plan", self.nodes.plan_node)
        workflow.add_node("research", self.nodes.research_node)
        workflow.add_node("scrape", self.nodes.scrape_node)
        workflow.add_node("write", self.nodes.write_node)
        workflow.add_node("review", self.nodes.review_node)

        # Set entry point
        workflow.set_entry_point("plan")

        # Add edges
        workflow.add_edge("plan", "research")
        workflow.add_edge("research", "scrape")
        workflow.add_edge("scrape", "write")
        workflow.add_edge("write", "review")

        # Add conditional edges from review
        def should_continue(state: AgentState) -> str:
            """Determine if the graph should continue or end"""
            if state.get("report") and state["report"].strip():
                return "end"
            elif state["current_sub_topic_index"] >= len(state.get("sub_topics", [])):
                return "research"  # Loop back to research more
            else:
                return "research"

        workflow.add_conditional_edges(
            "review",
            should_continue,
            {
                "end": END,
                "research": "research"
            }
        )

        # Compile with memory for debugging
        memory_saver = MemorySaver()
        compiled_graph = workflow.compile(checkpointer=memory_saver)

        return compiled_graph

    def run_research(self, query: str, session_id: str = "default") -> Dict[str, Any]:

        print(f"🚀 Starting research for: {query}")

        # Initialize state
        initial_state = {
            "query": query,
            "sub_topics": [],
            "current_sub_topic_index": 0,
            "search_results": [],
            "current_urls": [],
            "documents": [],
            "scraped_content": [],
            "report": "",
            "report_draft": "",
            "loop_count": 0,
            "max_loops": 3,
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "urls_scraped": 0,
            "search_queries_made": 0
        }

        try:
            # Configure checkpointer with proper thread_id
            config = {"configurable": {"thread_id": session_id, "checkpoint_id": session_id}}

            # Run the graph
            result = self.graph.invoke(initial_state, config=config)

            print("✅ Research completed successfully!")

            return {
                "success": True,
                "report": result.get("report", "No report generated"),
                "metadata": {
                    "urls_scraped": result.get("urls_scraped", 0),
                    "search_queries": result.get("search_queries_made", 0),
                    "loop_count": result.get("loop_count", 0),
                    "documents_count": len(result.get("documents", [])),
                    "session_id": session_id
                }
            }

        except Exception as e:
            print(f"❌ Error in research graph: {e}")
            return {
                "success": False,
                "error": str(e),
                "report": f"Error occurred during research: {str(e)}",
                "metadata": {"session_id": session_id}
            }

    def get_graph_visualization(self) -> str:
        """Get a mermaid diagram representation of the graph"""
        return """
graph TD
    A[Plan] --> B[Research]
    B --> C[Scrape]
    C --> D[Write]
    D --> E[Review]
    E -->|Need more research| B
    E -->|Complete| F[End]
        """

# Main execution function
def run_research_agent(query: str, session_id: str = "default") -> Dict[str, Any]:
    """Main function to run the research agent"""
    graph = ResearchGraph()
    return graph.run_research(query, session_id)