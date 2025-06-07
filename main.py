import streamlit as st
from typing import TypedDict, List, Dict
from newsapi import NewsApiClient
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.tools import tool
from datetime import datetime
from fpdf import FPDF
import re
import os
import unicodedata
import tempfile
import io

st.set_page_config(page_title="AI News Summarizer", layout="wide")

# --- State Definition ---
class NewsState(TypedDict):
    topic: str
    articles: List[Dict]
    summaries: List[Dict]
    pdf_path: str
    pdf_bytes: bytes

# --- Azure OpenAI LLM ---
llm = AzureChatOpenAI(
    openai_api_base=st.secrets["azure_openai_base"],
    openai_api_version=st.secrets["azure_openai_version"],
    deployment_name=st.secrets["azure_openai_deployment"],
    openai_api_key=st.secrets["azure_openai_key"],
    temperature=0.5
)

# --- Helper: Relevance Filtering ---
def is_relevant(article: Dict, topic: str) -> bool:
    combined_text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
    topic_keywords = topic.lower().split()
    return all(re.search(rf"\b{re.escape(word)}\b", combined_text) for word in topic_keywords)

# --- Tool: Get News ---
@tool
def get_news(topic: str) -> List[Dict]:
    """Fetch news articles specifically related to the provided topic using NewsAPI."""
    newsapi = NewsApiClient(api_key=st.secrets["news_api_key"])
    response = newsapi.get_everything(
        q=topic,
        qintitle=topic,
        language='en',
        sort_by='relevancy',
        page=1,
        page_size=20
    )
    articles = []
    if response.get('status') == 'ok':
        for article in response.get('articles', []):
            if is_relevant(article, topic):
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "content": article.get("content", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "publishedAt": article.get("publishedAt", ""),
                    "url": article.get("url", "")
                })
    return articles[:5]

# --- Tool: Summarize ---
@tool
def summarize_article_tool(title: str, description: str, content: str) -> Dict:
    """Summarize a news article by generating a headline and summary based on its title, description, and content."""
    clean = lambda x: re.sub(r'[^\w\s.,!?]', '', x or "")
    full_text = f"{clean(title)}. {clean(description)}. {clean(content)}".strip()
    truncated_text = full_text[:1500]

    prompt = PromptTemplate.from_template(
        "Please write a clear, neutral, and informative 4-5 word headline, a short summary (2-3 sentences), "
        "and provide 2-3 specific and relevant tags based on the key topics, companies, technologies, or concepts "
        "mentioned in this article. Tags should be specific (e.g., 'Google Photos', 'AI Editor', 'Meta AI') rather than "
        "generic categories. Separate multiple tags with commas.\n\n{article_text}\n\n"
        "Format:\nHeadline: <headline>\nSummary: <summary>\nTags: <tag1, tag2, tag3>"
    )

    chain = LLMChain(llm=llm, prompt=prompt)

    try:
        result = chain.run(article_text=truncated_text)
        
        # Extract headline
        if "Headline:" in result and "Summary:" in result:
            headline = result.split("Headline:")[1].split("Summary:")[0].strip()
        else:
            headline = "Headline unavailable"
        
        # Extract summary
        if "Summary:" in result:
            if "Tag:" in result:
                summary = result.split("Summary:")[1].split("Tag:")[0].strip()
            else:
                summary = result.split("Summary:")[1].strip()
        else:
            summary = "Summary unavailable"

        if "Tags:" in summary:
            summary = summary.split("Tags:")[0].strip()
        
        # Remove any trailing tag-like patterns (e.g., "Tags: xyz" or just standalone tags at the end)
        summary = re.sub(r'\s*Tags?:\s*.*$', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'\s*\bTags?\b.*$', '', summary, flags=re.IGNORECASE)

        
        # Extract tags
        if "Tags:" in result:
            tags_text = result.split("Tags:")[1].strip()
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
            # Limit to 3 tags maximum
            tags = tags[:3]
        else:
            tags = ["General"]
            
    except Exception as e:
        print(f"Error in summarization: {e}")
        headline = "Headline unavailable"
        summary = "Summary unavailable due to content filter or formatting issue."
        tags = ["General"]
    
    return {"headline": headline, "summary": summary, "tags": tags}

