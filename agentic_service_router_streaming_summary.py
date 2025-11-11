"""
Agentic Service Router with ReAct Pattern, Streaming & AI Summarization
Implements Reasoning + Acting loop with live streaming and intelligent summaries
"""

import streamlit as st
import json
import requests
from typing import Any, Dict, List, Optional, Tuple, Generator
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging
from enum import Enum
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import re
import time
from queue import Queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS & DATA MODELS
# ============================================================================

class StepType(Enum):
    """Type of step in the orchestration"""
    REASONING = "reasoning"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL_ANSWER = "final_answer"


class ActionType(Enum):
    """Type of action to perform"""
    EXECUTE_SERVICE = "execute_service"
    ANALYZE_RESULT = "analyze_result"
    COMBINE_RESULTS = "combine_results"
    EXTRACT_PARAMS = "extract_params"


@dataclass
class StreamEvent:
    """Event to stream to UI"""
    event_type: str
    step_number: int
    step_type: Optional[str] = None
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "event_type": self.event_type,
            "step_number": self.step_number,
            "step_type": self.step_type,
            "content": self.content,
            "data": self.data,
            "timestamp": self.timestamp
        }


@dataclass
class ServiceConfig:
    """Configuration for a REST service"""
    id: str
    name: str
    url: str
    http_type: str
    description: str
    input_params: List[str]
    output_params: List[str]
    headers: Optional[Dict[str, str]] = None
    auth_token: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class ExecutionResult:
    """Result of service execution"""
    service_name: str
    status: str
    data: Any
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class OrchestrationStep:
    """Single step in the orchestration process"""
    step_number: int
    step_type: StepType
    action_type: Optional[ActionType] = None
    reasoning: Optional[str] = None
    action: Optional[Dict[str, Any]] = None
    observation: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"

    def to_dict(self):
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "action_type": self.action_type.value if self.action_type else None,
            "reasoning": self.reasoning,
            "action": self.action,
            "observation": self.observation,
            "result": self.result,
            "timestamp": self.timestamp,
            "status": self.status
        }


