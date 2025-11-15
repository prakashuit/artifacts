
import streamlit as st
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Generator
import os
from urllib.parse import urlencode
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Agentic API Orchestrator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .step-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .processing-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== VENDOR-AGNOSTIC LLM CLIENT ====================
class LLMClient:
    """
    Vendor-agnostic LLM client that supports multiple providers.
    Can be easily swapped between Anthropic, OpenAI, or custom implementations.
    """

    def __init__(self, provider: str = "anthropic", api_key: str = None, model: str = None, base_url: str = None):
        """
        Initialize LLM client

        Args:
            provider: "anthropic", "openai", "custom", or other vendors
            api_key: API key for the provider
            model: Model name (e.g., "claude-3-5-sonnet-20241022", "gpt-4", etc.)
            base_url: Base URL for custom/self-hosted providers
        """
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.model = model or os.getenv(f"{provider.upper()}_MODEL")
        self.base_url = base_url or os.getenv(f"{provider.upper()}_BASE_URL")

        if not self.api_key:
            raise ValueError(f"API key not provided for {provider}. Set {provider.upper()}_API_KEY environment variable.")

        if not self.model:
            raise ValueError(f"Model not specified for {provider}. Set {provider.upper()}_MODEL environment variable.")

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate client based on provider"""
        if self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")

        elif self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")

        elif self.provider == "custom":
            # For custom/self-hosted providers using OpenAI-compatible API
            try:
                import openai
                if not self.base_url:
                    raise ValueError("base_url required for custom provider")
                self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def plan(self, user_prompt: str, services_info: str) -> str:
        """
        Get planning response from LLM (non-streaming)

        Args:
            user_prompt: User's request
            services_info: JSON string of available services

        Returns:
            LLM response as string
        """
        system_prompt = f"""You are an API orchestration expert. Based on the user's request and available services, you must:
1. Identify which service(s) need to be called
2. Determine the order of execution (if multiple services)
3. Construct the exact URL(s) that would work in Postman
4. Provide the parameters needed

Available Services:
{services_info}

Respond in JSON format with:
{{
    "plan": "Step-by-step explanation of what will be executed",
    "services_to_call": [
        {{
            "service_key": "service_name",
            "service_name": "Display name",
            "url": "Full URL with parameters",
            "http_method": "GET/POST/PUT/DELETE",
            "parameters": {{}},
            "order": 1,
            "depends_on": null or "previous_service_key"
        }}
    ],
    "reasoning": "Why these services were chosen"
}}"""

        if self.provider == "anthropic":
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return message.content[0].text

        elif self.provider in ["openai", "custom"]:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content

    def plan_streaming(self, user_prompt: str, services_info: str) -> Generator[str, None, None]:
        """
        Get planning response from LLM with streaming

        Args:
            user_prompt: User's request
            services_info: JSON string of available services

        Yields:
            Streamed text chunks
        """
        system_prompt = f"""You are an API orchestration expert. Based on the user's request and available services, you must:
1. Identify which service(s) need to be called
2. Determine the order of execution (if multiple services)
3. Construct the exact URL(s) that would work in Postman
4. Provide the parameters needed

Available Services:
{services_info}

