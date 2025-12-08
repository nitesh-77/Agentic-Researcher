import streamlit as st
import requests
import json

# 1. Page Configuration
st.set_page_config(
    page_title="AI Researcher",
    page_icon="🕵️",
    layout="centered"
)

# 2. Header and Description
st.title("🕵️ Deep Research Agent")
st.markdown("---")
st.markdown(
    """
    **Welcome!** This agent uses **Mistral AI**, **Serper**, and **Browserless** to:
    1. 🔍 Search the web for your topic.
    2. 📄 Scrape relevant pages for details.
    3. 📝 Synthesize a factual summary with citations.
    """
)

# 3. User Input
query = st.text_area(
    "What would you like to research?",
    placeholder="e.g., What are the latest breakthroughs in solid-state batteries?",
    height=100
)

# 4. Action Button
if st.button("Start Research", type="primary"):
    if not query:
        st.warning("Please enter a topic first.")
    else:
        # Show a spinner while the backend works
        with st.spinner("🕵️‍♂️ Agent is searching and scraping... (this may take a minute)"):
            try:
                # Call your own FastAPI backend
                response = requests.post(
                    "http://127.0.0.1:8000/", 
                    json={"query": query}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Success! Show result
                    st.success("Research Complete!")
                    st.markdown("### 📊 Research Report")
                    st.markdown("---")
                    
                    # Render the markdown report
                    st.markdown(result)
                    
                    # Optional: Add a download button for the report
                    st.download_button(
                        label="Download Report",
                        data=result,
                        file_name="research_report.md",
                        mime="text/markdown"
                    )
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            
            except requests.exceptions.ConnectionError:
                st.error("🚨 Could not connect to the backend. Is 'python app.py' running?")