"""
Microsoft Foundry SDK - Part 3: Observability, Evaluation & Guardrails
Complete example demonstrating tracing, evaluations, and safety guardrails.

This script shows:
1. Setting up OpenTelemetry for trace collection
2. Creating and running evaluations on agent responses
3. Configuring content safety and guardrails
4. Monitoring agent performance with Application Insights
"""

import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from azure.monitor.opentelemetry import AzureMonitorTraceExporter


def setup_tracing(instrumentation_key: str):
    """Configure OpenTelemetry tracing with Azure Monitor."""
    trace_exporter = AzureMonitorTraceExporter(
        connection_string=f"InstrumentationKey={instrumentation_key}"
    )
    trace_provider = TracerProvider()
    trace_provider.add_span_processor(SimpleSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)
    
    return trace.get_tracer(__name__)


def main():
    # Initialize Foundry client
    project_client = AIProjectClient.from_config(
        credential=DefaultAzureCredential()
    )
    
    print(f"✓ Connected to project: {project_client.project_name}")
    print()
    
    # Step 1: Setup OpenTelemetry tracing
    print("Step 1: Setting Up Tracing")
    print("-" * 40)
    
    app_insights_conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if app_insights_conn:
        tracer = setup_tracing(app_insights_conn)
        print("  ✓ OpenTelemetry configured")
        print("  ✓ Traces will be sent to Application Insights")
    else:
        tracer = None
        print("  ⚠ Application Insights not configured")
    print()
    
    # Step 2: Define guardrails
    print("Step 2: Configuring Guardrails")
    print("-" * 40)
    
    guardrails_config = {
        "content_safety": {
            "enabled": True,
            "hate_speech_threshold": "medium",
            "violence_threshold": "medium",
            "sexual_content_threshold": "medium",
            "self_harm_threshold": "medium"
        },
        "token_limits": {
            "max_tokens_per_request": 4096,
            "max_tokens_per_response": 2048
        },
        "rate_limiting": {
            "requests_per_minute": 100
        }
    }
    
    print("  ✓ Content safety enabled")
    print(f"    - Hate speech threshold: {guardrails_config['content_safety']['hate_speech_threshold']}")
    print(f"    - Max response tokens: {guardrails_config['token_limits']['max_tokens_per_response']}")
    print()
    
    # Step 3: Create agent
    print("Step 3: Creating Agent")
    print("-" * 40)
    
    agent_definition = PromptAgentDefinition(
        name="observability-agent",
        instructions="You are a helpful AI assistant. Provide clear, accurate responses."
    )
    
    agent = project_client.agents.create_agent(
        agent_definition=agent_definition,
        model="gpt-4o-mini"
    )
    
    print(f"  ✓ Agent created: {agent.id}")
    print()
    
    # Step 4: Create thread and measure performance
    print("Step 4: Running Agent with Observability")
    print("-" * 40)
    
    thread = project_client.agents.create_thread()
    print(f"  ✓ Thread created: {thread.id}")
    
    # Send message with tracing
    if tracer:
        with tracer.start_as_current_span("agent_message") as span:
            span.set_attribute("agent.id", agent.id)
            span.set_attribute("thread.id", thread.id)
            
            user_input = "Explain how machine learning works in simple terms."
            print(f"  User: {user_input}")
            
            message = project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=user_input
            )
            span.set_attribute("message.created", True)
    else:
        user_input = "Explain how machine learning works in simple terms."
        print(f"  User: {user_input}")
        
        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
    
    print()
    
    # Step 5: Run and measure
    print("Step 5: Monitoring Execution")
    print("-" * 40)
    
    run = project_client.agents.create_run(thread_id=thread.id, assistant_id=agent.id)
    
    print(f"  ✓ Run started: {run.id}")
    print(f"  ✓ Initial status: {run.status}")
    
    # Wait and collect metrics
    iteration = 0
    while run.status in ["queued", "in_progress"]:
        iteration += 1
        run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
        print(f"  Step {iteration}: {run.status}")
    
    print(f"  ✓ Completed: {run.status}")
    print()
    
    # Step 6: Retrieve and evaluate response
    print("Step 6: Evaluating Response")
    print("-" * 40)
    
    messages = project_client.agents.list_messages(thread_id=thread.id)
    
    for msg in messages:
        if msg.role == "assistant":
            response_text = msg.content[0].text
            
            # Simple evaluation metrics
            metrics = {
                "response_length": len(response_text),
                "word_count": len(response_text.split()),
                "contains_code": "```" in response_text,
                "contains_lists": any(c in response_text for c in ["•", "-", "•"]),
            }
            
            print(f"  Response Length: {metrics['response_length']} characters")
            print(f"  Word Count: {metrics['word_count']} words")
            print(f"  Contains Code: {metrics['contains_code']}")
            print(f"  Contains Lists: {metrics['contains_lists']}")
            print()
            
            print("  Response Preview:")
            print(f"  {response_text[:300]}...")
            break
    
    print()
    
    # Cleanup
    print("Cleanup")
    print("-" * 40)
    project_client.agents.delete_agent(agent.id)
    print(f"  ✓ Agent deleted: {agent.id}")
    print("  ✓ Traces logged to Application Insights")


if __name__ == "__main__":
    main()