@dataclass
class OrchestrationTrace:
    """Complete trace of orchestration execution"""
    user_prompt: str
    steps: List[OrchestrationStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    summary: Optional[str] = None
    total_steps: int = 0
    execution_time: float = 0.0
    status: str = "pending"
    error: Optional[str] = None

    def add_step(self, step: OrchestrationStep):
        """Add a step to the trace"""
        self.steps.append(step)
        self.total_steps = len(self.steps)

    def to_dict(self):
        return {
            "user_prompt": self.user_prompt,
            "steps": [step.to_dict() for step in self.steps],
            "final_answer": self.final_answer,
            "summary": self.summary,
            "total_steps": self.total_steps,
            "execution_time": self.execution_time,
            "status": self.status,
            "error": self.error
        }


# ============================================================================
# SERVICE MANAGER
# ============================================================================

class ServiceManager:
    """Manages service configurations and execution"""

    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}

    def add_service(self, config: ServiceConfig):
        """Add a service configuration"""
        self.services[config.id] = config
        logger.info(f"Service added: {config.name}")

    def remove_service(self, service_id: str):
        """Remove a service configuration"""
        if service_id in self.services:
            del self.services[service_id]
            logger.info(f"Service removed: {service_id}")

    def get_service(self, service_id: str) -> Optional[ServiceConfig]:
        """Get a service by ID"""
        return self.services.get(service_id)

    def list_services(self) -> List[ServiceConfig]:
        """List all services"""
        return list(self.services.values())

    def get_service_by_name(self, name: str) -> Optional[ServiceConfig]:
        """Get a service by name"""
        for service in self.services.values():
            if service.name.lower() == name.lower():
                return service
        return None

    def execute_service(
        self,
        service_id: str,
        params: Dict[str, Any],
        timeout: int = 10
    ) -> ExecutionResult:
        """Execute a service with given parameters"""
        service = self.get_service(service_id)
        if not service:
            return ExecutionResult(
                service_name="Unknown",
                status="error",
                data=None,
                error=f"Service {service_id} not found"
            )

        try:
            url = service.url
            headers = service.headers or {}

            if service.auth_token:
                headers["Authorization"] = f"Bearer {service.auth_token}"

            if service.http_type == "GET":
                query_params = {k: v for k, v in params.items() if k in service.input_params}
                response = requests.get(url, params=query_params, headers=headers, timeout=timeout)
            elif service.http_type == "POST":
                response = requests.post(url, json=params, headers=headers, timeout=timeout)
            elif service.http_type == "PUT":
                response = requests.put(url, json=params, headers=headers, timeout=timeout)
            elif service.http_type == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return ExecutionResult(
                    service_name=service.name,
                    status="error",
                    data=None,
                    error=f"Unsupported HTTP method: {service.http_type}"
                )

            response.raise_for_status()
            data = response.json()

            if service.output_params:
                if isinstance(data, list):
                    filtered_data = [
                        {k: v for k, v in item.items() if k in service.output_params}
                        for item in data
                    ]
                else:
                    filtered_data = {k: v for k, v in data.items() if k in service.output_params}
            else:
                filtered_data = data

            return ExecutionResult(
                service_name=service.name,
                status="success",
                data=filtered_data
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Service execution failed: {str(e)}")
            return ExecutionResult(
                service_name=service.name,
                status="error",
                data=None,
                error=str(e)
            )


# ============================================================================
# STREAMING REACT AGENT WITH SUMMARIZATION
# ============================================================================

class StreamingReactServiceAgent:
    """
    ReAct Agent with real-time streaming and AI-powered summarization
    """

    def __init__(self, service_manager: ServiceManager, api_key: str, max_steps: int = 10):
        self.service_manager = service_manager
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=api_key,
            temperature=0
        )
        self.max_steps = max_steps
        self.current_trace: Optional[OrchestrationTrace] = None
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.event_queue: Queue = Queue()

    def _emit_event(self, event: StreamEvent):
        """Emit an event to the stream"""
        self.event_queue.put(event)
        logger.info(f"Event emitted: {event.event_type} - Step {event.step_number}")

    def _get_services_description(self) -> str:
        """Get formatted description of all available services"""
        services = self.service_manager.list_services()
        if not services:
            return "No services available"

        services_info = []
        for service in services:
            info = f"""
Service Name: {service.name}
Description: {service.description}
URL: {service.url}
HTTP Method: {service.http_type}
Input Parameters: {', '.join(service.input_params)}
Output Parameters: {', '.join(service.output_params)}
"""
            services_info.append(info)

        return "\n".join(services_info)

    def _create_react_prompt(self, user_prompt: str, observations: str = "") -> str:
        """Create ReAct prompt for the agent"""
        services_desc = self._get_services_description()

        prompt = f"""You are an intelligent service orchestration agent using ReAct (Reasoning + Acting) pattern.

Your task is to help the user by orchestrating calls to available services.

Available Services:
{services_desc}

User Request: {user_prompt}

{observations}

You must follow this format strictly:

Thought: [Your reasoning about what to do next]
Action: [The action to take - either EXECUTE_SERVICE, ANALYZE_RESULT, or FINAL_ANSWER]
Action Input: [JSON with details about the action]

If Action is EXECUTE_SERVICE:
  Action Input should be: {{"service_name": "...", "params": {{...}}}}

If Action is ANALYZE_RESULT:
  Action Input should be: {{"analysis": "..."}}

If Action is FINAL_ANSWER:
  Action Input should be: {{"answer": "..."}}

Think step by step. Execute services one at a time. After each service execution, analyze the result before deciding next steps.
"""
        return prompt

    def _parse_agent_response(self, response: str) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
        """Parse agent response to extract thought, action, and action input"""
        try:
            thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', response, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else None

            action_match = re.search(r'Action:\s*(.+?)(?=Action Input:|$)', response, re.DOTALL)
            action = action_match.group(1).strip() if action_match else None

            action_input_match = re.search(r'Action Input:\s*(\{.+?\})', response, re.DOTALL)
            action_input = None
            if action_input_match:
                try:
                    action_input = json.loads(action_input_match.group(1))
                except json.JSONDecodeError:
                    action_input = {"raw": action_input_match.group(1)}

            return thought, action, action_input

        except Exception as e:
            logger.error(f"Error parsing agent response: {str(e)}")
            return None, None, None

    def _execute_action(self, action: str, action_input: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """Execute the action specified by the agent"""
        try:
            if action == "EXECUTE_SERVICE":
                service_name = action_input.get("service_name")
                params = action_input.get("params", {})

                self._emit_event(StreamEvent(
                    event_type="action",
                    step_number=step_number,
                    content=f"Executing service: {service_name}",
                    data={"service": service_name, "params": params}
                ))

                service = self.service_manager.get_service_by_name(service_name)
                if not service:
                    return {
                        "status": "error",
                        "error": f"Service '{service_name}' not found"
                    }

                result = self.service_manager.execute_service(service.id, params)
                self.execution_results[service_name] = result

                return {
                    "status": result.status,
                    "service": result.service_name,
                    "data": result.data,
                    "error": result.error
                }

            elif action == "ANALYZE_RESULT":
                analysis = action_input.get("analysis", "")
                self._emit_event(StreamEvent(
                    event_type="action",
                    step_number=step_number,
                    content=f"Analyzing results",
                    data={"analysis": analysis}
                ))
                return {
                    "status": "success",
                    "analysis": analysis
                }

            elif action == "FINAL_ANSWER":
                answer = action_input.get("answer", "")
                self._emit_event(StreamEvent(
                    event_type="final_answer",
                    step_number=step_number,
                    content=answer,
                    data={"answer": answer}
                ))
                return {
                    "status": "success",
                    "final_answer": answer
                }

            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {action}"
                }

        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _generate_summary(self, user_prompt: str, execution_results: Dict[str, ExecutionResult]) -> str:
        """Generate AI-powered summary of all collected data"""
        try:
            # Prepare data for summarization
            collected_data = {}
            for service_name, result in execution_results.items():
                if result.status == "success":
                    collected_data[service_name] = result.data

            if not collected_data:
                return "No data was collected from services."

            summary_prompt = f"""You are a helpful assistant that summarizes data collected from multiple services.

User's Original Request: {user_prompt}

Data Collected from Services:
{json.dumps(collected_data, indent=2, default=str)}

Please provide a comprehensive, well-structured summary that:
1. Directly answers the user's request
2. Highlights the most important information
3. Presents data in a clear, readable format
4. Uses bullet points or sections where appropriate
5. Avoids technical jargon
6. Is concise but complete
7. Provides actionable insights if applicable

Format the response in markdown for better readability. Use headers, bold text, and lists to make it visually appealing."""

            response = self.llm.invoke([HumanMessage(content=summary_prompt)])
            return response.content

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Unable to generate summary. Raw data available in execution history."

    def process_prompt_streaming(self, user_prompt: str) -> Generator[StreamEvent, None, OrchestrationTrace]:
        """
        Process user prompt using ReAct pattern with streaming
        Yields events as they happen
        Returns final trace with summary
        """
        import time
        start_time = time.time()

        self.current_trace = OrchestrationTrace(user_prompt=user_prompt)
        self.current_trace.status = "in_progress"
        self.execution_results = {}

        observations = ""
        step_count = 0

        try:
            while step_count < self.max_steps:
                step_count += 1

                # ===== STEP 1: REASONING =====
                self._emit_event(StreamEvent(
                    event_type="step_started",
                    step_number=step_count,
                    step_type="reasoning",
                    content="🤔 Agent is thinking..."
                ))

                reasoning_step = OrchestrationStep(
                    step_number=step_count,
                    step_type=StepType.REASONING,
                    status="in_progress"
                )
                self.current_trace.add_step(reasoning_step)

                # Get agent's reasoning
                react_prompt = self._create_react_prompt(user_prompt, observations)
                response = self.llm.invoke([HumanMessage(content=react_prompt)])
                response_text = response.content

                thought, action, action_input = self._parse_agent_response(response_text)

                reasoning_step.reasoning = thought
                reasoning_step.status = "completed"

                # Emit reasoning event
                self._emit_event(StreamEvent(
                    event_type="reasoning",
                    step_number=step_count,
                    content=thought,
                    data={"thought": thought}
                ))

                # ===== STEP 2: ACTION =====
                if action:
                    action_step = OrchestrationStep(
                        step_number=step_count + 1,
                        step_type=StepType.ACTION,
                        action_type=ActionType[action.upper().replace("-", "_")] if action.upper().replace("-", "_") in ActionType.__members__ else None,
                        action={"type": action, "input": action_input},
                        status="in_progress"
                    )
                    self.current_trace.add_step(action_step)

                    # Execute the action
                    action_result = self._execute_action(action, action_input or {}, step_count + 1)
                    action_step.result = action_result
                    action_step.status = "completed"

                    # ===== STEP 3: OBSERVATION =====
                    observation_step = OrchestrationStep(
                        step_number=step_count + 2,
                        step_type=StepType.OBSERVATION,
                        observation=action_result,
                        status="completed"
                    )
                    self.current_trace.add_step(observation_step)

                    # Emit observation event
                    self._emit_event(StreamEvent(
                        event_type="observation",
                        step_number=step_count + 2,
                        content="Observation received",
                        data=action_result
                    ))

                    # Update observations for next iteration
                    observations += f"\nObservation: {json.dumps(action_result, indent=2)}"

                    # Check if we have a final answer
                    if action == "FINAL_ANSWER":
                        self.current_trace.final_answer = action_result.get("final_answer")
                        self.current_trace.status = "completed"
                        break

                    step_count += 2

                else:
                    reasoning_step.status = "failed"
                    self.current_trace.status = "failed"
                    self.current_trace.error = "Failed to parse agent response"
                    self._emit_event(StreamEvent(
                        event_type="error",
                        step_number=step_count,
                        content="Failed to parse agent response"
                    ))
                    break

        except Exception as e:
            logger.error(f"Error in ReAct loop: {str(e)}")
            self.current_trace.status = "failed"
            self.current_trace.error = str(e)
            self._emit_event(StreamEvent(
                event_type="error",
                step_number=step_count,
                content=f"Error: {str(e)}"
            ))

        # Generate summary
        if self.current_trace.status == "completed" and self.execution_results:
            self._emit_event(StreamEvent(
                event_type="step_started",
                step_number=step_count + 1,
                content="📝 Generating AI summary..."
            ))

            summary = self._generate_summary(user_prompt, self.execution_results)
            self.current_trace.summary = summary

            self._emit_event(StreamEvent(
                event_type="summary",
                step_number=step_count + 1,
                content=summary,
                data={"summary": summary}
            ))

        self.current_trace.execution_time = time.time() - start_time

        # Emit completion event
        self._emit_event(StreamEvent(
            event_type="step_completed",
            step_number=step_count,
            content="Orchestration complete",
            data={"status": self.current_trace.status}
        ))

        return self.current_trace


