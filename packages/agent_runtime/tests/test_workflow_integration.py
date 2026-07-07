"""Integration tests for WorkflowGenerator.

Tests cover:
- Workflow generation from user intent
- Prompt construction
- LLM response parsing
- Workflow validation
- Error handling
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.definition.models import (
    AgentDefinitionSnapshot,
    McpBindingSnapshot,
    SkillBindingSnapshot,
    SkillDefinitionSnapshot,
    ToolBindingSnapshot,
)
from agent_runtime.workflow.contracts import (
    FailurePolicy,
    InputRef,
    StepDef,
    WorkflowDef,
)
from agent_runtime.workflow.generator import WorkflowGenerator, WorkflowValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_gateway():
    """Create a mock GatewayService."""
    gateway = AsyncMock()
    gateway.generate_text = AsyncMock()
    return gateway


@pytest.fixture
def sample_agent_definition():
    """Create a sample agent definition with tools."""
    return AgentDefinitionSnapshot(
        agent_key="test_agent",
        version_number=1,
        display_name="Test Agent",
        description="A test agent for workflow generation",
        model_key="gpt-4",
        tools=(
            ToolBindingSnapshot(
                tool_name="lookup_order",
                description="Look up an order by ID",
            ),
            ToolBindingSnapshot(
                tool_name="check_eligibility",
                description="Check if user is eligible for a refund",
            ),
            ToolBindingSnapshot(
                tool_name="process_refund",
                description="Process a refund for an order",
            ),
            ToolBindingSnapshot(
                tool_name="send_notification",
                description="Send a notification to the user",
            ),
        ),
    )


@pytest.fixture
def sample_agent_with_mcp():
    """Create a sample agent definition with MCP bindings."""
    return AgentDefinitionSnapshot(
        agent_key="mcp_agent",
        version_number=1,
        display_name="MCP Agent",
        description="An agent with MCP tools",
        model_key="gpt-4",
        tools=(
            ToolBindingSnapshot(
                tool_name="internal_tool",
                description="An internal tool",
            ),
        ),
        mcp_bindings=(
            McpBindingSnapshot(
                server_name="github",
                is_enabled=True,
                tool_whitelist=("create_issue", "list_repos"),
            ),
            McpBindingSnapshot(
                server_name="slack",
                is_enabled=True,
                tool_whitelist=None,  # All tools allowed
            ),
        ),
    )


@pytest.fixture
def sample_agent_with_skills():
    """Create a sample agent definition with skill bindings."""
    return AgentDefinitionSnapshot(
        agent_key="skill_agent",
        version_number=1,
        display_name="Skill Agent",
        description="An agent with skills",
        model_key="gpt-4",
        tools=(
            ToolBindingSnapshot(
                tool_name="search_knowledge",
                description="Search the knowledge base",
            ),
        ),
        skill_bindings=(
            SkillBindingSnapshot(
                skill_key="customer_support",
                is_enabled=True,
                definition=SkillDefinitionSnapshot(
                    skill_key="customer_support",
                    display_name="Customer Support",
                    description="Handle customer inquiries professionally",
                    version="1.0.0",
                ),
            ),
        ),
    )


# ============================================================================
# Prompt construction tests
# ============================================================================


class TestPromptConstruction:
    """Tests for prompt construction."""

    def test_prompt_includes_tools(self, mock_gateway, sample_agent_definition):
        """Verify tools are included in the prompt."""
        generator = WorkflowGenerator(mock_gateway)

        prompt = generator._build_generation_prompt(
            agent_definition=sample_agent_definition,
            user_intent="Help me refund an order",
            max_steps=10,
        )

        assert "lookup_order" in prompt
        assert "check_eligibility" in prompt
        assert "process_refund" in prompt
        assert "send_notification" in prompt

    def test_prompt_includes_mcp(self, mock_gateway, sample_agent_with_mcp):
        """Verify MCP bindings are included in the prompt."""
        generator = WorkflowGenerator(mock_gateway)

        prompt = generator._build_generation_prompt(
            agent_definition=sample_agent_with_mcp,
            user_intent="Create a GitHub issue",
            max_steps=10,
        )

        assert "github" in prompt
        assert "create_issue" in prompt
        assert "list_repos" in prompt
        assert "slack" in prompt

    def test_prompt_includes_skills(self, mock_gateway, sample_agent_with_skills):
        """Verify skill bindings are included in the prompt."""
        generator = WorkflowGenerator(mock_gateway)

        prompt = generator._build_generation_prompt(
            agent_definition=sample_agent_with_skills,
            user_intent="Help a customer",
            max_steps=10,
        )

        assert "Customer Support" in prompt
        assert "customer_support" in prompt

    def test_prompt_includes_user_intent(self, mock_gateway, sample_agent_definition):
        """Verify user intent is included in the prompt."""
        generator = WorkflowGenerator(mock_gateway)
        intent = "I want to refund order #12345 because it arrived damaged"

        prompt = generator._build_generation_prompt(
            agent_definition=sample_agent_definition,
            user_intent=intent,
            max_steps=10,
        )

        assert intent in prompt

    def test_prompt_includes_max_steps(self, mock_gateway, sample_agent_definition):
        """Verify max_steps is included in the prompt."""
        generator = WorkflowGenerator(mock_gateway)

        prompt = generator._build_generation_prompt(
            agent_definition=sample_agent_definition,
            user_intent="Do something",
            max_steps=15,
        )

        assert "15" in prompt


# ============================================================================
# LLM response parsing tests
# ============================================================================


class TestLLMResponseParsing:
    """Tests for LLM response parsing."""

    def test_parse_plain_json(self, mock_gateway):
        """Parse plain JSON response."""
        generator = WorkflowGenerator(mock_gateway)
        response = '{"steps": [{"step_id": "test", "step_type": "tool"}]}'

        result = generator._parse_llm_response(response)
        assert "steps" in result
        assert len(result["steps"]) == 1

    def test_parse_markdown_json(self, mock_gateway):
        """Parse JSON wrapped in markdown code blocks."""
        generator = WorkflowGenerator(mock_gateway)
        response = '```json\n{"steps": [{"step_id": "test", "step_type": "tool"}]}\n```'

        result = generator._parse_llm_response(response)
        assert "steps" in result

    def test_parse_markdown_without_language(self, mock_gateway):
        """Parse JSON wrapped in markdown code blocks without language specifier."""
        generator = WorkflowGenerator(mock_gateway)
        response = '```\n{"steps": [{"step_id": "test", "step_type": "tool"}]}\n```'

        result = generator._parse_llm_response(response)
        assert "steps" in result

    def test_parse_invalid_json_raises(self, mock_gateway):
        """Raise ValueError for invalid JSON."""
        generator = WorkflowGenerator(mock_gateway)

        with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
            generator._parse_llm_response("not valid json")


# ============================================================================
# Workflow dict conversion tests
# ============================================================================


class TestWorkflowConversion:
    """Tests for converting dict to WorkflowDef."""

    def test_convert_simple_workflow(self, mock_gateway):
        """Convert a simple workflow dict."""
        generator = WorkflowGenerator(mock_gateway)
        workflow_dict = {
            "steps": [
                {
                    "step_id": "lookup",
                    "step_type": "tool",
                    "display_name": "Lookup Order",
                    "tool_name": "lookup_order",
                    "tool_arguments": {
                        "order_id": "$user_input",
                    },
                },
                {
                    "step_id": "notify",
                    "step_type": "tool",
                    "display_name": "Send Notification",
                    "tool_name": "send_notification",
                    "input_mapping": {
                        "message": "$steps.lookup.status",
                    },
                },
            ]
        }

        workflow = generator._dict_to_workflow(
            workflow_dict=workflow_dict,
            agent_key="test_agent",
            version=1,
            metadata={"intent": "test"},
        )

        assert workflow.agent_key == "test_agent"
        assert workflow.version == 1
        assert len(workflow.steps) == 2
        assert workflow.steps[0].step_id == "lookup"
        assert workflow.steps[0].step_type == "tool"
        assert workflow.steps[0].tool_name == "lookup_order"

    def test_convert_condition_step(self, mock_gateway):
        """Convert a workflow with condition step."""
        generator = WorkflowGenerator(mock_gateway)
        workflow_dict = {
            "steps": [
                {
                    "step_id": "check",
                    "step_type": "condition",
                    "display_name": "Check Eligibility",
                    "condition_expr": "$steps.lookup.eligible == true",
                    "condition_true_step": "refund",
                    "condition_false_step": "deny",
                },
            ]
        }

        workflow = generator._dict_to_workflow(
            workflow_dict=workflow_dict,
            agent_key="test_agent",
            version=1,
            metadata={},
        )

        step = workflow.steps[0]
        assert step.step_type == "condition"
        assert step.condition_expr == "$steps.lookup.eligible == true"
        assert step.condition_true_step == "refund"
        assert step.condition_false_step == "deny"

    def test_convert_human_gate_step(self, mock_gateway):
        """Convert a workflow with human_gate step."""
        generator = WorkflowGenerator(mock_gateway)
        workflow_dict = {
            "steps": [
                {
                    "step_id": "confirm",
                    "step_type": "human_gate",
                    "display_name": "Confirm Refund",
                    "gate_prompt": "Do you want to proceed with the refund?",
                    "gate_options": ["Yes", "No"],
                },
            ]
        }

        workflow = generator._dict_to_workflow(
            workflow_dict=workflow_dict,
            agent_key="test_agent",
            version=1,
            metadata={},
        )

        step = workflow.steps[0]
        assert step.step_type == "human_gate"
        assert step.gate_prompt == "Do you want to proceed with the refund?"
        assert step.gate_options == ("Yes", "No")

    def test_convert_agent_step(self, mock_gateway):
        """Convert a workflow with agent step."""
        generator = WorkflowGenerator(mock_gateway)
        workflow_dict = {
            "steps": [
                {
                    "step_id": "analyze",
                    "step_type": "agent",
                    "display_name": "Analyze Data",
                    "agent_key": "analysis_agent",
                    "agent_task": "Analyze the order data: {$steps.lookup.data}",
                },
            ]
        }

        workflow = generator._dict_to_workflow(
            workflow_dict=workflow_dict,
            agent_key="test_agent",
            version=1,
            metadata={},
        )

        step = workflow.steps[0]
        assert step.step_type == "agent"
        assert step.agent_key == "analysis_agent"
        assert "{$steps.lookup.data}" in step.agent_task

    def test_convert_failure_policy(self, mock_gateway):
        """Convert a step with failure policy."""
        generator = WorkflowGenerator(mock_gateway)
        workflow_dict = {
            "steps": [
                {
                    "step_id": "risky_step",
                    "step_type": "tool",
                    "tool_name": "some_tool",
                    "failure_policy": {
                        "on_failure": "retry",
                        "max_retries": 5,
                        "retry_delay_seconds": 2.0,
                    },
                },
            ]
        }

        workflow = generator._dict_to_workflow(
            workflow_dict=workflow_dict,
            agent_key="test_agent",
            version=1,
            metadata={},
        )

        step = workflow.steps[0]
        assert step.failure_policy.on_failure == "retry"
        assert step.failure_policy.max_retries == 5
        assert step.failure_policy.retry_delay_seconds == 2.0


# ============================================================================
# Validation tests
# ============================================================================


class TestWorkflowValidation:
    """Tests for workflow validation."""

    def test_valid_workflow_passes(self, mock_gateway, sample_agent_definition):
        """A valid workflow should pass validation."""
        generator = WorkflowGenerator(mock_gateway)
        workflow = WorkflowDef(
            workflow_id="test-id",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(
                    step_id="lookup",
                    step_type="tool",
                    display_name="Lookup",
                    tool_name="lookup_order",
                ),
                StepDef(
                    step_id="notify",
                    step_type="tool",
                    display_name="Notify",
                    tool_name="send_notification",
                    input_mapping={
                        "message": InputRef("$steps.lookup.status"),
                    },
                ),
            ),
        )

        errors = generator._validate_workflow(workflow, sample_agent_definition)
        assert errors == []

    def test_invalid_tool_name_fails(self, mock_gateway, sample_agent_definition):
        """Referencing a non-existent tool should fail."""
        generator = WorkflowGenerator(mock_gateway)
        workflow = WorkflowDef(
            workflow_id="test-id",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(
                    step_id="bad_step",
                    step_type="tool",
                    display_name="Bad Step",
                    tool_name="nonexistent_tool",
                ),
            ),
        )

        errors = generator._validate_workflow(workflow, sample_agent_definition)
        assert len(errors) == 1
        assert "nonexistent_tool" in errors[0]

    def test_duplicate_step_ids_fail(self, mock_gateway, sample_agent_definition):
        """Duplicate step IDs should fail."""
        generator = WorkflowGenerator(mock_gateway)
        workflow = WorkflowDef(
            workflow_id="test-id",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(
                    step_id="same_id",
                    step_type="tool",
                    display_name="First",
                    tool_name="lookup_order",
                ),
                StepDef(
                    step_id="same_id",
                    step_type="tool",
                    display_name="Second",
                    tool_name="send_notification",
                ),
            ),
        )

        errors = generator._validate_workflow(workflow, sample_agent_definition)
        assert len(errors) == 1
        assert "Duplicate step_id" in errors[0]

    def test_forward_reference_fails(self, mock_gateway, sample_agent_definition):
        """Referencing a future step should fail."""
        generator = WorkflowGenerator(mock_gateway)
        workflow = WorkflowDef(
            workflow_id="test-id",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(
                    step_id="step_a",
                    step_type="tool",
                    display_name="Step A",
                    tool_name="lookup_order",
                    input_mapping={
                        "data": InputRef("$steps.step_b.result"),  # Forward reference!
                    },
                ),
                StepDef(
                    step_id="step_b",
                    step_type="tool",
                    display_name="Step B",
                    tool_name="send_notification",
                ),
            ),
        )

        errors = generator._validate_workflow(workflow, sample_agent_definition)
        assert len(errors) == 1
        assert "forward reference" in errors[0].lower() or "not before" in errors[0].lower()

    def test_invalid_condition_target_fails(self, mock_gateway, sample_agent_definition):
        """Condition referencing non-existent step should fail."""
        generator = WorkflowGenerator(mock_gateway)
        workflow = WorkflowDef(
            workflow_id="test-id",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(
                    step_id="check",
                    step_type="condition",
                    display_name="Check",
                    condition_expr="$steps.lookup.eligible == true",
                    condition_true_step="nonexistent_step",
                ),
            ),
        )

        errors = generator._validate_workflow(workflow, sample_agent_definition)
        assert len(errors) == 1
        assert "nonexistent_step" in errors[0]

    def test_missing_tool_name_fails(self, mock_gateway, sample_agent_definition):
        """Tool step without tool_name should fail."""
        generator = WorkflowGenerator(mock_gateway)
        workflow = WorkflowDef(
            workflow_id="test-id",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(
                    step_id="bad_tool",
                    step_type="tool",
                    display_name="Bad Tool",
                    # tool_name is None
                ),
            ),
        )

        errors = generator._validate_workflow(workflow, sample_agent_definition)
        assert len(errors) == 1
        assert "tool_name" in errors[0]

    def test_missing_gate_prompt_fails(self, mock_gateway, sample_agent_definition):
        """Human gate without gate_prompt should fail."""
        generator = WorkflowGenerator(mock_gateway)
        workflow = WorkflowDef(
            workflow_id="test-id",
            agent_key="test_agent",
            version=1,
            steps=(
                StepDef(
                    step_id="bad_gate",
                    step_type="human_gate",
                    display_name="Bad Gate",
                    # gate_prompt is None
                ),
            ),
        )

        errors = generator._validate_workflow(workflow, sample_agent_definition)
        assert len(errors) == 1
        assert "gate_prompt" in errors[0]


# ============================================================================
# Full generation tests
# ============================================================================


class TestFullGeneration:
    """Tests for full workflow generation."""

    @pytest.mark.asyncio
    async def test_generate_workflow_success(self, mock_gateway, sample_agent_definition):
        """Test successful workflow generation."""
        # Mock LLM response
        llm_response = json.dumps({
            "steps": [
                {
                    "step_id": "lookup",
                    "step_type": "tool",
                    "display_name": "Lookup Order",
                    "tool_name": "lookup_order",
                    "tool_arguments": {"order_id": "$user_input"},
                },
                {
                    "step_id": "check",
                    "step_type": "condition",
                    "display_name": "Check Eligibility",
                    "condition_expr": "$steps.lookup.eligible == true",
                    "condition_true_step": "refund",
                    "condition_false_step": "deny",
                },
                {
                    "step_id": "refund",
                    "step_type": "tool",
                    "display_name": "Process Refund",
                    "tool_name": "process_refund",
                },
                {
                    "step_id": "deny",
                    "step_type": "tool",
                    "display_name": "Send Denial",
                    "tool_name": "send_notification",
                },
            ]
        })

        mock_response = MagicMock()
        mock_response.text = llm_response
        mock_gateway.generate_text.return_value = mock_response

        generator = WorkflowGenerator(mock_gateway)
        workflow = await generator.generate(
            agent_definition=sample_agent_definition,
            user_intent="I want to refund order #12345",
        )

        assert workflow.agent_key == "test_agent"
        assert len(workflow.steps) == 4
        assert workflow.steps[0].step_id == "lookup"
        assert workflow.steps[1].step_type == "condition"
        assert "generated_at" in workflow.metadata

    @pytest.mark.asyncio
    async def test_generate_workflow_validation_error(self, mock_gateway, sample_agent_definition):
        """Test that validation errors are raised."""
        # Mock LLM response with invalid tool
        llm_response = json.dumps({
            "steps": [
                {
                    "step_id": "bad_step",
                    "step_type": "tool",
                    "display_name": "Bad Step",
                    "tool_name": "nonexistent_tool",
                }
            ]
        })

        mock_response = MagicMock()
        mock_response.text = llm_response
        mock_gateway.generate_text.return_value = mock_response

        generator = WorkflowGenerator(mock_gateway)

        with pytest.raises(WorkflowValidationError) as exc_info:
            await generator.generate(
                agent_definition=sample_agent_definition,
                user_intent="Do something",
            )

        assert len(exc_info.value.errors) == 1
        assert "nonexistent_tool" in exc_info.value.errors[0]

    @pytest.mark.asyncio
    async def test_generate_workflow_with_markdown_response(self, mock_gateway, sample_agent_definition):
        """Test generation with markdown-wrapped JSON response."""
        llm_response = """```json
{
    "steps": [
        {
            "step_id": "lookup",
            "step_type": "tool",
            "display_name": "Lookup",
            "tool_name": "lookup_order"
        }
    ]
}
```"""

        mock_response = MagicMock()
        mock_response.text = llm_response
        mock_gateway.generate_text.return_value = mock_response

        generator = WorkflowGenerator(mock_gateway)
        workflow = await generator.generate(
            agent_definition=sample_agent_definition,
            user_intent="Look up an order",
        )

        assert len(workflow.steps) == 1

    @pytest.mark.asyncio
    async def test_generate_workflow_with_metadata(self, mock_gateway, sample_agent_definition):
        """Test that custom metadata is preserved."""
        llm_response = json.dumps({
            "steps": [
                {
                    "step_id": "test",
                    "step_type": "tool",
                    "display_name": "Test",
                    "tool_name": "lookup_order",
                }
            ]
        })

        mock_response = MagicMock()
        mock_response.text = llm_response
        mock_gateway.generate_text.return_value = mock_response

        generator = WorkflowGenerator(mock_gateway)
        workflow = await generator.generate(
            agent_definition=sample_agent_definition,
            user_intent="Test",
            metadata={"source": "test_suite", "priority": "high"},
        )

        assert workflow.metadata["source"] == "test_suite"
        assert workflow.metadata["priority"] == "high"
        assert "generated_at" in workflow.metadata

    @pytest.mark.asyncio
    async def test_generate_workflow_respects_max_steps(self, mock_gateway, sample_agent_definition):
        """Test that max_steps is passed to the prompt."""
        llm_response = json.dumps({"steps": []})

        mock_response = MagicMock()
        mock_response.text = llm_response
        mock_gateway.generate_text.return_value = mock_response

        generator = WorkflowGenerator(mock_gateway)

        # Capture the prompt sent to the LLM
        captured_prompts = []
        original_generate = mock_gateway.generate_text

        async def capture_prompt(request):
            captured_prompts.append(request.prompt)
            return mock_response

        mock_gateway.generate_text.side_effect = capture_prompt

        await generator.generate(
            agent_definition=sample_agent_definition,
            user_intent="Test",
            max_steps=5,
        )

        assert "5" in captured_prompts[0]
