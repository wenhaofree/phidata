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
        print(categorize)
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
            # client.create_page_blocks(page_title=title,content=final_report_chinese_ok,image_url=image_url,categorize=categorize)

            article_summarizer_now = get_article_summarizer_now(model=summary_model, length=per_article_summary_length)
            _summary: str = article_summarizer_now.run(final_report, stream=False)
            _summary_chinese=translate_text(_summary,None)

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

def test():
    text='''
## **华硕推出 Vivobook S 15：首款配备 Qualcomm Snapdragon X Elite 处理器的 Copilot+ PC**

### **概述**
华硕通过推出该公司首款 Copilot+ PC 笔记本电脑 Vivobook S 15，在人工智能驱动的计算领域取得了重大飞跃。这款笔记本电脑由 Qualcomm Snapdragon X Elite 处理器提供支持，有望彻底改变我们与设备交互的方式。凭借其时尚的设计、令人印象深刻的规格和创新功能，Vivobook S 15 必将改变移动计算领域的游戏规则。

### **设计和规格**
Vivobook S 15 采用全金属设计，配备 15.6 英寸 OLED 显示屏，分辨率为 2,880 x 1,620，刷新率为 120 Hz。这款笔记本电脑重量仅为 3.13 磅，非常适合忙碌的人们。它配备 16GB 或 32GB RAM 选项以及用于板载存储的 1TB SSD。此外，它还具有用于额外存储的 microSD 读卡器、HDMI、两个 USB-A 端口和两个 USB-C 端口。一次充电电池续航时间预计可达 18 小时。

### **创新功能**
Vivobook S 15 不仅仅是一台笔记本电脑，它还是通往人工智能体验新世界的门户。凭借高通 Snapdragon X Elite 处理器，该设备能够提供无与伦比的性能和功能。它支持 Microsoft 的 Copilot+ 功能，包括 Recall、Windows 照片中的 AI 升级、用于视频通话的增强型 Windows Studio 效果以及实时字幕。该笔记本电脑还具有自适应屏幕调光和锁定系统、带有两个风扇、两个热管和两个排气口的冷却系统。

### **供货情况和定价**
华硕 Vivobook S 15 现已接受预订，起价为 1,300 美元。该设备将彻底改变移动计算世界，它的上市标志着人工智能个人电脑的发展向前迈出了重要一步。

### **外卖**

* Asus Vivobook S 15 是首款 Copilot+ PC 笔记本电脑，标志着人工智能计算领域向前迈出了重要一步。
* 这款笔记本电脑采用全金属设计、令人印象深刻的规格以及自适应屏幕调光和锁定系统等创新功能。
* 该设备搭载 Qualcomm Snapdragon X Elite 处理器，提供无与伦比的性能和功能。
* Vivobook S 15 现已接受预订，起价为 1,300 美元。

### **参考**
- [华硕 Vivobook S 15 笔记本电脑将成为该公司首款 Copilot+ PC 笔记本电脑](https://www.neowin.net/news/the-asus-vivobook-s-15-laptop-will-be-the-companys-第一副驾驶电脑笔记本/)
- [华硕将 Snapdragon X 芯片引入其 Vivobook S 15 OLED 半高端笔记本电脑系列](https://liliputing.com/asus-brings-snapdragon-x-chips-to-is-vivobook-s-15-oled -半高级笔记本电脑系列/)
- [这是第一批搭载高通 Snapdragon X 系列芯片的“Copilot+”个人电脑](https://www.thurrott.com/a-i/302760/here-are-the-first-copilot-pcs-powered-by-qualcomms -snapdragon-x-系列芯片）
- [Copilot+ 电脑简介](https://blogs.microsoft.com/blog/2024/05/20/introducing-copilot-pcs/)
'''
    # {'page_id': '6c9cb446-5715-453e-a59b-74e327fe9b96', 'page_picture': {'name': 'Integromat', 'type': 'external', 'external': {'url': 'https://media.bleacherreport.com/image/upload/c_fill,g_faces,w_3800,h_2000,q_95/v1716224915/ewqar7jtqbjsruak1b4o.jpg'}}, 'page_title': 'Paul Pierce Suffered Horrific Finger Injury After 45-Pound Weight Fell During Workout'}
    title='这是测试'
    page_id='6c9cb446-5715-453e-a59b-74e327fe9b96'
    page_picture='https://media.bleacherreport.com/image/upload/c_fill,g_faces,w_3800,h_2000,q_95/v1716224915/ewqar7jtqbjsruak1b4o.jpg'
    client = notion_client()
    if client.update_page_blocks(page_id=page_id,page_title=title,page_content=text,picture_url=page_picture):
            content='总结性内容'
            # content=news_summary
            client.update_page_content(page_id, title, "格式化",content)

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
    print(content)
    page_title=content['page_title']
    page_id=content['page_id']
    page_picture=content['page_picture']
    page_picture_url=page_picture['external']['url']
    program_start=True
    main(page_id,page_title,program_start,page_picture_url)

if __name__ == '__main__':
    # test()
    # main()
    main_pro()