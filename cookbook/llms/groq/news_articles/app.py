import nest_asyncio
from typing import Optional

import streamlit as st
from duckduckgo_search import DDGS
from phi.tools.newspaper4k import Newspaper4k
from phi.utils.log import logger

from assistants import get_article_summarizer, get_article_writer,get_article_writer_chinese,get_article_writer_chinese_out  # type: ignore

nest_asyncio.apply()
st.set_page_config(
    page_title="News Articles",
    page_icon=":orange_heart:",
)
st.title("News Articles powered by Groq")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")

from deep_translator import GoogleTranslator
from notion_client import Client
import re
def translate_text(text, target_language):
    # 替换为您自己的Google Cloud API密钥
    target_language='zh-CN'
    translator = GoogleTranslator(source='auto', target=target_language)
    translated_text = translator.translate(text)
    return translated_text

class notion_client:
    def __init__(self):
        global global_notion
        global global_database_id
        global_token = "secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw"
        global_database_id = "3ad7d67332a34988868dcdfb03630387"  # 采集-关键字新闻
        global_notion = Client(auth=global_token)
        print('开始Notion自动化获取数据...')

    def create_page_blocks(self, page_title,content):
        new_page = global_notion.pages.create(
            parent={
                'database_id': global_database_id
            },
            properties={
                '标题': {
                    'title': [
                        {
                            'text': {
                                'content': str(page_title)
                            }
                        }
                    ]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                }
            ]
        )
        print(f'创建Notion页面成功...{page_title}')


def truncate_text(text: str, words: int) -> str:
    return " ".join(text.split()[:words])


def main() -> None:
    # Get models
    summary_model = st.sidebar.selectbox(
        "Select Summary Model", options=["llama3-8b-8192", "mixtral-8x7b-32768", "llama3-70b-8192"]
    )
    # Set assistant_type in session state
    if "summary_model" not in st.session_state:
        st.session_state["summary_model"] = summary_model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["summary_model"] != summary_model:
        st.session_state["summary_model"] = summary_model
        st.rerun()

    writer_model = st.sidebar.selectbox(
        "Select Writer Model", options=["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]
    )
    # Set assistant_type in session state
    if "writer_model" not in st.session_state:
        st.session_state["writer_model"] = writer_model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["writer_model"] != writer_model:
        st.session_state["writer_model"] = writer_model
        st.rerun()

    # Checkboxes for research options
    st.sidebar.markdown("## Research Options")
    num_search_results = st.sidebar.slider(
        ":sparkles: Number of Search Results",
        min_value=3,
        max_value=20,
        value=7,
        help="Number of results to search for, note only the articles that can be read will be summarized.",
    )
    per_article_summary_length = st.sidebar.slider(
        ":sparkles: Length of Article Summaries",
        min_value=100,
        max_value=2000,
        value=800,
        step=100,
        help="Number of words per article summary",
    )
    news_summary_length = st.sidebar.slider(
        ":sparkles: Length of Draft",
        min_value=1000,
        max_value=10000,
        value=5000,
        step=100,
        help="Number of words in the draft article, this should fit the context length of the model.",
    )

    # Get topic for report
    article_topic = st.text_input(
        ":spiral_calendar_pad: Enter a topic",
        value="Hashicorp IBM",
    )
    write_article = st.button("Write Article")
    if write_article:
        news_results = []
        news_summary: Optional[str] = None
        with st.status("Reading News", expanded=False) as status:
            with st.container():
                news_container = st.empty()
                ddgs = DDGS()
                newspaper_tools = Newspaper4k()
                results = ddgs.news(keywords=article_topic, max_results=num_search_results)
                for r in results:
                    if "url" in r:
                        article_data = newspaper_tools.get_article_data(r["url"])
                        if article_data and "text" in article_data:
                            r["text"] = article_data["text"]
                            news_results.append(r)
                            if news_results:
                                news_container.write(news_results)
            if news_results:
                news_container.write(news_results)
            status.update(label="News Search Complete", state="complete", expanded=False)

        if len(news_results) > 0:
            print(f"Found {len(news_results)} articles")
            news_summary = ""
            with st.status("Summarizing News", expanded=False) as status:
                article_summarizer = get_article_summarizer(model=summary_model, length=per_article_summary_length)
                with st.container():
                    summary_container = st.empty()
                    for news_result in news_results:
                        news_summary += f"### {news_result['title']}\n\n"
                        news_summary += f"- Date: {news_result['date']}\n\n"
                        news_summary += f"- URL: {news_result['url']}\n\n"
                        news_summary += f"#### Introduction\n\n{news_result['body']}\n\n"

                        _summary: str = article_summarizer.run(news_result["text"], stream=False)
                        _summary_length = len(_summary.split())
                        if _summary_length > news_summary_length:
                            _summary = truncate_text(_summary, news_summary_length)
                            logger.info(f"Truncated summary for {news_result['title']} to {news_summary_length} words.")
                        news_summary += "#### Summary\n\n"
                        news_summary += _summary
                        news_summary += "\n\n---\n\n"
                        if news_summary:
                            summary_container.markdown(news_summary)
                        if len(news_summary.split()) > news_summary_length:
                            logger.info(f"Stopping news summary at length: {len(news_summary.split())}")
                            break
                if news_summary:
                    summary_container.markdown(news_summary)
                status.update(label="News Summarization Complete", state="complete", expanded=False)

        if news_summary is None:
            st.write("Sorry could not find any news or web search results. Please try again.")
            return

        article_draft = ""
        article_draft += f"# Topic: {article_topic}\n\n"
        if news_summary:
            article_draft += "## Summary of News Articles\n\n"
            article_draft += f"This section provides a summary of the news articles about {article_topic}.\n\n"
            article_draft += "<news_summary>\n\n"
            article_draft += f"{news_summary}\n\n"
            article_draft += "</news_summary>\n\n"

        with st.status("Writing Draft", expanded=True) as status:
            with st.container():
                draft_container = st.empty()
                draft_container.markdown(article_draft)
            status.update(label="Draft Complete", state="complete", expanded=False)

        article_writer = get_article_writer(model=writer_model)
        # article_writer = get_article_writer_chinese(model=writer_model)
        # article_writer = get_article_writer_chinese_out(model=writer_model)
        final_report = ""
        with st.spinner("Writing Article..."):
            final_report = ""
            final_report_container = st.empty()
            for delta in article_writer.run(article_draft):
                final_report += delta  # type: ignore
                final_report_container.markdown(final_report)

        #TODO: 数据存储Notion 翻译中文后存储
        try:
            final_report_chinese=translate_text(final_report,None)
            final_report_chinese = final_report_chinese.replace('＃＃＃', '###')
            print(final_report_chinese)
            if final_report_chinese is None:
                print('翻译失败')
                return
            pattern = re.compile(r'##\s*(.*)$', re.MULTILINE)
            matches = pattern.findall(final_report_chinese)
            title = matches[0]
            client = notion_client()
            client.create_page_blocks(page_title=title,content=final_report_chinese)
        except Exception as e:
            print(f'Notion存储异常:{e}')


    st.sidebar.markdown("---")
    if st.sidebar.button("Restart"):
        st.rerun()


main()
