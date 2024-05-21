import nest_asyncio
from typing import Optional
import datetime
import requests

import streamlit as st
from duckduckgo_search import DDGS
from phi.tools.newspaper4k import Newspaper4k
from phi.utils.log import logger

from assistants import get_article_summarizer, get_article_writer ,get_article_summarizer_now # type: ignore

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
        # global_database_id = "3ad7d67332a34988868dcdfb03630387"  # 采集-关键字新闻
        global_database_id = "9fb048dac6c04399b9e5280d9248fe30"  # 【🔥采集-科技新闻Techmeme】
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

    def update_page_blocks(self, page_id, page_title, page_content, picture_url):
            BLOCK_ID = page_id
            headers = {
                "Authorization": f"Bearer secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            }
            data = {
                "children": [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": page_title}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external":
                                {
                                    "url": picture_url
                                }
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": page_content,
                                    }
                                }
                            ]
                        }
                    }
                ]
            }

            # Make the PATCH request
            url = f"https://api.notion.com/v1/blocks/{BLOCK_ID}/children"
            response = requests.patch(url, headers=headers, json=data)
            if response.status_code != 200:
                print(response.text)
                return False
            return True
    def update_page_content(self, page_id, title, properties_params,content):
            # 更新页面的属性
            update_payload = {
                "properties": {
                    '标题': {
                        'title': [
                            {
                                'text': {
                                    'content': title
                                }
                            }
                        ]
                    },
                    "Tags": {
                        "multi_select": [
                            {
                                "name": properties_params
                            }
                        ]
                    },
                    '正文内容': {
                        'rich_text': [
                            {
                                'text': {
                                    'content': content
                                }
                            }
                        ]
                    },
                    # 其他属性更新
                },
            }
            # 执行更新操作
            update_page = global_notion.pages.update(page_id=page_id, **update_payload)
            print("更新状态", properties_params)

    def query_results_by_condication(self, params: str, start_cursor=None):
        if start_cursor:
            response = global_notion.databases.query(
                **{
                    "database_id": global_database_id,
                    "start_cursor": start_cursor,
                    "filter": {
                        "and": [
                            {
                                "property": '发布时间',
                                "date": {
                                    "after": params
                                }
                            },
                            {
                                "property": 'Tags',
                                "multi_select": {
                                    "contains": '初始化'
                                }
                            }
                        ]
                    }
                }
            )
        else:
            response = global_notion.databases.query(
                **{
                    "database_id": global_database_id,
                    "filter": {
                        "and": [
                            {
                                "property": '发布时间',
                                "date": {
                                    "after": params
                                }
                            },
                            {
                                "property": 'Tags',
                                "multi_select": {
                                    "contains": '初始化'
                                }
                            }
                        ]
                    }
                }
            )
        # 获取结果和下一页的cursor
        results = response['results']
        next_cursor = response.get('next_cursor')
        return results, next_cursor


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


