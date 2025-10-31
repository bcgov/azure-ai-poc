"""
Advanced LangGraph agent service with sophisticated reasoning capabilities.

This service provides enhanced agent workflows with:
- Multi-step reasoning and planning
- Tool chaining and orchestration
- Conditional logic and decision making
- Memory persistence and context management
- Complex workflow orchestration
"""

import json
import re
import time
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.core.logger import get_logger
from app.services.langchain_service import LangChainAIService
from app.services.langgraph_agent_service import AgentState
from app.services.mcp_tools import get_mcp_tools


def extract_json_from_text(text: str) -> dict | None:
    """Extract JSON from text that may contain additional content."""
    if not text or not isinstance(text, str):
        return None

    # Try to parse the entire text as JSON first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Look for JSON patterns in the text
    json_patterns = [
        r"\{[^{}]*\}",  # Simple JSON object
        r"\{(?:[^{}]|\{[^{}]*\})*\}",  # Nested JSON object
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    return None


class AdvancedAgentService:
    """
    Advanced LangGraph agent service with sophisticated reasoning capabilities.

    This service enhances the basic agent with:
    - Multi-step reasoning and planning
    - Tool chaining and complex workflows
    - Conditional logic and decision trees
    - Memory persistence and learning
    - Advanced error recovery
    """

    def __init__(self, langchain_service: LangChainAIService):
        """
        Initialize the advanced agent service.

        Args:
            langchain_service: LangChain service for AI completions
        """
        self.langchain_service = langchain_service
        self.logger = get_logger(__name__)

        # Available MCP tools wrapped for LangChain
        self.tools = get_mcp_tools()
        self.tool_node = ToolNode(self.tools)

        # Build the enhanced agent workflow
        self.graph = self._build_advanced_agent_graph()
        self.logger.info("Advanced LangGraph agent service initialized")

    def _build_advanced_agent_graph(self) -> StateGraph:
        """Build the advanced agent workflow graph with enhanced capabilities."""
        # Create the state graph
        graph = StateGraph(AgentState)

        # Add enhanced nodes
        graph.add_node("planner", self._planning_node)
        graph.add_node("reasoner", self._reasoning_node)
        graph.add_node("executor", self._execution_node)
        graph.add_node("tools", self.tool_node)
        graph.add_node("evaluator", self._evaluation_node)
        graph.add_node("memory_manager", self._memory_management_node)
        graph.add_node("decision_maker", self._decision_making_node)
        graph.add_node("error_recovery", self._error_recovery_node)
        graph.add_node("final_response", self._final_response_node)

        # Add complex workflow edges
        graph.add_edge(START, "planner")

        # Planning phase
        graph.add_conditional_edges(
            "planner",
            self._routing_logic,
            {"reason": "reasoner", "execute": "executor", "error": "error_recovery"},
        )

        # Reasoning phase
        graph.add_conditional_edges(
            "reasoner",
            self._reasoning_routing,
            {
                "continue_reasoning": "reasoner",
                "execute": "executor",
                "decide": "decision_maker",
                "error": "error_recovery",
            },
        )

        # Execution phase
        graph.add_conditional_edges(
            "executor",
            self._execution_routing,
            {
                "use_tools": "tools",
                "evaluate": "evaluator",
                "reason": "reasoner",
                "error": "error_recovery",
            },
        )

        # Tool usage
        graph.add_conditional_edges(
            "tools",
            self._tool_routing,
            {
                "continue_tools": "tools",
                "evaluate": "evaluator",
                "reason": "reasoner",
                "error": "error_recovery",
            },
        )

        # Evaluation phase
        graph.add_conditional_edges(
            "evaluator",
            self._evaluation_routing,
            {
                "plan_more": "planner",
                "execute_more": "executor",
                "finalize": "memory_manager",
                "error": "error_recovery",
            },
        )

        # Decision making
        graph.add_conditional_edges(
            "decision_maker",
            self._decision_routing,
            {
                "execute": "executor",
                "reason": "reasoner",
                "finalize": "memory_manager",
                "error": "error_recovery",
            },
        )

        # Memory management
        graph.add_edge("memory_manager", "final_response")

        # Error recovery
        graph.add_conditional_edges(
            "error_recovery",
            self._recovery_routing,
            {
                "retry_plan": "planner",
                "retry_reason": "reasoner",
                "retry_execute": "executor",
                "finalize": "final_response",
            },
        )

        # Final response
        graph.add_edge("final_response", END)

        # Compile the graph with increased recursion limit
        return graph.compile(
            checkpointer=None,  # No checkpointing for now
            interrupt_before=None,
            interrupt_after=None,
            debug=False,
        )

    async def _planning_node(self, state: AgentState) -> dict[str, Any]:
        """
        Advanced planning node with multi-step reasoning.
        Analyzes the request and creates a detailed execution plan.
        """
        try:
            state.step_count += 1
            self.logger.info("Starting advanced planning phase")

            # Get the latest user message
            user_messages = [msg for msg in state.messages if isinstance(msg, HumanMessage)]
            if not user_messages:
                return {"error": "No user message found", "retry_count": state.retry_count + 1}

            latest_message = user_messages[-1].content

            # Create planning prompt (avoid JSON template to prevent LangChain variable parsing)
            planning_prompt = f"""
You are an advanced AI planning agent for BC Government services. Analyze the user's request
and create a simple execution plan.

User Request: {latest_message}

IMPORTANT: You must respond ONLY with valid JSON containing these exact fields:
- main_objective: Brief description of main goal
- sub_objectives: Array of 2-3 steps
- complexity_level: "low", "medium", or "high"
- estimated_steps: Number between 1-5

Example response format:
JSON with main_objective, sub_objectives array, complexity_level string, and estimated_steps number

Do not include any text before or after the JSON."""

            # Get planning response using safe method with memory to avoid template parsing issues
            planning_response = await self.langchain_service.chat_completion_safe_with_memory(
                message=planning_prompt,
                context="Advanced agent planning",
                session_id=state.session_id,
                user_id=state.user_id,
            )

            # Parse planning response
            plan_data = extract_json_from_text(planning_response)
            if plan_data:
                return {
                    "current_objective": plan_data.get("main_objective"),
                    "sub_objectives": plan_data.get("sub_objectives", []),
                    "execution_plan": plan_data.get("execution_plan", []),
                    "working_memory": {
                        "complexity_level": plan_data.get("complexity_level", "medium"),
                        "estimated_steps": plan_data.get("estimated_steps", 3),
                        "success_criteria": plan_data.get("success_criteria", []),
                    },
                    "reasoning_steps": [
                        {
                            "step": state.step_count,
                            "phase": "planning",
                            "reasoning": (
                                f"Created execution plan with "
                                f"{len(plan_data.get('execution_plan', []))} steps"
                            ),
                            "confidence": 0.8,
                        }
                    ],
                }
            else:
                self.logger.warning("Failed to parse planning response as JSON, using fallback")
                return {
                    "current_objective": latest_message,
                    "execution_plan": [
                        {"step": 1, "action": "direct_response", "tools_needed": []}
                    ],
                    "working_memory": {"complexity_level": "low", "estimated_steps": 1},
                }

        except Exception as e:
            self.logger.error(f"Error in planning node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _reasoning_node(self, state: AgentState) -> dict[str, Any]:
        """
        Advanced reasoning node with step-by-step logical analysis.
        """
        try:
            state.step_count += 1
            self.logger.info("Starting advanced reasoning phase")

            # Get current plan step
            current_step = state.current_plan_step
            execution_plan = state.execution_plan or []

            if current_step >= len(execution_plan):
                return {"reasoning_complete": True}

            current_action = execution_plan[current_step]

            # Create reasoning prompt
            reasoning_prompt = f"""
You are performing step-by-step reasoning for a BC Government AI agent.

Current Objective: {state.current_objective}
Current Step: {current_action.get("action", "Unknown action")}
Tools Available: {current_action.get("tools_needed", [])}
Expected Outcome: {current_action.get("expected_outcome", "Not specified")}

Previous Reasoning Steps:
{json.dumps(state.reasoning_steps, indent=2)}

Current Working Memory:
{json.dumps(state.working_memory, indent=2)}

Perform detailed reasoning for this step:
1. Analyze the current situation
2. Evaluate available information
3. Determine the best approach
4. Identify any dependencies or prerequisites
5. Assess confidence level

Respond in JSON format:
{{{{
    "reasoning": "Detailed step-by-step analysis",
    "approach": "Selected approach with justification",
    "dependencies": ["dep1", "dep2"],
    "confidence": 0.85,
    "next_action": "execute|reason_more|use_tools|decide",
    "tools_to_use": ["tool1", "tool2"]
}}}}
"""

            # Get reasoning response (use clean session ID for advanced agent)
            reasoning_session_id = f"{state.session_id}-reasoning" if state.session_id else None
            reasoning_response = await self.langchain_service.chat_completion(
                message=reasoning_prompt,
                context="Advanced agent reasoning",
                session_id=reasoning_session_id,
                user_id=state.user_id,
            )

            # Parse reasoning response
            try:
                reasoning_data = json.loads(reasoning_response)

                # Add to reasoning steps
                new_reasoning_step = {
                    "step": state.step_count,
                    "phase": "reasoning",
                    "reasoning": reasoning_data.get("reasoning", ""),
                    "approach": reasoning_data.get("approach", ""),
                    "confidence": reasoning_data.get("confidence", 0.5),
                    "dependencies": reasoning_data.get("dependencies", []),
                    "timestamp": time.time(),
                }

                updated_reasoning_steps = state.reasoning_steps + [new_reasoning_step]

                return {
                    "reasoning_steps": updated_reasoning_steps,
                    "confidence_scores": {
                        f"step_{state.step_count}": reasoning_data.get("confidence", 0.5)
                    },
                    "working_memory": {
                        **state.working_memory,
                        "current_approach": reasoning_data.get("approach", ""),
                        "tools_to_use": reasoning_data.get("tools_to_use", []),
                    },
                    "next_action": reasoning_data.get("next_action", "execute"),
                }

            except json.JSONDecodeError:
                self.logger.warning("Failed to parse reasoning response as JSON")
                return {
                    "reasoning_steps": state.reasoning_steps
                    + [
                        {
                            "step": state.step_count,
                            "phase": "reasoning",
                            "reasoning": "Failed to parse detailed reasoning",
                            "confidence": 0.3,
                        }
                    ],
                    "next_action": "execute",
                }

        except Exception as e:
            self.logger.error(f"Error in reasoning node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _execution_node(self, state: AgentState) -> dict[str, Any]:
        """
        Advanced execution node with tool orchestration.
        """
        try:
            state.step_count += 1
            self.logger.info("Starting advanced execution phase")

            # Get current plan step
            current_step = state.current_plan_step
            execution_plan = state.execution_plan or []

            if current_step >= len(execution_plan):
                return {"execution_complete": True}

            current_action = execution_plan[current_step]
            tools_to_use = state.working_memory.get(
                "tools_to_use", current_action.get("tools_needed", [])
            )

            # Prepare execution
            execution_result = {
                "current_plan_step": current_step + 1,
                "tool_call_history": state.tool_call_history.copy(),
            }

            # Execute based on action type
            action_type = current_action.get("action", "")

            if "tool" in action_type.lower() and tools_to_use:
                # Prepare for tool usage
                execution_result["use_tools"] = True
                execution_result["tools_to_execute"] = tools_to_use
                return execution_result

            elif "response" in action_type.lower():
                # Direct response generation
                response_prompt = f"""
Generate a response for the BC Government user based on:

Objective: {state.current_objective}
Current Step: {current_action.get("action")}
Expected Outcome: {current_action.get("expected_outcome")}
Reasoning History: {json.dumps(state.reasoning_steps[-3:], indent=2) if state.reasoning_steps else "None"}

Provide a clear, helpful response following BC Government communication guidelines.
"""

                execution_session_id = f"{state.session_id}-execution" if state.session_id else None
                response = await self.langchain_service.chat_completion(
                    message=response_prompt,
                    context="Advanced agent execution",
                    session_id=execution_session_id,
                    user_id=state.user_id,
                )

                execution_result["final_answer"] = response
                execution_result["execution_complete"] = True

            return execution_result

        except Exception as e:
            self.logger.error(f"Error in execution node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _evaluation_node(self, state: AgentState) -> dict[str, Any]:
        """
        Evaluation node for assessing progress and quality.
        """
        try:
            state.step_count += 1
            self.logger.info("Starting evaluation phase")

            # Evaluate current progress (completely avoid JSON syntax to prevent memory corruption)
            evaluation_prompt = f"""
Evaluate the current progress of this BC Government AI agent workflow:

Objective: {state.current_objective}
Assess the progress and decide next action.

IMPORTANT: You must respond ONLY with valid JSON using this structure:
- progress_score: decimal number between 0.0 and 1.0
- objective_completion: decimal number between 0.0 and 1.0
- recommendation: one of "continue", "finalize", or "revise_plan"

Respond with JSON containing exactly those three fields. No other text.
Choose recommendation: "continue", "finalize", or "revise_plan"
"""

            evaluation_response = await self.langchain_service.chat_completion_safe_with_memory(
                message=evaluation_prompt,
                context="Advanced agent evaluation",
                session_id=state.session_id,
                user_id=state.user_id,
            )

            eval_data = extract_json_from_text(evaluation_response)
            if eval_data:
                # Get completion score and use it for smart recommendations
                completion_score = eval_data.get("objective_completion", 0.5)

                # Much more aggressive finalization logic to prevent infinite loops
                recommendation = eval_data.get("recommendation", "finalize")

                # Force finalization after just 2 steps to prevent loops
                if state.step_count >= 2:
                    recommendation = "finalize"
                # Any completion score above 0.3, finalize immediately
                elif completion_score >= 0.3:
                    recommendation = "finalize"
                # If we have any reasoning steps at all, finalize
                elif len(state.reasoning_steps) >= 1:
                    recommendation = "finalize"
                # If execution has run at least once, finalize
                elif state.working_memory.get("executed_action"):
                    recommendation = "finalize"
                # Default to finalize to prevent infinite loops
                else:
                    recommendation = "finalize"

                return {
                    "confidence_scores": {
                        **state.confidence_scores,
                        "progress": eval_data.get("progress_score", 0.5),
                        "quality": eval_data.get("quality_score", 0.5),
                        "completion": completion_score,
                    },
                    "working_memory": {
                        **state.working_memory,
                        "evaluation": eval_data,
                        "recommendation": recommendation,
                    },
                }
            else:
                # If we can't parse JSON, default to finalization to prevent infinite loops
                default_recommendation = "finalize"  # Always finalize when JSON parsing fails
                self.logger.warning(
                    f"Failed to parse evaluation JSON, defaulting to: {default_recommendation}"
                )
                return {
                    "working_memory": {
                        **state.working_memory,
                        "recommendation": default_recommendation,
                    }
                }

        except Exception as e:
            self.logger.error(f"Error in evaluation node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _decision_making_node(self, state: AgentState) -> dict[str, Any]:
        """
        Decision making node for complex conditional logic.
        """
        try:
            state.step_count += 1
            self.logger.info("Starting decision making phase")

            # Make decisions based on current state
            confidence_avg = sum(state.confidence_scores.values()) / max(
                len(state.confidence_scores), 1
            )
            progress = state.current_plan_step / max(len(state.execution_plan), 1)

            # Decision logic
            decision_point = {
                "timestamp": time.time(),
                "confidence_level": confidence_avg,
                "progress_level": progress,
                "reasoning_depth": len(state.reasoning_steps),
                "tool_usage": len(state.tool_call_history),
            }

            # Determine next action
            if confidence_avg > 0.8 and progress > 0.8:
                next_action = "finalize"
            elif confidence_avg < 0.4:
                next_action = "reason"
            elif progress < 0.5:
                next_action = "execute"
            else:
                next_action = "execute"

            return {
                "decision_points": state.decision_points + [decision_point],
                "working_memory": {
                    **state.working_memory,
                    "decision": next_action,
                    "decision_confidence": confidence_avg,
                },
            }

        except Exception as e:
            self.logger.error(f"Error in decision making node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _memory_management_node(self, state: AgentState) -> dict[str, Any]:
        """
        Memory management node for context persistence.
        """
        try:
            state.step_count += 1
            self.logger.info("Starting memory management phase")

            # Consolidate working memory
            consolidated_memory = {
                "session_summary": {
                    "objective": state.current_objective,
                    "steps_taken": state.step_count,
                    "tools_used": list(state.tool_results.keys()),
                    "avg_confidence": sum(state.confidence_scores.values())
                    / max(len(state.confidence_scores), 1),
                    "completion_status": "completed" if state.final_answer else "in_progress",
                },
                "learned_patterns": {
                    "effective_tools": [
                        tool
                        for tool, result in state.tool_results.items()
                        if "success" in str(result).lower()
                    ],
                    "reasoning_quality": len(
                        [step for step in state.reasoning_steps if step.get("confidence", 0) > 0.7]
                    ),
                    "decision_effectiveness": len(state.decision_points),
                },
            }

            return {"working_memory": {**state.working_memory, "consolidated": consolidated_memory}}

        except Exception as e:
            self.logger.error(f"Error in memory management node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _error_recovery_node(self, state: AgentState) -> dict[str, Any]:
        """
        Error recovery node with intelligent retry strategies.
        """
        try:
            state.step_count += 1
            self.logger.info(f"Starting error recovery for: {state.error}")

            # Analyze error and determine recovery strategy
            recovery_attempt = {
                "timestamp": time.time(),
                "error": state.error,
                "retry_count": state.retry_count,
                "recovery_strategy": "unknown",
            }

            # Recovery strategies based on error type
            if state.retry_count >= 3:
                recovery_attempt["recovery_strategy"] = "finalize_with_error"
                return {
                    "recovery_attempts": state.recovery_attempts + [recovery_attempt],
                    "final_answer": f"I apologize, but I encountered persistent errors while processing your request: {state.error}. Please try rephrasing your question or contact support.",
                }

            elif "tool" in str(state.error).lower():
                recovery_attempt["recovery_strategy"] = "retry_without_tools"
                return {
                    "recovery_attempts": state.recovery_attempts + [recovery_attempt],
                    "working_memory": {**state.working_memory, "avoid_tools": True},
                    "retry_count": state.retry_count + 1,
                    "error": None,
                }

            elif "reasoning" in str(state.error).lower():
                recovery_attempt["recovery_strategy"] = "simplify_reasoning"
                return {
                    "recovery_attempts": state.recovery_attempts + [recovery_attempt],
                    "working_memory": {**state.working_memory, "simple_mode": True},
                    "retry_count": state.retry_count + 1,
                    "error": None,
                }

            else:
                recovery_attempt["recovery_strategy"] = "retry_from_planning"
                return {
                    "recovery_attempts": state.recovery_attempts + [recovery_attempt],
                    "current_plan_step": 0,
                    "retry_count": state.retry_count + 1,
                    "error": None,
                }

        except Exception as e:
            self.logger.error(f"Error in recovery node: {e}")
            return {
                "final_answer": "I apologize, but I encountered multiple errors and cannot complete your request. Please try again or contact support."
            }

    async def _final_response_node(self, state: AgentState) -> dict[str, Any]:
        """
        Enhanced final response node with comprehensive summary.
        """
        try:
            # If we already have a final answer, use it
            if state.final_answer:
                return {"final_answer": state.final_answer}

            # Generate comprehensive final response
            final_prompt = f"""
Generate a comprehensive final response for this BC Government AI agent session:

Objective: {state.current_objective}
Steps Completed: {state.step_count}
Reasoning Quality: {len([step for step in state.reasoning_steps if step.get("confidence", 0) > 0.7])}/{len(state.reasoning_steps)} high-confidence steps
Tools Used: {list(state.tool_results.keys()) if state.tool_results else "None"}
Average Confidence: {sum(state.confidence_scores.values()) / max(len(state.confidence_scores), 1):.2f}

Key Insights from Reasoning:
{json.dumps([step.get("reasoning", "") for step in state.reasoning_steps[-3:]], indent=2)}

Provide a helpful, comprehensive response that:
1. Addresses the user's original request
2. Summarizes key findings
3. Provides actionable information
4. Follows BC Government communication guidelines
"""

            final_session_id = f"{state.session_id}-final" if state.session_id else None
            final_response = await self.langchain_service.chat_completion(
                message=final_prompt,
                context="Advanced agent final response",
                session_id=final_session_id,
                user_id=state.user_id,
            )

            return {"final_answer": final_response}

        except Exception as e:
            self.logger.error(f"Error in final response node: {e}")
            return {
                "final_answer": "I apologize, but I encountered an error while generating my final response. Please try again or contact support."
            }

    # Routing logic methods
    def _routing_logic(self, state: AgentState) -> str:
        """Main routing logic for the planning phase."""
        if state.error:
            return "error"
        if not state.current_objective:
            return "error"
        if state.working_memory.get("complexity_level") == "high":
            return "reason"
        return "execute"

    def _reasoning_routing(self, state: AgentState) -> str:
        """Routing logic for the reasoning phase."""
        if state.error:
            return "error"
        next_action = state.working_memory.get("decision", "execute")
        if next_action == "reason_more":
            return "continue_reasoning"
        elif next_action == "decide":
            return "decide"
        return "execute"

    def _execution_routing(self, state: AgentState) -> str:
        """Routing logic for the execution phase."""
        if state.error:
            return "error"
        if state.working_memory.get("tools_to_use"):
            return "use_tools"
        if state.current_plan_step >= len(state.execution_plan):
            return "evaluate"
        return "reason"

    def _tool_routing(self, state: AgentState) -> str:
        """Routing logic for tool usage."""
        if state.error:
            return "error"
        if state.working_memory.get("continue_tools"):
            return "continue_tools"
        return "evaluate"

    def _evaluation_routing(self, state: AgentState) -> str:
        """Routing logic for evaluation phase with better termination logic."""
        if state.error:
            return "error"

        # Force finalization if we've taken too many steps (prevent infinite loops)
        if state.step_count >= 3:  # Much more aggressive - finalize after just 3 steps
            self.logger.warning(f"Reached maximum steps ({state.step_count}), forcing finalization")
            return "finalize"

        # For testing purposes, be very aggressive about finalizing
        recommendation = state.working_memory.get("recommendation", "finalize")

        # Force finalization if we've done any execution at all
        if state.working_memory.get("executed_action"):
            return "finalize"

        # Force finalization if objective completion is any reasonable level
        evaluation_data = state.working_memory.get("evaluation", {})
        objective_completion = evaluation_data.get("objective_completion", 0.0)
        if objective_completion >= 0.3:  # Much lower threshold - 30%
            return "finalize"

        # Force finalization if we have any reasoning
        if len(state.reasoning_steps) >= 1:
            return "finalize"

        if recommendation == "continue":
            return "execute_more"
        elif recommendation == "revise_plan":
            return "plan_more"
        return "finalize"

    def _decision_routing(self, state: AgentState) -> str:
        """Routing logic for decision making."""
        if state.error:
            return "error"
        decision = state.working_memory.get("decision", "finalize")
        if decision == "reason":
            return "reason"
        elif decision == "execute":
            return "execute"
        return "finalize"

    def _recovery_routing(self, state: AgentState) -> str:
        """Routing logic for error recovery."""
        if state.final_answer:
            return "finalize"
        strategy = (
            state.recovery_attempts[-1].get("recovery_strategy", "finalize")
            if state.recovery_attempts
            else "finalize"
        )
        if strategy == "retry_from_planning":
            return "retry_plan"
        elif strategy == "simplify_reasoning":
            return "retry_reason"
        elif strategy == "retry_without_tools":
            return "retry_execute"
        return "finalize"

    async def process_advanced_message(
        self,
        message: str,
        user_id: str | None = None,
        session_id: str | None = None,
        context: str | None = None,
    ) -> str:
        """
        Process a message through the advanced agent workflow.

        Args:
            message: User message to process
            user_id: User identifier for personalization
            session_id: Session identifier for conversation history
            context: Additional context for the conversation

        Returns:
            Final response from the advanced agent
        """
        try:
            # Create initial state
            initial_state = AgentState(
                messages=[HumanMessage(content=message)],
                user_id=user_id,
                session_id=session_id,
                workflow_id=str(uuid.uuid4()),
                context=context,
            )

            self.logger.info(f"Starting advanced agent workflow for message: {message[:100]}")

            # Run the workflow with increased recursion limit
            config = {"recursion_limit": 25}  # Increased limit to allow more complex workflows
            result = await self.graph.ainvoke(initial_state, config=config)

            # Extract final answer
            final_answer = result.get("final_answer", "I'm sorry, I couldn't process your request.")

            self.logger.info(
                f"Advanced agent workflow completed in {result.get('step_count', 0)} steps"
            )

            return final_answer

        except Exception as e:
            self.logger.error(f"Error in advanced agent workflow: {e}")
            return (
                "I apologize, but I encountered an error while processing your request with advanced reasoning. "
                "Please try again or contact support if the issue persists."
            )


# Global service instance
_advanced_agent_service: AdvancedAgentService | None = None


def get_advanced_agent_service() -> AdvancedAgentService:
    """Get the global advanced agent service instance."""
    global _advanced_agent_service
    if _advanced_agent_service is None:
        from app.services.langchain_service import get_langchain_ai_service

        langchain_service = get_langchain_ai_service()
        _advanced_agent_service = AdvancedAgentService(langchain_service)
    return _advanced_agent_service
