from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.google import Gemini

assistant = Assistant(
    name="Finance Assistant",
    llm=Gemini(model="gemini-1.5-pro"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    instructions=["Format your response using markdown and use tables to display data where possible."],
    # debug_mode=True,
)
assistant.print_response("Share the NVDA stock price and analyst recommendations", markdown=True)
# assistant.print_response("Summarize fundamentals for TSLA", markdown=True)