def main(page_id:None,page_title:None,program_start:None,page_picture_url:None) -> None:
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
        # value="Hashicorp IBM",
        value=f'{page_title}',
    )
    if page_title is not None:
        article_topic=page_title
        
    write_article = st.button("Write Article")
    if program_start:
        write_article=True

    if write_article:
        image_results = []
        news_results = []
        news_summary: Optional[str] = None
        ddgs = DDGS()
        newspaper_tools = Newspaper4k()
        results = ddgs.news(keywords=article_topic, max_results=num_search_results)
        for r in results:
            if "url" in r:
                article_data = newspaper_tools.get_article_data(r["url"])
                if article_data and "text" in article_data:
                    r["text"] = article_data["text"]
                    news_results.append(r)


        if len(news_results) > 0:
            print(f"Found {len(news_results)} articles")
            # 执行新闻摘要
            image_results = []
            news_summary = ""
            article_summarizer = get_article_summarizer(model=summary_model, length=per_article_summary_length)

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
                if len(news_summary.split()) > news_summary_length:
                    logger.info(f"Stopping news summary at length: {len(news_summary.split())}")
                    break


        if news_summary is None:
            return



        article_draft = ""
        article_draft += f"# Topic: {article_topic}\n\n"
        if news_summary:
            article_draft += "## Summary of News Articles\n\n"
            article_draft += f"This section provides a summary of the news articles about {article_topic}.\n\n"
            article_draft += "<news_summary>\n\n"
            article_draft += f"{news_summary}\n\n"
            article_draft += "</news_summary>\n\n"


        article_writer = get_article_writer(model=writer_model)
        # article_writer = get_article_writer_chinese(model=writer_model)
        # article_writer = get_article_writer_chinese_out(model=writer_model)
        final_report = ""
        for delta in article_writer.run(article_draft):
            final_report += delta  # type: ignore
        
        
        categorize = categorize_string(article_topic)
        # print(categorize)
        #TODO: 数据存储Notion 翻译中文后存储  更新正文
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
            # print(final_report_chinese)
            if final_report_chinese is None:
                print('翻译失败')
                return
            pattern = re.compile(r'##\s*(.*)$', re.MULTILINE)
            matches = pattern.findall(final_report_chinese)
            title = matches[0]
            print(f'标题:{title}')
            client = notion_client()
            final_report_chinese_ok = ""
            final_report_chinese_ok +=image_url
            final_report_chinese_ok +='\n\n'
            final_report_chinese_ok +=final_report_chinese
            # client.create_page_blocks(page_title=title,content=final_report_chinese_ok,image_url=image_url,categorize=categorize)

            article_summarizer_now = get_article_summarizer_now(model=summary_model, length=per_article_summary_length)
            _summary: str = article_summarizer_now.run(final_report, stream=False)
            _summary_chinese=translate_text(_summary,None)
            _summary_chinese = _summary_chinese.replace('＃＃＃', '###')

            if len(final_report_chinese_ok)<2500:
                final_report_chinese_ok=final_report_chinese_ok[:2000] #长度限制

            if client.update_page_blocks(page_id=page_id,page_title=title,page_content=final_report_chinese_ok,picture_url=page_picture_url):
                print("更新成功")
                content=_summary_chinese
                client.update_page_content(page_id, title, "格式化",content)
        except Exception as e:
            print(f'Notion存储异常:{e}')

# main()
def get_yesterday():
    # 获取当前时间
    current_time = datetime.datetime.now()
    # 计算前一天的时间
    yesterday = current_time - datetime.timedelta(days=3)
    formatted_time = yesterday.strftime("%Y-%m-%d 00:00:00")
    print(formatted_time)
    return formatted_time

def general_article(client, params: str):
    results, next_cursor = client.query_results_by_condication(params, start_cursor=None)
    for page in results:
        if page["object"] == "page":
            # 1. 过滤
            page_tags = page["properties"]["Tags"]["multi_select"]
            tag_flag = False
            for item in page_tags:
                if item['name'] in ['格式化']:
                    tag_flag = True
                    break
            if tag_flag:
                continue
            page_id = page["id"]
            page_title = page["properties"]['标题']['title'][0]['plain_text']
            page_picture = page["properties"]['图片文件']['files'][0]
            content = {
                "page_id": page_id,
                'page_picture': page_picture,
                "page_title": page_title,
            }
            return content
    return None, None
def main_pro():
    '''
    1. 查询
    2. 生成文章
    3. 更新内容+状态
    '''
    client = notion_client()
     # 1. 获取数据-三天内
    day = get_yesterday()
    content=general_article(client=client,params=day)
    page_title=content['page_title']
    print(f'page_title:{page_title}')
    page_id=content['page_id']
    page_picture=content['page_picture']
    page_picture_url=page_picture['external']['url']
    program_start=True
    main(page_id,page_title,program_start,page_picture_url)

if __name__ == '__main__':
    # test()
    # main()
    main_pro()