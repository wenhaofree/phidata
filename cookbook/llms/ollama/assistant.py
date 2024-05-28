from rich.pretty import pprint
from phi.assistant import Assistant
from phi.llm.ollama import Ollama

assistant = Assistant(
    llm=Ollama(model="llama3"),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
print("\n-*- Metrics:")
pprint(assistant.llm.metrics)  # type: ignore