# ============================================================================
# STREAMLIT UI WITH STREAMING & SUMMARIZATION
# ============================================================================

def initialize_session_state():
    """Initialize Streamlit session state"""
    if "service_manager" not in st.session_state:
        st.session_state.service_manager = ServiceManager()
        _add_default_services(st.session_state.service_manager)

    if "agent" not in st.session_state:
        st.session_state.agent = None

    if "execution_traces" not in st.session_state:
        st.session_state.execution_traces = []

    if "current_trace" not in st.session_state:
        st.session_state.current_trace = None

    if "streaming_active" not in st.session_state:
        st.session_state.streaming_active = False


def _add_default_services(manager: ServiceManager):
    """Add default services for demo"""
    default_services = [
        ServiceConfig(
            id="weather_service",
            name="Weather Service",
            url="https://api.open-meteo.com/v1/forecast",
            http_type="GET",
            description="Get weather forecast for a location (requires latitude, longitude)",
            input_params=["latitude", "longitude", "current"],
            output_params=["current", "timezone"]
        ),
        ServiceConfig(
            id="user_service",
            name="User Service",
            url="https://jsonplaceholder.typicode.com/users",
            http_type="GET",
            description="Get user information by ID",
            input_params=["id"],
            output_params=["id", "name", "email", "phone", "company"]
        ),
        ServiceConfig(
            id="post_service",
            name="Post Service",
            url="https://jsonplaceholder.typicode.com/posts",
            http_type="GET",
            description="Get posts by user ID",
            input_params=["userId"],
            output_params=["id", "title", "body", "userId"]
        ),
        ServiceConfig(
            id="comment_service",
            name="Comment Service",
            url="https://jsonplaceholder.typicode.com/comments",
            http_type="GET",
            description="Get comments by post ID",
            input_params=["postId"],
            output_params=["id", "name", "email", "body"]
        ),
    ]

    for service in default_services:
        manager.add_service(service)


