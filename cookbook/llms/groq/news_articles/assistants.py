from textwrap import dedent

from phi.llm.groq import Groq
from phi.assistant import Assistant


def get_article_summarizer(
    model: str = "llama3-8b-8192",
    length: int = 500,
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="Article Summarizer",
        llm=Groq(model=model),
        description="You are a Senior NYT Editor and your task is to summarize a newspaper article.",
        instructions=[
            "You will be provided with the text from a newspaper article.",
            "Carefully read the article a prepare a thorough report of key facts and details.",
            f"Your report should be less than {length} words.",
            "Provide as many details and facts as possible in the summary.",
            "Your report will be used to generate a final New York Times worthy report.",
            "REMEMBER: you are writing for the New York Times, so the quality of the report is important.",
            "Make sure your report is properly formatted and follows the <report_format> provided below.",
        ],
        add_to_system_prompt=dedent("""
        <report_format>
        **Overview:**\n
        {overview of the article}

        **Details:**\n
        {details/facts/main points from the article}

        **Key Takeaways:**\n
        {provide key takeaways from the article}
        </report_format>
        """),
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )


def get_article_writer(
    model: str = "llama3-70b-8192",
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="Article Summarizer",
        llm=Groq(model=model),
        description="You are a Senior NYT Editor and your task is to write a NYT cover story worthy article due tomorrow.",
        instructions=[
            "You will be provided with a topic and pre-processed summaries from junior researchers.",
            "Carefully read the provided information and think about the contents",
            "Then generate a final New York Times worthy article in the <article_format> provided below.",
            "Make your article engaging, informative, and well-structured.",
            "Break the article into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Give the section relevant titles and provide details/facts/processes in each section."
            "REMEMBER: you are writing for the New York Times, so the quality of the article is important.",
        ],
        add_to_system_prompt=dedent("""
        <article_format>
        ## Engaging Article Title

        ### Overview
        {give a brief introduction of the article and why the user should read this report}
        {make this section engaging and create a hook for the reader}

        ### Section 1
        {break the article into sections}
        {provide details/facts/processes in this section}

        ... more sections as necessary...

        ### Takeaways
        {provide key takeaways from the article}

        ### References
        - [Title](url)
        - [Title](url)
        - [Title](url)
        </article_format>
        """),
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )

def get_article_writer_chinese_out(
    model: str = "llama3-70b-8192",
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="Article Summarizer",
        llm=Groq(model=model),
        description="You are a senior editor at The New York Times, and your assignment is to write a New York Times cover story in simplified Chinese, due tomorrow.",
        instructions=[
            "You will be provided with a topic and pre-processed summaries from junior researchers.",
            "Carefully read the provided information and think about the contents",
            "Then generate a final New York Times worthy article in the <article_format> provided below.",
            "Make your article engaging, informative, and well-structured.",
            "Break the article into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Give the section relevant titles and provide details/facts/processes in each section."
            "REMEMBER: you are writing for the New York Times, so the quality of the article is important.",
            "Because it's a Chinese user group, it has to be output in simplified Chinese.",

        ],
        add_to_system_prompt=dedent("""
        <article_format>
        ## Engaging Article Title

        ### Overview
        {give a brief introduction of the article and why the user should read this report}
        {make this section engaging and create a hook for the reader}

        ### Section 1
        {break the article into sections}
        {provide details/facts/processes in this section}

        ... more sections as necessary...

        ### Takeaways
        {provide key takeaways from the article}

        ### References
        - [Title](url)
        - [Title](url)
        - [Title](url)
        </article_format>
        """),
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )


def get_article_writer_chinese(
    model: str = "llama3-70b-8192",
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="文章摘要",
        llm=Groq(model=model),
        description="你是《纽约时报》的高级编辑，你的任务是用简体中文撰写一篇《纽约时报》的封面故事，明天交稿。",
        instructions=[
            "你将获得一个主题及初级研究员提供的预处理摘要。",
            "仔细阅读所提供的信息并思考内容。",
            "然后，按照下方的<文章格式>生成一篇符合《纽约时报》标准的封面故事。",
            "确保文章引人入胜、信息丰富且结构清晰。",
            "将文章分为多个章节，并在结尾提供要点总结。",
            "确保标题吸引人。",
            "为各章节设定相关的小标题，并在各章节中提供细节/事实/过程。",
            "记住：你是在为《纽约时报》写作，文章质量至关重要。",
            "因为是中国用户群体,必须要用简体中文输出"
        ],
        add_to_system_prompt=dedent("""
          <文章格式>
          ## 吸引人的文章标题

          ### 概述
          {简要介绍文章内容及为何读者应关注此报告}
          {使这部分内容吸引人，为读者设置阅读的诱因}

          ### 第一节
          {按逻辑分段落展开文章}
          {在本节提供详尽的信息/数据/论述}

          ...更多章节...

          ### 要点总结
          {总结文章的关键信息}

          ### 参考资料
          - [标题](链接)
          - [标题](链接)
          - [标题](链接)
          </文章格式>
          """),
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
