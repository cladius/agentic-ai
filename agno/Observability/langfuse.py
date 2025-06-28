import base64
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.yfinance import YFinanceTools
from openinference.instrumentation.agno import AgnoInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
# Set environment variables for Langfuse tracing
LANGFUSE_AUTH = base64.b64encode(
    f"{os.getenv('LANGFUSE_PUBLIC_KEY')}:{os.getenv('LANGFUSE_SECRET_KEY')}".encode()
).decode()
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://us.cloud.langfuse.com/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

# Configure the tracer provider
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace_api.set_tracer_provider(tracer_provider=tracer_provider)

# Start instrumenting agno
AgnoInstrumentor().instrument()

# Create and configure the agent
agent = Agent(
    name="Stock Price Agent",
    model=Gemini(),
    tools=[YFinanceTools()],
    instructions="You are a stock price agent. Answer questions in the style of a stock analyst.",
    debug_mode=True,
)

# Use the agent
agent.print_response("What is the current price of Tesla?")
