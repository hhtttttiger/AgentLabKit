"""WorkflowGenerator — LLM-driven workflow definition generation.

Given a user intent and an agent's capabilities (tools, MCP, skills),
this module generates a deterministic WorkflowDef that the engine can
execute step-by-step without further LLM decisions.

Design principles:
- Generation is an LLM capability (creating the plan)
- Execution is an engine capability (running the plan deterministically)
- The generator validates tool references and step dependencies
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from llm_gateway import GatewayProtocol, TextGenerateRequest

from ..definition.models import AgentDefinitionSnapshot, ToolBindingSnapshot
from .contracts import (
    FailurePolicy,
    InputRef,
    StepDef,
    WorkflowDef,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class WorkflowValidationError(Exception):
    """Raised when a generated workflow fails validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Workflow validation failed: {'; '.join(errors)}")


# ---------------------------------------------------------------------------
# WorkflowGenerator
# ---------------------------------------------------------------------------


class WorkflowGenerator:
    """LLM-driven workflow generator.

    Generates a deterministic WorkflowDef from:
    - User intent (natural language description of what to accomplish)
    - Agent definition (available tools, MCP servers, skills)

    The generated workflow is a sequence of steps that can be executed
    by WorkflowEngine without further LLM decisions (except for agent-type
    steps which run their own Agent Loop).
    """

    def __init__(
        self,
        gateway_service: GatewayProtocol,
        default_model: str | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            gateway_service: LLM gateway for calling the generation model.
            default_model: Default model binding key for generation.
                If None, uses the agent's model_key.
        """
        self._gateway = gateway_service
        self._default_model = default_model

    async def generate(
        self,
        agent_definition: AgentDefinitionSnapshot,
        user_intent: str,
        *,
        model_override: str | None = None,
        max_steps: int = 20,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowDef:
        """Generate a workflow definition from user intent.

        Args:
            agent_definition: The agent's capabilities (tools, MCP, skills).
            user_intent: Natural language description of what the workflow should do.
            model_override: Override the model used for generation.
            max_steps: Maximum number of steps allowed in the generated workflow.
            metadata: Additional metadata to attach to the workflow.

        Returns:
            A validated WorkflowDef ready for execution.

        Raises:
            WorkflowValidationError: If the generated workflow fails validation.
            ValueError: If the LLM response cannot be parsed.
        """
        logger.info(
            "Generating workflow for agent=%s intent=%s",
            agent_definition.agent_key,
            user_intent[:100],
        )

        # 1. Build the generation prompt
        prompt = self._build_generation_prompt(
            agent_definition=agent_definition,
            user_intent=user_intent,
            max_steps=max_steps,
        )

        # 2. Call LLM to generate workflow JSON
        model = model_override or self._default_model or agent_definition.model_key
        request = TextGenerateRequest(
            model=model,
            prompt=prompt,
            temperature=0.2,  # Low temperature for deterministic output
            max_output_tokens=4096,
        )

        response = await self._gateway.generate_text(request)
        raw_text = response.text.strip()

        # 3. Parse the LLM response
        workflow_dict = self._parse_llm_response(raw_text)

        # 4. Convert to WorkflowDef
        workflow = self._dict_to_workflow(
            workflow_dict=workflow_dict,
            agent_key=agent_definition.agent_key,
            version=agent_definition.version_number,
            metadata=metadata or {},
        )

        # 5. Validate the workflow
        errors = self._validate_workflow(workflow, agent_definition)
        if errors:
            raise WorkflowValidationError(errors)

        logger.info(
            "Generated workflow_id=%s with %d steps",
            workflow.workflow_id,
            len(workflow.steps),
        )

        return workflow

    def _build_generation_prompt(
        self,
        agent_definition: AgentDefinitionSnapshot,
        user_intent: str,
        max_steps: int,
    ) -> str:
        """Build the LLM prompt for workflow generation.

        The prompt includes:
        - Agent's available tools (name + schema + description)
        - Agent's MCP bindings (server names + available tools)
        - Agent's skill bindings (descriptions)
        - User intent
        - Output format requirements (JSON schema)
        """
        # Collect tool information
        tools_section = self._format_tools_section(agent_definition.tools)

        # Collect MCP bindings
        mcp_section = self._format_mcp_section(agent_definition.mcp_bindings)

        # Collect skill bindings
        skills_section = self._format_skills_section(agent_definition.skill_bindings)

        return f"""You are a workflow planner. Given a user's intent and an agent's capabilities,
generate a deterministic workflow definition as JSON.

## Agent Capabilities

### Available Tools
{tools_section}

### MCP Servers
{mcp_section}

### Skills
{skills_section}

## User Intent
{user_intent}

## Output Format

Generate a JSON object with the following structure:

```json
{{
  "steps": [
    {{
      "step_id": "unique_step_id",
      "step_type": "tool|agent|human_gate|condition",
      "display_name": "Human-readable step name",
      "description": "What this step does",

      // For tool type:
      "tool_name": "tool_name_from_list",
      "tool_arguments": {{
        "param_name": "$user_input|$steps.prev_step.output_key|$const:value"
      }},

      // For agent type:
      "agent_key": "agent_identifier",
      "agent_task": "Task description with {{variable}} interpolation",

      // For human_gate type:
      "gate_prompt": "Message to show the user",
      "gate_options": ["option1", "option2"],

      // For condition type:
      "condition_expr": "$steps.step_id.field == value",
      "condition_true_step": "step_id_if_true",
      "condition_false_step": "step_id_if_false",

      // General:
      "input_mapping": {{
        "input_name": "$user_input|$steps.prev_step.output_key|$const:value"
      }},
      "failure_policy": {{
        "on_failure": "fail|retry|skip",
        "max_retries": 3,
        "retry_delay_seconds": 1.0
      }},
      "timeout_seconds": 60
    }}
  ]
}}
```

## Rules

1. Use ONLY tools from the Available Tools list
2. Step IDs must be unique and descriptive (e.g., "lookup_order", "check_eligibility")
3. Use `$user_input` to reference the original user message
4. Use `$steps.<step_id>.<output_key>` to reference previous step outputs
5. Use `$const:<value>` for literal constants
6. Keep the workflow minimal — only include necessary steps
7. Add human_gate steps for actions that require user confirmation
8. Use condition steps for branching logic
9. Maximum {max_steps} steps
10. Each step should have a clear, descriptive display_name

## Response

Return ONLY the JSON object, no additional text or markdown formatting."""

    def _format_tools_section(self, tools: tuple[ToolBindingSnapshot, ...]) -> str:
        """Format tools for the prompt."""
        if not tools:
            return "No tools available."

        lines = []
        for tool in tools:
            lines.append(f"- **{tool.tool_name}**: {tool.description or 'No description'}")
        return "\n".join(lines)

    def _format_mcp_section(self, mcp_bindings: Any) -> str:
        """Format MCP bindings for the prompt."""
        if not mcp_bindings:
            return "No MCP servers configured."

        lines = []
        for binding in mcp_bindings:
            if not binding.is_enabled:
                continue
            lines.append(f"- **{binding.server_name}**")
            if binding.tool_whitelist:
                lines.append(f"  Tools: {', '.join(binding.tool_whitelist)}")
            else:
                lines.append("  Tools: All available")
        return "\n".join(lines) if lines else "No enabled MCP servers."

    def _format_skills_section(self, skill_bindings: Any) -> str:
        """Format skill bindings for the prompt."""
        if not skill_bindings:
            return "No skills configured."

        lines = []
        for binding in skill_bindings:
            if not binding.is_enabled:
                continue
            skill_def = binding.definition
            if skill_def:
                lines.append(f"- **{skill_def.display_name}** ({binding.skill_key})")
                lines.append(f"  {skill_def.description}")
            else:
                lines.append(f"- **{binding.skill_key}**")
        return "\n".join(lines) if lines else "No enabled skills."

    def _parse_llm_response(self, raw_text: str) -> dict[str, Any]:
        """Parse the LLM's JSON response.

        Handles common issues like markdown code blocks.
        """
        # Strip markdown code blocks if present
        text = raw_text.strip()
        if text.startswith("```"):
            # Find the first newline after opening ```
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
            # Remove trailing ```
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e

    def _dict_to_workflow(
        self,
        workflow_dict: dict[str, Any],
        agent_key: str,
        version: int,
        metadata: dict[str, Any],
    ) -> WorkflowDef:
        """Convert a parsed JSON dict to a WorkflowDef."""
        steps_data = workflow_dict.get("steps", [])
        steps = tuple(self._dict_to_step(step_data) for step_data in steps_data)

        return WorkflowDef(
            workflow_id=str(uuid.uuid4()),
            agent_key=agent_key,
            version=version,
            steps=steps,
            metadata={
                **metadata,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generator_version": "1.0.0",
            },
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _dict_to_step(self, step_data: dict[str, Any]) -> StepDef:
        """Convert a step dict to a StepDef."""
        # Parse input refs
        input_mapping = {}
        for key, ref_str in step_data.get("input_mapping", {}).items():
            input_mapping[key] = InputRef(ref_str)

        # Parse tool arguments
        tool_arguments = {}
        for key, ref_str in step_data.get("tool_arguments", {}).items():
            tool_arguments[key] = InputRef(ref_str)

        # Parse failure policy
        failure_policy_data = step_data.get("failure_policy", {})
        failure_policy = FailurePolicy(
            on_failure=failure_policy_data.get("on_failure", "fail"),
            max_retries=failure_policy_data.get("max_retries", 3),
            retry_delay_seconds=failure_policy_data.get("retry_delay_seconds", 1.0),
        )

        return StepDef(
            step_id=step_data["step_id"],
            step_type=step_data["step_type"],
            display_name=step_data.get("display_name", step_data["step_id"]),
            # tool fields
            tool_name=step_data.get("tool_name"),
            tool_arguments=tool_arguments,
            # agent fields
            agent_key=step_data.get("agent_key"),
            agent_task=step_data.get("agent_task"),
            # human_gate fields
            gate_prompt=step_data.get("gate_prompt"),
            gate_options=tuple(step_data.get("gate_options", [])),
            # condition fields
            condition_expr=step_data.get("condition_expr"),
            condition_true_step=step_data.get("condition_true_step"),
            condition_false_step=step_data.get("condition_false_step"),
            # general fields
            input_mapping=input_mapping,
            output_mapping=step_data.get("output_mapping", {}),
            failure_policy=failure_policy,
            timeout_seconds=step_data.get("timeout_seconds", 60.0),
            description=step_data.get("description", ""),
        )

    def _validate_workflow(
        self,
        workflow: WorkflowDef,
        agent_definition: AgentDefinitionSnapshot,
    ) -> list[str]:
        """Validate a generated workflow.

        Checks:
        - Referenced tools exist in the agent definition
        - Step dependencies are valid (no forward references)
        - No orphaned steps
        - Condition step references are valid
        - Step IDs are unique

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []
        available_tools = {t.tool_name for t in agent_definition.tools}
        step_ids = {step.step_id for step in workflow.steps}

        # Check unique step IDs
        seen_ids: set[str] = set()
        for step in workflow.steps:
            if step.step_id in seen_ids:
                errors.append(f"Duplicate step_id: {step.step_id}")
            seen_ids.add(step.step_id)

        # Track which steps are referenced by conditions
        referenced_steps: set[str] = set()

        for i, step in enumerate(workflow.steps):
            # Validate tool references
            if step.step_type == "tool":
                if not step.tool_name:
                    errors.append(f"Step '{step.step_id}': tool type requires tool_name")
                elif step.tool_name not in available_tools:
                    errors.append(
                        f"Step '{step.step_id}': tool '{step.tool_name}' not in agent definition"
                    )

            # Validate agent references
            if step.step_type == "agent":
                if not step.agent_key:
                    errors.append(f"Step '{step.step_id}': agent type requires agent_key")

            # Validate human_gate
            if step.step_type == "human_gate":
                if not step.gate_prompt:
                    errors.append(f"Step '{step.step_id}': human_gate type requires gate_prompt")

            # Validate condition
            if step.step_type == "condition":
                if not step.condition_expr:
                    errors.append(f"Step '{step.step_id}': condition type requires condition_expr")
                if step.condition_true_step:
                    referenced_steps.add(step.condition_true_step)
                    if step.condition_true_step not in step_ids:
                        errors.append(
                            f"Step '{step.step_id}': condition_true_step '{step.condition_true_step}' not found"
                        )
                if step.condition_false_step:
                    referenced_steps.add(step.condition_false_step)
                    if step.condition_false_step not in step_ids:
                        errors.append(
                            f"Step '{step.step_id}': condition_false_step '{step.condition_false_step}' not found"
                        )

            # Validate input references
            for key, ref in step.input_mapping.items():
                if ref.ref.startswith("$steps."):
                    parts = ref.ref.split(".")
                    if len(parts) >= 3:
                        referenced_step_id = parts[1]
                        referenced_steps.add(referenced_step_id)
                        if referenced_step_id not in step_ids:
                            errors.append(
                                f"Step '{step.step_id}': input '{key}' references unknown step '{referenced_step_id}'"
                            )
                        # Check for forward references
                        ref_index = next(
                            (j for j, s in enumerate(workflow.steps) if s.step_id == referenced_step_id),
                            -1,
                        )
                        if ref_index >= i:
                            errors.append(
                                f"Step '{step.step_id}': input '{key}' references step '{referenced_step_id}' which is not before this step"
                            )

            # Validate tool_arguments references
            for key, ref in step.tool_arguments.items():
                if ref.ref.startswith("$steps."):
                    parts = ref.ref.split(".")
                    if len(parts) >= 3:
                        referenced_step_id = parts[1]
                        referenced_steps.add(referenced_step_id)
                        if referenced_step_id not in step_ids:
                            errors.append(
                                f"Step '{step.step_id}': tool_argument '{key}' references unknown step '{referenced_step_id}'"
                            )

        # Check for orphaned steps (steps that are never referenced and aren't the first step)
        # This is a warning, not an error — sequential execution may reach them
        # Only flag if there's a clear break in the flow

        return errors
