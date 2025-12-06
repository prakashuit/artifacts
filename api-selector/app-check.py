"""
API Selector Application - Production-Style Prototype
A Streamlit app using LangGraph and company LLM SDK for intelligent API orchestration.

This application:
1. Accepts natural-language queries from users
2. Plans which internal APIs to call using a ReAct-style agent
3. Shows the planned sequence with reasoning (toggleable)
4. Executes the plan on user confirmation
5. Displays raw responses and AI-generated summaries

Tech Stack:
- Streamlit for UI
- LangGraph for agent orchestration
- Company LLM SDK for all reasoning
- REST APIs only (GET, POST, PUT, DELETE)
"""

import streamlit as st
import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_MODEL = "default-model"
REGISTRY_FILE_PATH = "api_registry.json"
DEFAULT_TEMPERATURE = 0.7


# ============================================================================
# COMPANY LLM SDK INTEGRATION
# ============================================================================

# Placeholder for the actual SDK client object
# In production, this would be initialized with proper credentials
class MockSDKClient:
    """Mock SDK client for demonstration. Replace with actual SDK initialization."""
    
    class completion:
        @staticmethod
        def create(model: str, prompt: str, stream: bool = False, temperature: float = 1.0, n: int = 1):
            # Mock response structure - replace with actual SDK call
            return {
                "choices": [
                    {"text": "Mock completion response"}
                ]
            }
    
    class chat:
        @staticmethod
        def create(model: str, messages: list, stream: bool = False, temperature: float = 1.0, n: int = 1, **kwargs):
            # Mock response structure - replace with actual SDK call
            return {
                "choices": [
                    {"message": {"content": "Mock chat response"}}
                ]
            }


# Initialize the SDK client - REPLACE THIS WITH ACTUAL SDK INITIALIZATION
client = MockSDKClient()


def llm_completion(prompt: str, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Wrapper for company LLM completion API.
    
    Args:
        prompt: The prompt text
        model: Model identifier
        temperature: Sampling temperature
        
    Returns:
        The completion text as a string
    """
    try:
        response = client.completion.create(
            model=model,
            prompt=prompt,
            stream=False,
            temperature=temperature,
            n=1
        )
        # Parse the response and extract text
        return response["choices"][0]["text"]
    except Exception as e:
        st.error(f"LLM Completion Error: {str(e)}")
        return ""


def llm_chat(messages: list, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Wrapper for company LLM chat API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model identifier
        temperature: Sampling temperature
        
    Returns:
        The assistant's response text as a string
    """
    try:
        response = client.chat.create(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature,
            n=1
        )
        # Parse the response and extract assistant message content
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"LLM Chat Error: {str(e)}")
        return ""


# ============================================================================
# API REGISTRY
# ============================================================================

