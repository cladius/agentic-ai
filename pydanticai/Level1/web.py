from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastui import FastUI, prebuilt_html, AnyComponent
from fastui.components import Div, Markdown, Page, Link, Text
from fastui.events import GoToEvent
from pydantic import BaseModel
from agent.gemini_agent import HelloWorldAgent, UserInput, AgentResponse
import logfire
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure Logfire
logfire.configure(
    token=os.getenv('LOGFIRE_TOKEN'),
    send_to_logfire=True
)

app = FastAPI()

# Define a Pydantic model for validation
class QueryForm(BaseModel):
    query: str

# Initialize the agent
try:
    with logfire.span("Initializing GeminiAgent"):
        agent = GeminiAgent()
        logfire.info("GeminiAgent initialized successfully")
except ValueError as e:
    logfire.error("Agent initialization failed", error=str(e))
    raise HTTPException(status_code=500, detail=f"Agent initialization failed: {str(e)}")

@app.get('/api/', response_model=FastUI, response_model_exclude_none=True)
def home_page() -> list[AnyComponent]:
    with logfire.span("Rendering home page"):
        try:
            components = [
                Page(
                    components=[
                        Div(
                            components=[
                                Markdown(text='# Gemini Agent'),
                                Markdown(text='Enter your question below:'),
                                Div(
                                    components=[
                                        Text(text='Query:'),
                                        Markdown(text='<form method="POST" action="/api/query"><input type="text" name="query" required><button type="submit">Submit</button></form>')
                                    ]
                                ),
                            ]
                        )
                    ]
                )
            ]
            logfire.info("Home page components generated successfully")
            return components
        except Exception as e:
            logfire.error("Failed to render home page", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to render home page: {str(e)}")

@app.post('/api/query', response_model=FastUI, response_model_exclude_none=True)
async def handle_query(query: str = Form()) -> list[AnyComponent]:
    with logfire.span("Processing query"):
        try:
            response = agent.process_query(UserInput(query=query))
            logfire.info("Query processed successfully", query=query, response=response.output)
            return [
                Page(
                    components=[
                        Markdown(text=f"**Response:** {response.output}"),
                        Div(
                            components=[
                                Markdown(text='Ask another question:'),
                                Markdown(text='<form method="POST" action="/api/query"><input type="text" name="query" required><button type="submit">Submit</button></form>')
                            ]
                        ),
                        Div(
                            components=[
                                Link(
                                    components=[Text(text='Back to Home')],
                                    on_click=GoToEvent(url='/api/')
                                )
                            ]
                        )
                    ]
                )
            ]
        except Exception as e:
            logfire.error("Error processing query", error=str(e), query=query)
            return [
                Page(
                    components=[
                        Markdown(text=f"**Error:** {str(e)}"),
                        Div(
                            components=[
                                Link(
                                    components=[Text(text='Back to Home')],
                                    on_click=GoToEvent(url='/api/')
                                )
                            ]
                        )
                    ]
                )
            ]

@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    with logfire.span("Serving HTML landing page"):
        try:
            html = prebuilt_html(title='Gemini Agent')
            logfire.info("HTML landing page served successfully")
            return HTMLResponse(html)
        except Exception as e:
            logfire.error("Failed to serve HTML landing page", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to serve HTML: {str(e)}")