def render_streaming_executor():
    """Render the streaming agent executor"""
    st.subheader("🤖 ReAct Agent Executor (Streaming + Summarization)")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write("**Enter your request (can be multi-step):**")
        user_prompt = st.text_area(
            "Natural Language Prompt",
            placeholder="e.g., 'Get user 1 details, then get their posts, then get comments on their first post'",
            height=120,
            label_visibility="collapsed"
        )

        if st.button("▶️ Execute ReAct Agent (Streaming)", use_container_width=True, type="primary"):
            if not user_prompt:
                st.error("Please enter a prompt")
            elif not st.session_state.agent:
                st.error("OpenAI API key not configured. Please add it in the sidebar.")
            else:
                st.session_state.streaming_active = True
                st.rerun()

    with col2:
        st.write("**Available Services:**")
        services = st.session_state.service_manager.list_services()
        for service in services:
            with st.expander(service.name, expanded=False):
                st.write(f"📝 {service.description}")
                st.write(f"🔗 `{service.url}`")
                st.write(f"📥 Input: {', '.join(service.input_params)}")
                st.write(f"📤 Output: {', '.join(service.output_params)}")

    # Streaming execution
    if st.session_state.streaming_active and user_prompt:
        st.divider()
        st.write("### 📊 Live Execution Stream")

        # Create containers for streaming
        stream_container = st.container()
        metrics_container = st.container()

        with metrics_container:
            col1, col2, col3, col4 = st.columns(4)
            metric_step = col1.empty()
            metric_status = col2.empty()
            metric_time = col3.empty()
            metric_services = col4.empty()

        with stream_container:
            stream_placeholder = st.empty()

        # Summary container
        summary_placeholder = st.empty()

        # Process with streaming
        trace = None
        step_count = 0
        events_log = []

        try:
            for event in st.session_state.agent.process_prompt_streaming(user_prompt):
                events_log.append(event)
                step_count += 1

                # Update metrics
                metric_step.metric("Current Step", event.step_number)
                metric_status.metric("Status", event.event_type.upper())

                # Build display content
                display_content = ""
                for evt in events_log:
                    icon_map = {
                        "step_started": "🔄",
                        "reasoning": "🤔",
                        "action": "⚡",
                        "observation": "👁️",
                        "final_answer": "✅",
                        "error": "❌",
                        "step_completed": "🏁",
                        "summary": "📝"
                    }
                    icon = icon_map.get(evt.event_type, "📍")

                    if evt.event_type == "reasoning":
                        display_content += f"\n{icon} **Step {evt.step_number} - Thought:**\n> {evt.content}\n"
                    elif evt.event_type == "action":
                        display_content += f"\n{icon} **Step {evt.step_number} - Action:**\n"
                        if evt.data:
                            display_content += f"```json\n{json.dumps(evt.data, indent=2)}\n```\n"
                    elif evt.event_type == "observation":
                        display_content += f"\n{icon} **Step {evt.step_number} - Observation:**\n"
                        if evt.data:
                            display_content += f"```json\n{json.dumps(evt.data, indent=2)}\n```\n"
                    elif evt.event_type == "final_answer":
                        display_content += f"\n{icon} **Final Answer:**\n> {evt.content}\n"
                    elif evt.event_type == "error":
                        display_content += f"\n{icon} **Error:** {evt.content}\n"
                    elif evt.event_type == "summary":
                        # Display summary separately
                        with summary_placeholder.container():
                            st.success("### ✅ AI-Generated Summary")
                            st.markdown(evt.content)

                # Update stream display
                with stream_placeholder.container():
                    st.markdown(display_content)

                # Small delay for visual effect
                time.sleep(0.1)

            # Get final trace
            trace = st.session_state.agent.current_trace

        except Exception as e:
            st.error(f"Error during streaming: {str(e)}")

        # Store trace
        if trace:
            st.session_state.execution_traces.append(trace)
            st.session_state.current_trace = trace

            # Final metrics
            with metrics_container:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Steps", trace.total_steps)
                col2.metric("Status", trace.status.upper())
                col3.metric("Execution Time", f"{trace.execution_time:.2f}s")
                successful = sum(1 for s in trace.steps if s.status == "completed")
                col4.metric("Completed", successful)

        st.session_state.streaming_active = False