# --- Utility to clean Unicode text ---
def clean_text(text: str) -> str:
    """Remove characters that can't be encoded with latin-1 for PDF output."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("latin-1", "ignore").decode("latin-1")

# --- Tool: Generate PDF ---
def generate_pdf(articles: List[Dict], summaries: List[Dict], topic: str) -> bytes:
    """Generate PDF and return as bytes for download."""
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 16)
            self.cell(0, 12, clean_text("AI News Summarizer Report"), ln=1, align="C")
            self.set_font("Arial", "", 12)
            self.cell(0, 8, clean_text(f"Topic: {topic}"), ln=1, align="C")
            self.cell(0, 8, clean_text(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"), ln=1, align="C")
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

        def add_article(self, article, summary, idx):
            # Article section
            self.set_font("Arial", "B", 14)
            self.set_fill_color(230, 243, 252)
            self.cell(0, 10, clean_text(f"Article {idx}"), ln=1, fill=True)
            self.ln(2)
            
            self.set_font("Arial", "B", 11)
            self.cell(0, 6, clean_text("Title:"), ln=1)
            self.set_font("Arial", "", 10)
            self.multi_cell(0, 6, clean_text(article['title']), align="L")
            self.ln(2)
            
            self.set_font("Arial", "B", 11)
            self.cell(0, 6, clean_text("Description:"), ln=1)
            self.set_font("Arial", "", 10)
            description = combine_and_trim_description(article.get('description', ''), article.get('content', ''))
            self.multi_cell(0, 6, clean_text(description), align="L")
            self.ln(2)
            
            self.set_font("Arial", "B", 11)
            self.cell(0, 6, clean_text("Source & Date:"), ln=1)
            self.set_font("Arial", "", 10)
            self.multi_cell(0, 6, clean_text(f"{article['source']} | {summary['date']}"), align="L")
            self.ln(2)
            
            self.set_font("Arial", "B", 11)
            self.cell(0, 6, clean_text("URL:"), ln=1)
            self.set_font("Arial", "", 10)
            self.multi_cell(0, 6, clean_text(article['url']), align="L")
            self.ln(5)
            
            # Summary section
            self.set_font("Arial", "B", 14)
            self.set_fill_color(234, 250, 241)  # Light green background
            self.cell(0, 10, clean_text(f"AI Generated Summary {idx}"), ln=1, fill=True)
            self.ln(2)
            
            self.set_font("Arial", "B", 11)
            self.cell(0, 6, clean_text("Generated Headline:"), ln=1)
            self.set_font("Arial", "", 10)
            self.multi_cell(0, 6, clean_text(summary['headline']), align="L")
            self.ln(2)
            
            self.set_font("Arial", "B", 11)
            self.cell(0, 6, clean_text("Summary:"), ln=1)
            self.set_font("Arial", "", 10)
            self.multi_cell(0, 6, clean_text(summary['summary']), align="L")
            self.ln(2)
            
            self.set_font("Arial", "B", 11)
            self.cell(0, 6, clean_text("Tags:"), ln=1)
            self.set_font("Arial", "", 10)
            tags_text = ", ".join(summary.get('tags', ['General']))
            self.multi_cell(0, 6, clean_text(tags_text), align="L")
            self.ln(8)
            
            # Add separator line
            if idx < len(articles):
                self.set_draw_color(200, 200, 200)
                self.line(10, self.get_y(), 200, self.get_y())
                self.ln(5)

    pdf = PDF()
    pdf.add_page()
    
    # Add summary statistics
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, clean_text(f"Total Articles Found: {len(articles)}"), ln=1)
    pdf.ln(5)
    
    for idx, (article, summary) in enumerate(zip(articles, summaries), 1):
        pdf.add_article(article, summary, idx)
    
    # Return PDF as bytes
    return pdf.output(dest='S').encode('latin-1')

def generate_pdf_node(state: NewsState) -> Dict:
    pdf_bytes = generate_pdf(state["articles"], state["summaries"], state["topic"])
    return {"pdf_bytes": pdf_bytes}

# --- LangGraph Nodes ---
def get_news_node(state: NewsState) -> Dict:
    return {"articles": get_news.invoke(state["topic"])}

def summarize_node(state: NewsState) -> Dict:
    summaries = [
        {
            **summarize_article_tool.invoke({
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "content": article.get("content", "")
            }),
            "source": article.get("source", ""),
            "date": format_date(article.get("publishedAt", ""))
        }
        for article in state["articles"]
    ]
    return {"summaries": summaries}

# --- Date Formatting ---
def format_date(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        return iso_date

def combine_and_trim_description(description: str, content: str) -> str:
    content = re.sub(r'… \[\+\d+ chars\]', '', content or "")
    description = description or ""
    combined = f"{description.strip()} {content.strip()}".strip()
    combined = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', combined)
    combined = combined[:700]
    last_sentence_end = combined.rfind('.')
    if last_sentence_end != -1:
        combined = combined[:last_sentence_end + 1]
    else:
        combined = combined.rstrip('.') + '.'
    return combined.strip()

# --- LangGraph Setup ---
workflow = StateGraph(NewsState)
workflow.add_node("get_news", get_news_node)
workflow.add_node("summarize_news", summarize_node)
workflow.add_node("generate_pdf", generate_pdf_node)
workflow.add_edge(START, "get_news")
workflow.add_edge("get_news", "summarize_news")
workflow.add_edge("summarize_news", "generate_pdf")
workflow.add_edge("generate_pdf", END)
app = workflow.compile()

# --- Streamlit UI ---
st.title("News Summarizer")
st.markdown("*Get the latest news articles summarized by AI*")

topic = st.text_input("Enter a topic to search for news articles:", placeholder="e.g., Artificial Intelligence")

if topic:
    # Check if we already have data in session state to prevent refetching
    if f"articles_{topic}" not in st.session_state:
        with st.spinner("🔍 Fetching and summarizing news..."):
            input_state = {"topic": topic, "articles": [], "summaries": [], "pdf_path": "", "pdf_bytes": b""}
            output = app.invoke(input_state)
            
            # Store results in session state
            st.session_state[f"articles_{topic}"] = output.get("articles", [])
            st.session_state[f"summaries_{topic}"] = output.get("summaries", [])
            st.session_state[f"pdf_bytes_{topic}"] = output.get("pdf_bytes", b"")
    
    # Get data from session state
    articles = st.session_state.get(f"articles_{topic}", [])
    summaries = st.session_state.get(f"summaries_{topic}", [])
    pdf_bytes = st.session_state.get(f"pdf_bytes_{topic}", b"")

    if not articles:
        st.warning("No relevant articles found for this topic. Try a different search term.")
    else:
        # Header section
        st.subheader(f"📰 Results for: {topic}")
        st.write(f"Found {len(articles)} relevant articles")

        st.markdown("---")

        # Enhanced CSS styling
        st.markdown("""
            <style>
            .news-card {
                padding: 20px;
                border-radius: 15px;
                border: 1px solid #ddd;
                margin-bottom: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                transition: transform 0.2s ease-in-out;
            }
            .news-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.15);
            }
            .original-box {
                background: linear-gradient(135deg, #eaf3fc 0%, #f0f8ff 100%);
                border-left: 4px solid #007acc;
            }
            .summary-box {
                background: linear-gradient(135deg, #eafaf1 0%, #f0fff4 100%);
                border-left: 4px solid #28a745;
            }
            .article-title {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
            .article-meta {
                font-size: 12px;
                color: #6c757d;
                margin-top: 10px;
            }
            .summary-headline {
                font-size: 15px;
                font-weight: bold;
                color: #155724;
                margin-bottom: 8px;
            }
            .tag-badge {
                display: inline-block;
                background: linear-gradient(90deg, #4da6d9, #66b3e0);
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                margin: 2px 3px 2px 0;
            }
            .tags-container {
                margin-top: 8px;
            }
            a {
                color: #007acc;
                text-decoration: none;
                font-weight: 500;
            }
            a:hover {
                text-decoration: underline;
                color: #0056b3;
            }
            .stDownloadButton > button {
                background: linear-gradient(90deg, #007acc, #0056b3);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 10px 20px;
                box-shadow: 0 2px 8px rgba(0,122,204,0.3);
            }
            .stDownloadButton > button:hover {
                background: linear-gradient(90deg, #0056b3, #004085);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,122,204,0.4);
            }
            </style>
        """, unsafe_allow_html=True)

        # Display articles and summaries
        for i, (article, summary) in enumerate(zip(articles, summaries), 1):
            formatted_date = summary.get("date", "")
            full_description = combine_and_trim_description(
                article.get("description", ""), article.get("content", "")
            )
            tags = summary.get("tags", ["General"])
            
            # Create tags HTML
            tags_html = ""
            for tag in tags:
                tags_html += f'<span class="tag-badge">{tag}</span>'

            col1, col2 = st.columns(2, gap="medium")

            with col1:
                st.markdown(f"""
                <div class="news-card original-box">
                    <div class="article-title">📄 Original Article {i}</div>
                    <div style="margin-bottom: 12px;">
                        <strong>Title:</strong><br>
                        <span style="font-size: 14px; line-height: 1.4;">{article.get('title', 'No title available')}</span>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <strong>Description:</strong><br>
                        <span style="font-size: 13px; line-height: 1.5; color: #495057;">{full_description}</span>
                    </div>
                    <div class="article-meta">
                        <strong>Source:</strong> {article.get('source', 'Unknown')}<br>
                        <strong>Published:</strong> {formatted_date}<br>
                        <a href="{article.get('url', '#')}" target="_blank">🔗 Read Full Article</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="news-card summary-box">
                    <div class="article-title">Summary {i}</div>
                    <div style="margin-bottom: 12px;">
                        <div class="summary-headline">{summary.get('headline', 'No headline available')}</div>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <strong>Summary:</strong><br>
                        <span style="font-size: 13px; line-height: 1.5; color: #495057;">{summary.get('summary', 'No summary available')}</span>
                    </div>
                    <div class="article-meta">
                        <strong>Source:</strong> {summary.get('source', 'Unknown')}<br>
                        <strong>Published:</strong> {summary.get('date', 'Unknown')}
                        <div class="tags-container">
                            <strong>Tags:</strong> {tags_html}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Footer section with download option
        st.markdown("---")
        
        # Download button at the bottom
        if pdf_bytes:
            st.markdown("""
                <div style="text-align: center; margin: 20px 0;">
                    <h5 style="color: #007acc;">📄 Download PDF Report</h5>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                filename = f"news_summary_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                st.download_button(
                    label="📄 Download PDF Report Containing All Articles and Summaries",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    help="Download a comprehensive PDF report with all articles and summaries",
                    use_container_width=True,
                    type="secondary"
                )
                
        # Additional info
        st.markdown("""
        <div style="text-align: center; margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 10px;">
            <small style="color: #6c757d;">
                💡 <strong>Tip:</strong> The PDF report contains all articles with enhanced formatting and is perfect for offline reading or sharing.
            </small>
        </div>
        """, unsafe_allow_html=True)