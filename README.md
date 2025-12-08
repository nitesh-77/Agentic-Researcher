# Agentic Researcher

**Agentic Researcher** is an autonomous AI agent designed to perform deep, verifiable technical research. Unlike standard LLM chatbots that rely on hallucinations or surface-level search snippets, this agent orchestrates a multi-step workflow: it searches the web, critically evaluates sources, and autonomously scrapes full documentation to verify facts before answering.

Built with **Python**, **LangChain**, **Mistral AI**, and **FastAPI**, it solves the "lazy agent" problem by enforcing evidence-based reasoning.

##  Key Features

* **🤖 Autonomous Decision Making:** The agent intelligently decides when to search, which links to filter, and when to scrape for more details.
* **📉 Intelligent Noise Filtering:** It acts as a critical editor, analyzing search snippets to identify and select only the most authoritative sources (like official documentation) while discarding irrelevant clickbait.
* **🕷️ Full-Text Scraping:** Equipped with a headless browser, the agent visits the selected URLs to render and read the actual page content—including complex JavaScript-heavy sites—ensuring no detail is missed.
* **🧠 Mistral AI Integration:** Uses `mistral-small-latest` for high-speed, cost-effective reasoning and summarization.
* **📊 Interactive UI:** Features a clean **Streamlit** frontend to visualize the research process in real-time.

## 🛠️ Tech Stack

* **Core:** Python, LangChain
* **LLM:** Mistral AI API
* **Backend:** FastAPI
* **Frontend:** Streamlit
* **Tools:** Serper Dev (Search), Browserless (Scraping)

## ⚙️ Setup Instructions

Follow these steps to set up the project locally.

### 1. Clone the Repository
```bash
git clone https://github.com/nitesh-77/Agentic-Researcher.git
```
### 2. Create a Virtual Environment
```bash
# Create a new conda environment 
conda create -n research-agent python=3.10 -y

# Activate the environment
conda activate research-agent
```

### 3. Install the required packages
```bash
pip install -r requirements.txt
```

### 4. Configure API keys
Rename the environment file: Change the template file `example.env` to `.env`

Add your API Keys:
```bash
MISTRAL_API_KEY=your_mistral_api_key_here
SERP_API_KEY=your_serper_dev_key_here
BROWSERLESS_API_KEY=your_browserless_io_key_here
```
### 5. Make the script executable (only needed once on Linux/Mac)
`chmod +x run.sh`

### 6. Run the application
`./run.sh