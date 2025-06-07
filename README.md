
# 🧠 AI News Intelligence Hub

A powerful AI-powered application that fetches, filters, analyzes, and summarizes the most relevant news articles on any topic of your choice — all through a beautifully designed Streamlit interface.
---

## 🚀 Features

- 🔎 **Smart News Fetching** using NewsAPI with multi-query strategies  
- ✅ **Advanced Relevance Filtering** for 90–95% accurate results  
- 🤖 **AI-Powered Summarization** via Azure OpenAI GPT-4  
- 🎭 **Sentiment Analysis** with confidence scores and key phrases  
- 📄 **Downloadable PDF Reports** with summaries and insights  
- 🏷️ **Smart Tagging** to categorize news articles  
- 📊 **Streamlit Interface** with modern UI and session tracking

---

## 🛠️ Tech Stack

| Feature               | Technology Used             |
|----------------------|-----------------------------|
| News Fetching        | NewsAPI                     |
| AI Processing        | Azure OpenAI GPT-4 (GPT-4o) |
| Workflow Engine      | LangGraph                   |
| Frontend & UI        | Streamlit                   |
| PDF Report Generator | `reportlab`                 |
| Styling              | Custom CSS in Streamlit     |

---

## How It Works

1. **Enter a Topic** – Like `"Tesla earnings"` or `"AI in healthcare"`.
2. **LangGraph Agent Workflow** kicks in:
   - Step 1: `fetch_news_articles()` queries NewsAPI
   - Step 2: `summarize_article()` summarizes and tags each result
3. **Relevance Filtering** ensures only the top articles are used.
4. **Streamlit App** displays:
   - Article details with links
   - AI summaries with tags
   - Sentiment badges and confidence meters
5. **One-click PDF Download** for offline reports

---

## Directory Structure

```
ai-news-intelligence-hub/
│
├── app.py                    # Streamlit app entry point
├── graph_logic.py            # LangGraph workflow logic
├── agents/news_agent.py      # NewsAgent class (Azure OpenAI + tools)
├── tools/fetch_news.py       # Tool: Fetch articles
├── tools/summarize.py        # Tool: Summarize articles
├── utils/pdf_generator.py    # PDF generation logic
├── utils/helpers.py          # Relevance, color utils, etc.
├── styles/custom.css         # Custom UI styling
├── requirements.txt
└── README.md
```

## ⚙️ Setup Instructions

```bash
# Clone the repository
git clone https://github.com/yourusername/AI_News_Summarizer.git
cd ai-news-intelligence-hub

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API Keys (Azure OpenAI, NewsAPI)
export NEWS_API_KEY="your_newsapi_key"
export AZURE_OPENAI_API_KEY="your_azure_key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
export AZURE_DEPLOYMENT_NAME="your-deployment-id"

# Run the app
streamlit run app.py
```

---

## 🧠 Example Topics

- `"Tesla stock performance"`
- `"AI impact on healthcare diagnostics"`
- `"India space tech growth"`
- `"Climate change summit outcomes"`

---

## 📄 PDF Output Example

The app generates a downloadable PDF with:

- Title, description, and full article URL  
- AI-generated headline & summary  
- Sentiment analysis with confidence  
- Smart tags for quick reference  

---

## 🧰 Future Enhancements

- 🗂️ Topic history and bookmarking  
- 🌐 Multilingual summarization  
- 🔄 Auto-refreshing live news feed  
- 🧵 Threaded summaries over time

---

## 🙌 Acknowledgements

- [NewsAPI.org](https://newsapi.org/)
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service)
- [LangGraph](https://www.langchain.com/langgraph)
- [Streamlit](https://streamlit.io)

---

## 📜 License

This project is licensed under the MIT License.