Respond in JSON format with:
{{
    "plan": "Step-by-step explanation of what will be executed",
    "services_to_call": [
        {{
            "service_key": "service_name",
            "service_name": "Display name",
            "url": "Full URL with parameters",
            "http_method": "GET/POST/PUT/DELETE",
            "parameters": {{}},
            "order": 1,
            "depends_on": null or "previous_service_key"
        }}
    ],
    "reasoning": "Why these services were chosen"
}}"""

        if self.provider == "anthropic":
            with self.client.messages.stream(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            ) as stream:
                for text in stream.text_stream:
                    yield text

        elif self.provider in ["openai", "custom"]:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

# Initialize session state
if "services" not in st.session_state:
    st.session_state.services = {}
if "execution_mode" not in st.session_state:
    st.session_state.execution_mode = "quick"
if "plan_result" not in st.session_state:
    st.session_state.plan_result = None
if "execution_result" not in st.session_state:
    st.session_state.execution_result = None
if "quick_mode_result" not in st.session_state:
    st.session_state.quick_mode_result = None
if "llm_client" not in st.session_state:
    st.session_state.llm_client = None

# Initialize LLM Client
@st.cache_resource
def get_llm_client(provider: str, api_key: str, model: str, base_url: str = None):
    """Get or create LLM client"""
    try:
        return LLMClient(provider=provider, api_key=api_key, model=model, base_url=base_url)
    except Exception as e:
        st.error(f"Failed to initialize LLM client: {str(e)}")
        return None

# ==================== SAMPLE SERVICES ====================
def initialize_sample_services():
    """Initialize sample services for testing"""
    sample_services = {
        "weather_service": {
            "application_name": "Weather App",
            "service_name": "Get Weather",
            "service_description": "Get current weather for a city",
            "url": "https://api.open-meteo.com/v1/forecast",
            "http_method": "GET",
            "input_parameters": ["latitude", "longitude", "current"],
            "sample_input": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "current": "temperature_2m,weather_code"
            },
            "output_parameters": ["temperature", "weather_code", "time"]
        },
        "user_service": {
            "application_name": "User Management",
            "service_name": "Get User Info",
            "service_description": "Get user information by ID",
            "url": "https://jsonplaceholder.typicode.com/users",
            "http_method": "GET",
            "input_parameters": ["user_id"],
            "sample_input": {"user_id": 1},
            "output_parameters": ["id", "name", "email", "phone", "company"]
        },
        "posts_service": {
            "application_name": "Blog Platform",
            "service_name": "Get User Posts",
            "service_description": "Get all posts by a user",
            "url": "https://jsonplaceholder.typicode.com/posts",
            "http_method": "GET",
            "input_parameters": ["userId"],
            "sample_input": {"userId": 1},
            "output_parameters": ["userId", "id", "title", "body"]
        },
        "todos_service": {
            "application_name": "Task Manager",
            "service_name": "Get User Todos",
            "service_description": "Get all todos for a user",
            "url": "https://jsonplaceholder.typicode.com/todos",
            "http_method": "GET",
            "input_parameters": ["userId"],
            "sample_input": {"userId": 1},
            "output_parameters": ["userId", "id", "title", "completed"]
        }
    }
    return sample_services

# ==================== UTILITY FUNCTIONS ====================
def construct_url(base_url: str, params: Dict[str, Any], http_method: str) -> str:
    """Construct URL with parameters"""
    if http_method.upper() == "GET":
        query_string = urlencode(params)
        return f"{base_url}?{query_string}"
    return base_url

def execute_api_call(url: str, http_method: str, data: Dict = None) -> Dict[str, Any]:
    """Execute API call"""
    try:
        if http_method.upper() == "GET":
            response = requests.get(url, timeout=10)
        elif http_method.upper() == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif http_method.upper() == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif http_method.upper() == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {"error": f"Unsupported HTTP method: {http_method}"}

        response.raise_for_status()
        return {
            "status_code": response.status_code,
            "data": response.json() if response.text else {},
            "success": True
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": str(e),
            "success": False
        }

def execute_quick_mode_agentic(user_prompt: str, services_info: str, llm_client: LLMClient):
    """Execute Quick Mode with internal agentic workflow (no user interaction)"""

    # Step 1: Plan (with streaming)
    st.markdown('<div class="processing-box"><b>🤔 Step 1: Planning...</b></div>', unsafe_allow_html=True)
    plan_placeholder = st.empty()

    full_plan_response = ""
    for chunk in llm_client.plan_streaming(user_prompt, services_info):
        full_plan_response += chunk
        plan_placeholder.markdown(f"```json\n{full_plan_response}\n```")

    try:
        plan_result = json.loads(full_plan_response)
    except json.JSONDecodeError:
        st.error("Failed to parse plan response")
        return None

    st.markdown('<div class="success-box"><b>✅ Plan created successfully!</b></div>', unsafe_allow_html=True)

    # Display plan details
    with st.expander("📋 View Plan Details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Plan:**")
            st.write(plan_result.get('plan', 'N/A'))
        with col2:
            st.write("**Reasoning:**")
            st.write(plan_result.get('reasoning', 'N/A'))

    # Step 2: Execute (automatically)
    st.markdown('<div class="processing-box"><b>⚙️ Step 2: Executing Services...</b></div>', unsafe_allow_html=True)

    services_to_call = plan_result.get('services_to_call', [])
    execution_results = {}

    for service_call in services_to_call:
        service_key = service_call.get('service_key')
        url = service_call.get('url')
        http_method = service_call.get('http_method', 'GET')

        with st.spinner(f"🔄 Executing: {service_call.get('service_name')}"):
            result = execute_api_call(url, http_method)
            execution_results[service_key] = result

            if result.get('success'):
                st.success(f"✅ {service_call.get('service_name')} completed")
            else:
                st.error(f"❌ {service_call.get('service_name')} failed: {result.get('error')}")

    st.markdown('<div class="success-box"><b>✅ All services executed!</b></div>', unsafe_allow_html=True)

    # Step 3: Present (automatically)
    st.markdown('<div class="step-header">📊 Step 3: Results</div>', unsafe_allow_html=True)

    for service_key, result in execution_results.items():
        with st.expander(f"📦 {service_key}", expanded=True):
            if result.get('success'):
                st.json(result.get('data'))
            else:
                st.error(result.get('error'))

    return {
        "plan": plan_result,
        "execution_results": execution_results
    }

# ==================== MAIN UI ====================
st.markdown('<div class="main-header">🤖 Agentic API Orchestrator</div>', unsafe_allow_html=True)

# Sidebar for LLM Configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # LLM Provider Selection
    with st.expander("🔌 LLM Provider Settings", expanded=True):
        provider = st.selectbox(
            "Select LLM Provider",
            ["anthropic", "openai", "custom"],
            help="Choose your LLM provider. Can be easily swapped!"
        )

        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder=f"Enter {provider.upper()} API key",
            help=f"Your {provider.upper()} API key"
        )

        model = st.text_input(
            "Model Name",
            placeholder="e.g., claude-3-5-sonnet-20241022 or gpt-4",
            help="Specify the model to use"
        )

        if provider == "custom":
            base_url = st.text_input(
                "Base URL",
                placeholder="e.g., http://localhost:8000/v1",
                help="Base URL for custom/self-hosted LLM provider"
            )
        else:
            base_url = None

        if st.button("✅ Initialize LLM Client", use_container_width=True):
            if api_key and model:
                st.session_state.llm_client = get_llm_client(provider, api_key, model, base_url)
                if st.session_state.llm_client:
                    st.success(f"✅ Connected to {provider.upper()} with model: {model}")
                    st.rerun()
            else:
                st.error("Please provide API key and model name")

    st.divider()

    # Service Management
    st.header("⚙️ Service Management")

    # Load sample services
    if st.button("📥 Load Sample Services", use_container_width=True):
        st.session_state.services = initialize_sample_services()
        st.success("Sample services loaded!")
        st.rerun()

    st.divider()

    # Add new service
    with st.expander("➕ Add New Service", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            app_name = st.text_input("Application Name")
            service_name = st.text_input("Service Name")
            service_desc = st.text_area("Service Description")

        with col2:
            url = st.text_input("Service URL")
            http_method = st.selectbox("HTTP Method", ["GET", "POST", "PUT", "DELETE"])

        input_params = st.text_area("Input Parameters (comma-separated)", placeholder="param1,param2,param3")
        sample_input = st.text_area("Sample Input (JSON)", placeholder='{"param1": "value1"}')
        output_params = st.text_area("Output Parameters (comma-separated)", placeholder="output1,output2")

        if st.button("Add Service", use_container_width=True):
            if all([app_name, service_name, url, http_method]):
                service_key = service_name.lower().replace(" ", "_")
                st.session_state.services[service_key] = {
                    "application_name": app_name,
                    "service_name": service_name,
                    "service_description": service_desc,
                    "url": url,
                    "http_method": http_method,
                    "input_parameters": [p.strip() for p in input_params.split(",") if p.strip()],
                    "sample_input": json.loads(sample_input) if sample_input else {},
                    "output_parameters": [p.strip() for p in output_params.split(",") if p.strip()]
                }
                st.success(f"Service '{service_name}' added!")
                st.rerun()
            else:
                st.error("Please fill all required fields")

    st.divider()

    # View services
    if st.session_state.services:
        st.subheader("📋 Registered Services")
        for key, service in st.session_state.services.items():
            with st.expander(f"🔹 {service['service_name']}"):
                st.write(f"**App:** {service['application_name']}")
                st.write(f"**Description:** {service['service_description']}")
                st.write(f"**URL:** {service['url']}")
                st.write(f"**Method:** {service['http_method']}")
                st.write(f"**Input Params:** {', '.join(service['input_parameters'])}")
                st.write(f"**Output Params:** {', '.join(service['output_parameters'])}")

                if st.button(f"🗑️ Delete", key=f"delete_{key}", use_container_width=True):
                    del st.session_state.services[key]
                    st.rerun()

# Main content area
if not st.session_state.llm_client:
    st.warning("⚠️ Please configure LLM provider in the sidebar first!")
elif not st.session_state.services:
    st.info("👈 Please load or add services from the sidebar to get started!")
else:
    # Execution mode selection
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚡ Quick Mode (1-Step Agentic)", use_container_width=True,
                     type="primary" if st.session_state.execution_mode == "quick" else "secondary"):
            st.session_state.execution_mode = "quick"
            st.rerun()

    with col2:
        if st.button("🧠 Agentic Mode (3-Step Manual)", use_container_width=True,
                     type="primary" if st.session_state.execution_mode == "agentic" else "secondary"):
            st.session_state.execution_mode = "agentic"
            st.rerun()

    st.divider()

    # ==================== QUICK MODE (AGENTIC - AUTOMATIC) ====================
    if st.session_state.execution_mode == "quick":
        st.markdown('<div class="step-header">⚡ Quick Mode - Automatic Agentic Execution</div>', unsafe_allow_html=True)
        st.write("**Description:** Enter your request and the agent will automatically plan, execute, and present results in one click!")

        # User prompt
        user_prompt = st.text_area(
            "📝 Describe what you want to do:",
            placeholder="e.g., Get user information for user ID 1 and their posts",
            height=100,
            key="quick_mode_prompt"
        )

        if st.button("🚀 Execute (Automatic)", use_container_width=True, type="primary"):
            if not user_prompt:
                st.error("Please enter a prompt")
            else:
                services_info = json.dumps(st.session_state.services, indent=2)
                st.session_state.quick_mode_result = execute_quick_mode_agentic(
                    user_prompt, 
                    services_info, 
                    st.session_state.llm_client
                )

    # ==================== AGENTIC MODE (MANUAL 3-STEP) ====================
    else:
        st.markdown('<div class="step-header">🧠 Agentic Mode - Manual 3-Step Workflow</div>', unsafe_allow_html=True)
        st.write("**Description:** Control each step manually with button clicks for more control over the process.")

        # User prompt
        user_prompt = st.text_area(
            "📝 Describe what you want to do:",
            placeholder="e.g., Get user information for user ID 1 and their posts",
            height=100,
            key="agentic_mode_prompt"
        )

        col1, col2, col3 = st.columns(3)

        # Step 1: Plan
        with col1:
            if st.button("📋 Step 1: Plan", use_container_width=True, type="primary"):
                if not user_prompt:
                    st.error("Please enter a prompt")
                else:
                    with st.spinner("🤔 Planning with AI..."):
                        services_info = json.dumps(st.session_state.services, indent=2)

                        # Show streaming response
                        placeholder = st.empty()
                        full_response = ""

                        for chunk in st.session_state.llm_client.plan_streaming(user_prompt, services_info):
                            full_response += chunk
                            placeholder.markdown(f"```json\n{full_response}\n```")

                        try:
                            st.session_state.plan_result = json.loads(full_response)
                            st.markdown('<div class="success-box"><b>✅ Plan created successfully!</b></div>', unsafe_allow_html=True)
                        except json.JSONDecodeError:
                            st.error("Failed to parse plan response")

        # Step 2: Execute
        with col2:
            if st.button("⚙️ Step 2: Execute", use_container_width=True, type="primary",
                        disabled=st.session_state.plan_result is None):
                if st.session_state.plan_result:
                    with st.spinner("⏳ Executing services..."):
                        services_to_call = st.session_state.plan_result.get('services_to_call', [])
                        execution_results = {}

                        for service_call in services_to_call:
                            service_key = service_call.get('service_key')
                            url = service_call.get('url')
                            http_method = service_call.get('http_method', 'GET')

                            st.write(f"🔄 Executing: {service_call.get('service_name')}")

                            result = execute_api_call(url, http_method)
                            execution_results[service_key] = result

                            if result.get('success'):
                                st.success(f"✅ {service_call.get('service_name')} completed")
                            else:
                                st.error(f"❌ {service_call.get('service_name')} failed: {result.get('error')}")

                        st.session_state.execution_result = execution_results
                        st.markdown('<div class="success-box"><b>✅ All services executed!</b></div>', unsafe_allow_html=True)

        # Step 3: Present
        with col3:
            if st.button("📊 Step 3: Present", use_container_width=True, type="primary",
                        disabled=st.session_state.execution_result is None):
                if st.session_state.execution_result:
                    st.markdown('<div class="step-header">📊 Results</div>', unsafe_allow_html=True)

                    for service_key, result in st.session_state.execution_result.items():
                        with st.expander(f"📦 {service_key}", expanded=True):
                            if result.get('success'):
                                st.json(result.get('data'))
                            else:
                                st.error(result.get('error'))

        # Display plan if available
        if st.session_state.plan_result:
            st.divider()
            st.markdown('<div class="step-header">📋 Current Plan</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.write("**Plan:**")
                st.write(st.session_state.plan_result.get('plan', 'N/A'))

            with col2:
                st.write("**Reasoning:**")
                st.write(st.session_state.plan_result.get('reasoning', 'N/A'))

            st.write("**Services to Call:**")
            for service_call in st.session_state.plan_result.get('services_to_call', []):
                with st.expander(f"🔹 {service_call.get('service_name')} (Order: {service_call.get('order')})"):
                    st.write(f"**URL:** `{service_call.get('url')}`")
                    st.write(f"**Method:** {service_call.get('http_method')}")
                    st.write(f"**Parameters:** {json.dumps(service_call.get('parameters'), indent=2)}")
                    if service_call.get('depends_on'):
                        st.info(f"⚠️ Depends on: {service_call.get('depends_on')}")

st.divider()
st.caption("🚀 Agentic API Orchestrator v3.0 | Vendor-Agnostic LLM Integration")
