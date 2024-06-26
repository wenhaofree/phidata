import nest_asyncio
from typing import Optional

import streamlit as st
from duckduckgo_search import DDGS
from phi.tools.newspaper4k import Newspaper4k
from phi.utils.log import logger

from assistants import get_article_summarizer, get_article_writer  # type: ignore

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

    def create_page_blocks(self, page_title,content,image_url,categorize):
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
                },
                '文章类型':{
                    "select": {
                        "name": categorize
                    }
                },
                "Tags": {
                    "multi_select": [
                        {
                            "name": '初始化'
                        }
                    ]
                },
                "图片文件": {
                    "files": [
                        {
                            "name": "文件1",
                            "type": "external",
                            "external": {
                                "url": str(image_url)
                            }
                        }
                    ]
                },
                
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

 #领域判断:
def categorize_string(input_str):
    if 'Tech' in input_str:
        return '科技'
    elif 'NBA' in input_str:
        return '体育'
    else:
        return '未知'  # Or return None, or raise an exception, depending on your needs


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
        image_results = []
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
                        image_results.append(news_result["image"])
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
        
        
        categorize = categorize_string(article_topic)
        print(categorize)
        #TODO: 数据存储Notion 翻译中文后存储
        try:
            image_url=''
            for image in image_results:
                if image.startswith('http'):
                    image_url=image
                    break      
            if len(image_url)==0:
                print('没有图片')
                return
            image_url=f'![Image]({image_url})'
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
            final_report_chinese_ok = ""
            final_report_chinese_ok +=image_url
            final_report_chinese_ok +='\n\n'
            final_report_chinese_ok +=final_report_chinese
            client.create_page_blocks(page_title=title,content=final_report_chinese_ok,image_url=image_url,categorize=categorize)
        except Exception as e:
            print(f'Notion存储异常:{e}')


    st.sidebar.markdown("---")
    if st.sidebar.button("Restart"):
        st.rerun()


# def test():
#     client = notion_client()
#     title="test"
#     # image_url=f'![Image](https://9to5mac.com/wp-content/uploads/sites/6/2024/01/Security-Bite-FI-1.png?w=1600)'
#     image_url=f'![Image](https://prod-files-secure.s3.us-west-2.amazonaws.com/b0012720-ccd1-41ef-9ca9-02f55a45f30f/3516c3c5-f7d2-415f-93d2-684c02cb1300/Untitled.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=AKIAT73L2G45HZZMZUHI%2F20240508%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20240508T152400Z&X-Amz-Expires=3600&X-Amz-Signature=ee700820721eb30c586ecb1a5d5f9b72ae3eed29a1f7fb16c2730ba415bad7ad&X-Amz-SignedHeaders=host&x-id=GetObject)'
#     final_report_chinese='''## Apple iPad Pro M4: Revolutionizing Mobile Productivity and AI Capabilities ### Overview
#     On May 7, 2024, Apple unveiled its latest iPad Pro models, powered by the groundbreaking M4 chip. This new chip brings significant advancements in CPU, GPU, and AI capabilities, making it a game-changer for mobile productivity and AI applications. In this article, we'll delve into the features, benefits, and implications of the M4 chip and the new iPad Pro models.

#     '''
#     final_report_chinese_ok = ""
#     final_report_chinese_ok +=image_url
#     final_report_chinese_ok +='\n\n'
#     final_report_chinese_ok +=final_report_chinese
#     client.create_page_blocks(page_title=title,content=final_report_chinese_ok,image_url=image_url)

main()
# test()