def render_service_config():
    """Render the service configuration tab"""
    st.subheader("⚙️ Service Configuration")

    with st.expander("➕ Add New Service", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            service_name = st.text_input("Service Name")
            service_url = st.text_input("Service URL")
            service_desc = st.text_area("Description", height=80)

        with col2:
            http_method = st.selectbox("HTTP Method", ["GET", "POST", "PUT", "DELETE"])
            input_params = st.text_input("Input Parameters (comma-separated)")
            output_params = st.text_input("Output Parameters (comma-separated)")

        if st.button("Add Service", use_container_width=True):
            if service_name and service_url:
                new_service = ServiceConfig(
                    id=service_name.lower().replace(" ", "_"),
                    name=service_name,
                    url=service_url,
                    http_type=http_method,
                    description=service_desc,
                    input_params=[p.strip() for p in input_params.split(",") if p.strip()],
                    output_params=[p.strip() for p in output_params.split(",") if p.strip()]
                )
                st.session_state.service_manager.add_service(new_service)
                st.success(f"✅ Service '{service_name}' added successfully!")
                st.rerun()
            else:
                st.error("Please fill in Service Name and URL")

    st.write("**Configured Services:**")
    services = st.session_state.service_manager.list_services()

    if not services:
        st.info("No services configured yet. Add one above!")
    else:
        for service in services:
            col1, col2 = st.columns([4, 1])

            with col1:
                with st.expander(f"📌 {service.name}"):
                    st.write(f"**ID:** `{service.id}`")
                    st.write(f"**URL:** `{service.url}`")
                    st.write(f"**Method:** `{service.http_type}`")
                    st.write(f"**Description:** {service.description}")
                    st.write(f"**Input Params:** {', '.join(service.input_params) or 'None'}")
                    st.write(f"**Output Params:** {', '.join(service.output_params) or 'None'}")

            with col2:
                if st.button("🗑️", key=f"delete_{service.id}", help="Delete service"):
                    st.session_state.service_manager.remove_service(service.id)
                    st.success("Service deleted!")
                    st.rerun()


def render_execution_history():
    """Render execution history tab"""
    st.subheader("📋 Execution History")

    if not st.session_state.execution_traces:
        st.info("No executions yet. Try the ReAct Agent Executor!")
    else:
        for idx, trace in enumerate(reversed(st.session_state.execution_traces)):
            with st.expander(
                f"Execution #{len(st.session_state.execution_traces) - idx} - {trace.status.upper()}",
                expanded=False
            ):
                st.write(f"**Prompt:** {trace.user_prompt}")
                st.write(f"**Steps:** {trace.total_steps}")
                st.write(f"**Time:** {trace.execution_time:.2f}s")

                if trace.summary:
                    st.success("**AI Summary:**")
                    st.markdown(trace.summary)

                if trace.final_answer:
                    st.info(f"**Final Answer:** {trace.final_answer}")

                if trace.error:
                    st.error(f"**Error:** {trace.error}")

                # Show detailed steps
                with st.expander("View Detailed Steps"):
                    for step in trace.steps:
                        step_icon = {
                            StepType.REASONING: "🤔",
                            StepType.ACTION: "⚡",
                            StepType.OBSERVATION: "👁️",
                            StepType.FINAL_ANSWER: "✅"
                        }.get(step.step_type, "📍")

                        with st.expander(f"{step_icon} Step {step.step_number}: {step.step_type.value.upper()}"):
                            if step.reasoning:
                                st.write("**Thought:**")
                                st.info(step.reasoning)
                            if step.action:
                                st.write("**Action:**")
                                st.json(step.action)
                            if step.observation:
                                st.write("**Observation:**")
                                st.json(step.observation)


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="ReAct Service Router (Streaming + Summary)",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stTabs [data-baseweb="tab-list"] button { font-size: 1.1rem; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    initialize_session_state()

    # Header
    st.title("🤖 ReAct Service Router")
    st.markdown("Multi-step orchestration with real-time streaming & AI summarization")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        api_key = st.text_input("OpenAI API Key", type="password", help="Required for agent execution")

        if api_key:
            if not st.session_state.agent:
                st.session_state.agent = StreamingReactServiceAgent(
                    st.session_state.service_manager,
                    api_key,
                    max_steps=10
                )
                st.success("✅ API Key configured!")
            else:
                st.session_state.agent.llm.api_key = api_key

        st.divider()

        max_steps = st.slider("Max Steps", min_value=3, max_value=20, value=10)
        if st.session_state.agent:
            st.session_state.agent.max_steps = max_steps

        st.divider()
        st.write("**Statistics:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Services", len(st.session_state.service_manager.list_services()))
        with col2:
            st.metric("Executions", len(st.session_state.execution_traces))
        with col3:
            if st.session_state.execution_traces:
                completed = sum(1 for t in st.session_state.execution_traces if t.status == "completed")
                st.metric("Success", completed)

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🤖 ReAct Executor", "⚙️ Service Config", "📋 History"])

    with tab1:
        render_streaming_executor()

    with tab2:
        render_service_config()

    with tab3:
        render_execution_history()


if __name__ == "__main__":
    main()