class HttpMethod(Enum):
    """Supported HTTP methods for REST APIs."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class ApiDefinition:
    """Schema for an API definition in the registry."""
    name: str
    description: str
    url: str
    method: str  # GET, POST, PUT, DELETE
    input_schema: Dict[str, Any]  # Description of inputs
    output_schema: Dict[str, Any]  # Description of outputs
    type: str = "rest"
    tags: List[str] = None
    domain: str = ""
    example_inputs: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.example_inputs is None:
            self.example_inputs = {}


class ApiRegistry:
    """
    Manages the registry of available APIs.
    Supports in-memory operations and JSON persistence.
    """
    
    def __init__(self):
        self.apis: Dict[str, ApiDefinition] = {}
    
    def list_apis(self) -> List[ApiDefinition]:
        """Return list of all registered APIs."""
        return list(self.apis.values())
    
    def get_api_by_name(self, name: str) -> Optional[ApiDefinition]:
        """Retrieve an API definition by name."""
        return self.apis.get(name)
    
    def add_api(self, api_def: ApiDefinition) -> None:
        """Add or update an API in the registry."""
        self.apis[api_def.name] = api_def
    
    def remove_api(self, name: str) -> bool:
        """Remove an API from the registry. Returns True if removed."""
        if name in self.apis:
            del self.apis[name]
            return True
        return False
    
    def load_from_json(self, path: str) -> None:
        """Load API registry from a JSON file."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.apis = {}
                for api_dict in data.get('apis', []):
                    api_def = ApiDefinition(**api_dict)
                    self.apis[api_def.name] = api_def
        except FileNotFoundError:
            # File doesn't exist yet, start with empty registry
            pass
        except Exception as e:
            st.error(f"Error loading registry: {str(e)}")
    
    def save_to_json(self, path: str) -> None:
        """Save API registry to a JSON file."""
        try:
            data = {
                'apis': [asdict(api) for api in self.apis.values()]
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            st.error(f"Error saving registry: {str(e)}")
    
    def to_llm_context(self) -> str:
        """
        Format the registry as a string suitable for LLM context.
        Includes all relevant information for planning.
        """
        if not self.apis:
            return "No APIs currently registered."
        
        context_parts = ["Available APIs:\n"]
        for i, api in enumerate(self.apis.values(), 1):
            context_parts.append(f"\n{i}. API Name: {api.name}")
            context_parts.append(f"   Description: {api.description}")
            context_parts.append(f"   Method: {api.method}")
            context_parts.append(f"   URL: {api.url}")
            context_parts.append(f"   Domain: {api.domain}")
            context_parts.append(f"   Input Schema: {json.dumps(api.input_schema, indent=2)}")
            context_parts.append(f"   Output Schema: {json.dumps(api.output_schema, indent=2)}")
            if api.example_inputs:
                context_parts.append(f"   Example Inputs: {json.dumps(api.example_inputs, indent=2)}")
            if api.tags:
                context_parts.append(f"   Tags: {', '.join(api.tags)}")
        
        return "\n".join(context_parts)


def initialize_sample_apis() -> ApiRegistry:
    """
    Pre-populate the registry with sample investment banking APIs.
    These are mock APIs for demonstration purposes.
    """
    registry = ApiRegistry()
    
    # Trade Booking Status API
    registry.add_api(ApiDefinition(
        name="trade_booking_status",
        description="Retrieves the current booking status of trades. Returns status information including booking state, timestamps, and any errors.",
        url="https://mock-backoffice.internal/api/v1/trades/status",
        method="POST",
        input_schema={
            "trade_ids": {"type": "list[string]", "required": True, "description": "List of trade IDs to query"},
            "include_details": {"type": "boolean", "required": False, "description": "Whether to include detailed error messages"}
        },
        output_schema={
            "trades": {"type": "list[object]", "description": "List of trade status objects"},
            "status_fields": ["trade_id", "status", "booked_timestamp", "errors"]
        },
        domain="trade_lifecycle",
        tags=["trades", "booking", "status"],
        example_inputs={"trade_ids": ["TRD-2024-001", "TRD-2024-002"], "include_details": True}
    ))
    
    # Position Reconciliation API
    registry.add_api(ApiDefinition(
        name="position_reconciliation",
        description="Performs position reconciliation between internal books and external custodian. Returns breaks and discrepancies.",
        url="https://mock-backoffice.internal/api/v1/positions/reconcile",
        method="POST",
        input_schema={
            "account_id": {"type": "string", "required": True, "description": "Account identifier"},
            "as_of_date": {"type": "string", "required": True, "description": "Date for reconciliation in YYYY-MM-DD format"},
            "instrument_ids": {"type": "list[string]", "required": False, "description": "Optional list of specific instruments"}
        },
        output_schema={
            "summary": {"type": "object", "description": "Reconciliation summary with total breaks"},
            "breaks": {"type": "list[object]", "description": "List of position breaks"},
            "break_fields": ["instrument_id", "internal_quantity", "custodian_quantity", "difference"]
        },
        domain="reconciliation",
        tags=["positions", "reconciliation", "breaks"],
        example_inputs={"account_id": "ACC-12345", "as_of_date": "2024-12-06"}
    ))
    
    # Settlement Status API
    registry.add_api(ApiDefinition(
        name="settlement_status",
        description="Checks settlement status for trades. Returns settlement state, expected dates, and any failures.",
        url="https://mock-backoffice.internal/api/v1/settlements/status",
        method="GET",
        input_schema={
            "trade_ids": {"type": "list[string]", "required": False, "description": "Specific trade IDs to check"},
            "settlement_date": {"type": "string", "required": False, "description": "Filter by settlement date YYYY-MM-DD"},
            "status_filter": {"type": "string", "required": False, "description": "Filter by status: pending, settled, failed"}
        },
        output_schema={
            "settlements": {"type": "list[object]", "description": "List of settlement records"},
            "fields": ["trade_id", "settlement_status", "expected_date", "actual_date", "failure_reason"]
        },
        domain="settlement",
        tags=["settlement", "trades", "status"],
        example_inputs={"settlement_date": "2024-12-06", "status_filter": "pending"}
    ))
    
    # Corporate Actions API
    registry.add_api(ApiDefinition(
        name="corporate_actions",
        description="Lists corporate action events for instruments within a date range. Includes dividends, splits, mergers, etc.",
        url="https://mock-backoffice.internal/api/v1/corporate-actions",
        method="GET",
        input_schema={
            "instrument_ids": {"type": "list[string]", "required": False, "description": "Filter by instrument IDs"},
            "start_date": {"type": "string", "required": True, "description": "Start date YYYY-MM-DD"},
            "end_date": {"type": "string", "required": True, "description": "End date YYYY-MM-DD"},
            "event_types": {"type": "list[string]", "required": False, "description": "Filter by event types: dividend, split, merger, spinoff"}
        },
        output_schema={
            "events": {"type": "list[object]", "description": "List of corporate action events"},
            "event_fields": ["event_id", "instrument_id", "event_type", "ex_date", "payment_date", "details"]
        },
        domain="corporate_actions",
        tags=["corporate_actions", "events", "instruments"],
        example_inputs={"start_date": "2024-12-01", "end_date": "2024-12-31", "event_types": ["dividend"]}
    ))
    
    # Risk Metrics API
    registry.add_api(ApiDefinition(
        name="risk_metrics",
        description="Retrieves risk metrics snapshot for portfolios or positions. Includes VaR, Greeks, exposure metrics.",
        url="https://mock-backoffice.internal/api/v1/risk/metrics",
        method="POST",
        input_schema={
            "portfolio_ids": {"type": "list[string]", "required": False, "description": "Portfolio identifiers"},
            "account_ids": {"type": "list[string]", "required": False, "description": "Account identifiers"},
            "as_of_date": {"type": "string", "required": True, "description": "Date for risk calculation YYYY-MM-DD"},
            "metrics": {"type": "list[string]", "required": False, "description": "Specific metrics to retrieve: var, delta, gamma, vega, exposure"}
        },
        output_schema={
            "risk_data": {"type": "list[object]", "description": "Risk metrics by portfolio/account"},
            "metric_fields": ["entity_id", "var_95", "delta", "gamma", "vega", "total_exposure"]
        },
        domain="risk",
        tags=["risk", "metrics", "var", "greeks"],
        example_inputs={"portfolio_ids": ["PORT-001"], "as_of_date": "2024-12-06", "metrics": ["var", "delta"]}
    ))
    
    return registry


# ============================================================================
# HTTP EXECUTION LAYER
# ============================================================================

def execute_rest_api(api_def: ApiDefinition, resolved_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a REST API call based on the API definition and resolved inputs.
    
    Args:
        api_def: The API definition from the registry
        resolved_inputs: Dictionary of input parameters with resolved values
        
    Returns:
        Dictionary containing the response data or error information
    """
    try:
        # Build request parameters
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
            # Extension point: Add authentication headers here
            # "Authorization": f"Bearer {token}"
        }
        
        # Prepare request based on HTTP method
        method = api_def.method.upper()
        url = api_def.url
        
        if method == "GET":
            response = requests.get(url, params=resolved_inputs, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=resolved_inputs, headers=headers, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=resolved_inputs, headers=headers, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, json=resolved_inputs, headers=headers, timeout=30)
        else:
            return {"error": f"Unsupported HTTP method: {method}"}
        
        # Parse response
        response.raise_for_status()
        
        try:
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.text
            }
    
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout",
            "error_type": "timeout"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection error - could not reach API endpoint",
            "error_type": "connection"
        }
    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP error: {str(e)}",
            "status_code": response.status_code,
            "error_type": "http"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unknown",
            "traceback": traceback.format_exc()
        }


# ============================================================================
# LANGGRAPH STATE AND NODES
# ============================================================================

class AgentState(TypedDict):
    """State object passed through the LangGraph workflow."""
    user_query: str
    api_registry_context: str
    plan: List[Dict[str, Any]]
    plan_reasoning: str
    execution_results: List[Dict[str, Any]]
    final_summary: str
    error: Optional[str]


def planning_node(state: AgentState) -> AgentState:
    """
    Planning node: Uses LLM to analyze query and create execution plan.
    
    This node:
    1. Takes user query and API registry
    2. Uses LLM to determine which APIs to call and in what order
    3. Produces a structured plan with reasoning
    """
    user_query = state["user_query"]
    api_context = state["api_registry_context"]
    
    # Construct planning prompt
    planning_prompt = f"""You are an API orchestration planning agent for an investment banking back-office system.

Your task is to analyze the user's query and create a detailed execution plan using the available APIs.

{api_context}

User Query: {user_query}

Instructions:
1. Analyze the user's query to understand what information they need
2. Identify which APIs from the registry are relevant
3. Determine the optimal sequence of API calls
4. For each API call, specify:
   - Which API to call (exact name from registry)
   - Why this API is needed (reasoning)
   - What inputs to provide (and where they come from: user query, constants, or previous step outputs)
   - What outputs to expect and how they'll be used

5. Output your response in the following JSON format:
{{
  "reasoning": "Your overall reasoning and approach to solving this query",
  "plan": [
    {{
      "step": 1,
      "api_name": "exact_api_name_from_registry",
      "rationale": "Why this API is needed",
      "inputs": {{
        "param_name": {{"value": "actual_value", "source": "user_query|constant|step_N"}}
      }},
      "expected_outputs": "Description of what this step will return",
      "output_usage": "How these outputs will be used in subsequent steps or final answer"
    }}
  ]
}}

Ensure your response is valid JSON that can be parsed. Be specific about input values and their sources.
"""
    
    messages = [
        {"role": "system", "content": "You are an expert API orchestration planner. Always respond with valid JSON."},
        {"role": "user", "content": planning_prompt}
    ]
    
    try:
        llm_response = llm_chat(messages, temperature=0.3)
        
        # Parse the JSON response
        # Try to extract JSON from the response (in case LLM adds extra text)
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = llm_response[json_start:json_end]
            parsed_plan = json.loads(json_str)
        else:
            parsed_plan = json.loads(llm_response)
        
        state["plan"] = parsed_plan.get("plan", [])
        state["plan_reasoning"] = parsed_plan.get("reasoning", "")
        state["error"] = None
        
    except json.JSONDecodeError as e:
        state["error"] = f"Failed to parse LLM planning response as JSON: {str(e)}"
        state["plan"] = []
        state["plan_reasoning"] = llm_response  # Store raw response for debugging
    except Exception as e:
        state["error"] = f"Planning error: {str(e)}"
        state["plan"] = []
        state["plan_reasoning"] = ""
    
    return state


def execution_node(state: AgentState) -> AgentState:
    """
    Execution node: Executes the planned sequence of API calls.
    
    This node:
    1. Iterates through each step in the plan
    2. Resolves inputs (from user query, constants, or previous outputs)
    3. Executes the API call
    4. Stores results for use in subsequent steps
    """
    plan = state["plan"]
    execution_results = []
    
    # Storage for outputs from previous steps
    step_outputs = {}
    
    for step in plan:
        step_num = step.get("step", 0)
        api_name = step.get("api_name", "")
        
        # Get API definition from registry (passed via session state)
        api_def = st.session_state.registry.get_api_by_name(api_name)
        
        if not api_def:
            execution_results.append({
                "step": step_num,
                "api_name": api_name,
                "success": False,
                "error": f"API '{api_name}' not found in registry"
            })
            continue
        
        # Resolve inputs
        resolved_inputs = {}
        input_spec = step.get("inputs", {})
        
        for param_name, param_info in input_spec.items():
            if isinstance(param_info, dict):
                value = param_info.get("value")
                source = param_info.get("source", "constant")
                
                # Handle different sources
                if source == "constant" or source == "user_query":
                    resolved_inputs[param_name] = value
                elif source.startswith("step_"):
                    # Extract from previous step output
                    source_step = int(source.split("_")[1])
                    if source_step in step_outputs:
                        # Try to extract the value from previous step
                        resolved_inputs[param_name] = step_outputs[source_step].get("data", {})
                    else:
                        resolved_inputs[param_name] = value  # Fallback to specified value
                else:
                    resolved_inputs[param_name] = value
            else:
                resolved_inputs[param_name] = param_info
        
        # Execute API call
        result = execute_rest_api(api_def, resolved_inputs)
        
        # Store result
        execution_result = {
            "step": step_num,
            "api_name": api_name,
            "api_url": api_def.url,
            "api_method": api_def.method,
            "inputs": resolved_inputs,
            "rationale": step.get("rationale", ""),
            **result
        }
        
        execution_results.append(execution_result)
        
        # Store outputs for future steps
        if result.get("success"):
            step_outputs[step_num] = result
    
    state["execution_results"] = execution_results
    return state


def summarization_node(state: AgentState) -> AgentState:
    """
    Summarization node: Uses LLM to create human-friendly summary.
    
    This node:
    1. Takes all execution results
    2. Uses LLM to generate a natural language summary
    3. Formats the answer to directly address the user's query
    """
    user_query = state["user_query"]
    plan = state["plan"]
    execution_results = state["execution_results"]
    
    # Build context for summarization
    results_context = []
    for result in execution_results:
        results_context.append(f"\nStep {result['step']}: {result['api_name']}")
        results_context.append(f"Rationale: {result.get('rationale', 'N/A')}")
        results_context.append(f"Inputs: {json.dumps(result.get('inputs', {}), indent=2)}")
        if result.get('success'):
            results_context.append(f"Response: {json.dumps(result.get('data', {}), indent=2)}")
        else:
            results_context.append(f"Error: {result.get('error', 'Unknown error')}")
    
    results_text = "\n".join(results_context)
    
    summarization_prompt = f"""You are an AI assistant helping users understand API execution results.

User's Original Query: {user_query}

Execution Results:
{results_text}

Your task:
1. Analyze the execution results from all API calls
2. Extract key information relevant to the user's query
3. Create a clear, concise, human-friendly answer that directly addresses what the user asked
4. Highlight any important findings, metrics, or issues
5. If there were errors, explain them in simple terms
6. Format your response with appropriate structure (bullet points, sections, etc.)

Provide a comprehensive yet readable summary that a business user would understand.
"""
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that explains technical API results in business-friendly language."},
        {"role": "user", "content": summarization_prompt}
    ]
    
    try:
        summary = llm_chat(messages, temperature=0.5)
        state["final_summary"] = summary
    except Exception as e:
        state["final_summary"] = f"Error generating summary: {str(e)}"
    
    return state


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph workflow for the API selector agent.
    
    Workflow:
    Start -> Planning -> Execution -> Summarization -> End
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("planning", planning_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("summarization", summarization_node)
    
    # Define edges
    workflow.set_entry_point("planning")
    workflow.add_edge("planning", "execution")
    workflow.add_edge("execution", "summarization")
    workflow.add_edge("summarization", END)
    
    return workflow.compile()


# ============================================================================
# STREAMLIT UI
# ============================================================================

def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'registry' not in st.session_state:
        st.session_state.registry = initialize_sample_apis()
        # Try to load from file if exists
        st.session_state.registry.load_from_json(REGISTRY_FILE_PATH)
    
    if 'current_plan' not in st.session_state:
        st.session_state.current_plan = None
    
    if 'current_plan_reasoning' not in st.session_state:
        st.session_state.current_plan_reasoning = None
    
    if 'execution_results' not in st.session_state:
        st.session_state.execution_results = None
    
    if 'final_summary' not in st.session_state:
        st.session_state.final_summary = None
    
    if 'agent_graph' not in st.session_state:
        st.session_state.agent_graph = create_agent_graph()


def render_api_registry_sidebar():
    """Render the API registry management sidebar."""
    st.sidebar.title("API Registry Management")
    
    # Display current APIs
    st.sidebar.subheader("Registered APIs")
    apis = st.session_state.registry.list_apis()
    
    if apis:
        api_data = []
        for api in apis:
            api_data.append({
                "Name": api.name,
                "Method": api.method,
                "Domain": api.domain,
                "URL": api.url[:50] + "..." if len(api.url) > 50 else api.url
            })
        st.sidebar.dataframe(api_data, use_container_width=True)
    else:
        st.sidebar.info("No APIs registered yet.")
    
    # Add new API form
    st.sidebar.subheader("Add New API")
    
    with st.sidebar.form("add_api_form"):
        api_name = st.text_input("API Name*", help="Unique identifier for the API")
        api_description = st.text_area("Description*", help="What does this API do?")
        api_url = st.text_input("URL*", help="Full endpoint URL")
        api_method = st.selectbox("HTTP Method*", ["GET", "POST", "PUT", "DELETE"])
        api_domain = st.text_input("Domain", help="e.g., trades, risk, settlement")
        api_tags = st.text_input("Tags (comma-separated)", help="e.g., trades, status, booking")
        
        st.write("**Input Schema** (JSON format)")
        api_input_schema = st.text_area(
            "Input Schema",
            value='{\n  "param_name": {\n    "type": "string",\n    "required": true,\n    "description": "Parameter description"\n  }\n}',
            height=150
        )
        
        st.write("**Output Schema** (JSON format)")
        api_output_schema = st.text_area(
            "Output Schema",
            value='{\n  "field_name": {\n    "type": "string",\n    "description": "Field description"\n  }\n}',
            height=150
        )
        
        submit_button = st.form_submit_button("Add API")
        
        if submit_button:
            if not api_name or not api_description or not api_url:
                st.sidebar.error("Please fill in all required fields (marked with *).")
            else:
                try:
                    # Parse JSON schemas
                    input_schema = json.loads(api_input_schema)
                    output_schema = json.loads(api_output_schema)
                    
                    # Create API definition
                    new_api = ApiDefinition(
                        name=api_name,
                        description=api_description,
                        url=api_url,
                        method=api_method,
                        input_schema=input_schema,
                        output_schema=output_schema,
                        domain=api_domain,
                        tags=[tag.strip() for tag in api_tags.split(",")] if api_tags else []
                    )
                    
                    # Add to registry
                    st.session_state.registry.add_api(new_api)
                    st.session_state.registry.save_to_json(REGISTRY_FILE_PATH)
                    
                    st.sidebar.success(f"API '{api_name}' added successfully!")
                    st.rerun()
                    
                except json.JSONDecodeError as e:
                    st.sidebar.error(f"Invalid JSON in schema: {str(e)}")
                except Exception as e:
                    st.sidebar.error(f"Error adding API: {str(e)}")
    
    # Save/Load registry
    st.sidebar.subheader("Registry Persistence")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Save Registry", use_container_width=True):
            st.session_state.registry.save_to_json(REGISTRY_FILE_PATH)
            st.sidebar.success("Registry saved!")
    
    with col2:
        if st.button("Reload Registry", use_container_width=True):
            st.session_state.registry.load_from_json(REGISTRY_FILE_PATH)
            st.sidebar.success("Registry reloaded!")
            st.rerun()


def render_main_interface():
    """Render the main query and execution interface."""
    st.title("🤖 API Selector - Intelligent API Orchestration")
    st.markdown("Enter a natural language query, and I'll plan and execute the right sequence of API calls.")
    
    # User query input
    user_query = st.text_area(
        "Your Query",
        placeholder="Example: Show me all pending settlements for today and check if there are any position breaks for account ACC-12345",
        height=100
    )
    
    # Control buttons
    col1, col2, col3 = st.columns([2, 2, 6])
    
    with col1:
        generate_plan_button = st.button("🔍 Generate Plan", type="primary", use_container_width=True)
    
    with col2:
        execute_button = st.button(
            "▶️ Execute Plan",
            type="secondary",
            disabled=st.session_state.current_plan is None,
            use_container_width=True
        )
    
    # Generate plan
    if generate_plan_button and user_query:
        with st.spinner("Planning API calls..."):
            # Create initial state
            initial_state = {
                "user_query": user_query,
                "api_registry_context": st.session_state.registry.to_llm_context(),
                "plan": [],
                "plan_reasoning": "",
                "execution_results": [],
                "final_summary": "",
                "error": None
            }
            
            # Run only the planning node
            result_state = planning_node(initial_state)
            
            if result_state.get("error"):
                st.error(f"Planning Error: {result_state['error']}")
                st.text("Raw LLM Response:")
                st.code(result_state.get("plan_reasoning", ""), language="text")
            else:
                st.session_state.current_plan = result_state["plan"]
                st.session_state.current_plan_reasoning = result_state["plan_reasoning"]
                st.session_state.execution_results = None
                st.session_state.final_summary = None
                st.success("✅ Plan generated successfully!")
    
    # Display plan
    if st.session_state.current_plan:
        st.markdown("---")
        st.subheader("📋 Execution Plan")
        
        # Toggle for showing reasoning
        show_reasoning = st.checkbox("Show detailed reasoning", value=False)
        
        if show_reasoning and st.session_state.current_plan_reasoning:
            st.markdown("**Overall Reasoning:**")
            st.info(st.session_state.current_plan_reasoning)
        
        # Display plan steps
        for step in st.session_state.current_plan:
            with st.expander(f"Step {step.get('step', '?')}: {step.get('api_name', 'Unknown API')}", expanded=True):
                st.markdown(f"**API:** `{step.get('api_name', 'N/A')}`")
                
                if show_reasoning:
                    st.markdown(f"**Rationale:** {step.get('rationale', 'N/A')}")
                
                st.markdown("**Inputs:**")
                st.json(step.get('inputs', {}))
                
                st.markdown(f"**Expected Outputs:** {step.get('expected_outputs', 'N/A')}")
                
                if show_reasoning:
                    st.markdown(f"**Output Usage:** {step.get('output_usage', 'N/A')}")
    
    # Execute plan
    if execute_button and st.session_state.current_plan:
        with st.spinner("Executing API calls..."):
            # Create state with current plan
            execution_state = {
                "user_query": user_query,
                "api_registry_context": st.session_state.registry.to_llm_context(),
                "plan": st.session_state.current_plan,
                "plan_reasoning": st.session_state.current_plan_reasoning,
                "execution_results": [],
                "final_summary": "",
                "error": None
            }
            
            # Run execution and summarization
            execution_state = execution_node(execution_state)
            execution_state = summarization_node(execution_state)
            
            st.session_state.execution_results = execution_state["execution_results"]
            st.session_state.final_summary = execution_state["final_summary"]
            
            st.success("✅ Execution completed!")
    
    # Display results
    if st.session_state.execution_results:
        st.markdown("---")
        st.subheader("📊 Execution Results")
        
        # Display AI-generated summary first
        st.markdown("### 🎯 Summary")
        st.markdown(st.session_state.final_summary)
        
        # Display raw results
        st.markdown("### 🔍 Detailed Results")
        
        for result in st.session_state.execution_results:
            step_num = result.get('step', '?')
            api_name = result.get('api_name', 'Unknown')
            success = result.get('success', False)
            
            status_icon = "✅" if success else "❌"
            
            with st.expander(f"{status_icon} Step {step_num}: {api_name}", expanded=not success):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Method:** `{result.get('api_method', 'N/A')}`")
                    st.markdown(f"**URL:** `{result.get('api_url', 'N/A')}`")
                
                with col2:
                    st.markdown(f"**Status:** {'Success' if success else 'Failed'}")
                    if 'status_code' in result:
                        st.markdown(f"**Status Code:** `{result['status_code']}`")
                
                st.markdown("**Inputs:**")
                st.json(result.get('inputs', {}))
                
                if success:
                    st.markdown("**Response:**")
                    st.json(result.get('data', {}))
                else:
                    st.error(f"**Error:** {result.get('error', 'Unknown error')}")
                    if 'traceback' in result:
                        with st.expander("View Traceback"):
                            st.code(result['traceback'], language="python")


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="API Selector",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Render UI components
    render_api_registry_sidebar()
    render_main_interface()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "API Selector v1.0 | Powered by LangGraph & Company LLM SDK"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
