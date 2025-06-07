from langgraph.graph import StateGraph, START, END
from main import NewsState, get_news_node, summarize_node,generate_pdf_node

def build_news_graph():
    workflow = StateGraph(NewsState)
    workflow.add_node("get_news", get_news_node)
    workflow.add_node("summarize_news", summarize_node)
    workflow.add_node("generate_pdf", generate_pdf_node)
    workflow.add_edge(START, "get_news")
    workflow.add_edge("get_news", "summarize_news")
    workflow.add_edge("summarize_news", "generate_pdf")
    workflow.add_edge("generate_pdf", END)
    return workflow