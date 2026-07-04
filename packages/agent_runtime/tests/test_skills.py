"""Unit tests for the Skills Phase 1 implementation.

Covers:
- SkillRegistry: register, overwrite, get, list_all, list_by_tag, unregister
- SkillComposer.compose_prompt: all cases
- SkillComposer.compose_tool_bindings: all merge scenarios
- SkillBinding defaults
- Built-in skills: RagQaSkill, CustomerSupportSkill
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from agent_runtime.skills import (
    SkillBinding,
    SkillComposer,
    SkillPromptFragment,
    SkillRegistry,
    SkillSpec,
)
from agent_runtime.skills.builtin import CustomerSupportSkill, RagQaSkill
from agent_runtime.tools.contracts import ToolBinding


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_spec(
    skill_key: str = "test_skill_v1",
    *,
    tags: frozenset[str] = frozenset(),
    prompt_fragments: tuple[SkillPromptFragment, ...] = (),
) -> SkillSpec:
    return SkillSpec(
        skill_key=skill_key,
        display_name="Test Skill",
        description="A test skill.",
        version="1.0.0",
        prompt_fragments=prompt_fragments,
        tags=tags,
    )


def make_fragment(
    section: str = "Test Section",
    content: str = "Test content.",
    order: int = 100,
) -> SkillPromptFragment:
    return SkillPromptFragment(section=section, content=content, order=order)


def make_binding(
    skill_key: str = "test_skill_v1",
    *,
    is_enabled: bool = True,
    order: int = 100,
    config: dict | None = None,
    tool_overrides: tuple[ToolBinding, ...] = (),
) -> SkillBinding:
    return SkillBinding(
        skill_key=skill_key,
        is_enabled=is_enabled,
        order=order,
        config=config or {},
        tool_overrides=tool_overrides,
    )


@pytest.fixture()
def registry() -> SkillRegistry:
    return SkillRegistry()


@pytest.fixture()
def composer(registry: SkillRegistry) -> SkillComposer:
    return SkillComposer(registry)


# ---------------------------------------------------------------------------
# SkillRegistry tests
# ---------------------------------------------------------------------------


class TestSkillRegistry:
    def test_register_and_get(self, registry: SkillRegistry) -> None:
        spec = make_spec("skill_a")
        registry.register(spec)
        assert registry.get("skill_a") is spec

    def test_get_missing_returns_none(self, registry: SkillRegistry) -> None:
        assert registry.get("nonexistent") is None

    def test_register_overwrites_existing(self, registry: SkillRegistry) -> None:
        spec1 = make_spec("skill_a")
        spec2 = SkillSpec(
            skill_key="skill_a",
            display_name="Updated",
            description="Updated description.",
            version="2.0.0",
        )
        registry.register(spec1)
        registry.register(spec2)
        assert registry.get("skill_a") is spec2

    def test_list_all_empty(self, registry: SkillRegistry) -> None:
        assert registry.list_all() == []

    def test_list_all_returns_all_registered(self, registry: SkillRegistry) -> None:
        spec_a = make_spec("a")
        spec_b = make_spec("b")
        registry.register(spec_a)
        registry.register(spec_b)
        result = registry.list_all()
        assert spec_a in result
        assert spec_b in result
        assert len(result) == 2

    def test_list_by_tag_match(self, registry: SkillRegistry) -> None:
        spec = make_spec("tagged", tags=frozenset({"rag", "read_only"}))
        registry.register(spec)
        assert registry.list_by_tag("rag") == [spec]

    def test_list_by_tag_no_match(self, registry: SkillRegistry) -> None:
        spec = make_spec("untagged", tags=frozenset({"safety"}))
        registry.register(spec)
        assert registry.list_by_tag("rag") == []

    def test_list_by_tag_multiple_matches(self, registry: SkillRegistry) -> None:
        spec1 = make_spec("a", tags=frozenset({"rag"}))
        spec2 = make_spec("b", tags=frozenset({"rag", "safety"}))
        spec3 = make_spec("c", tags=frozenset({"safety"}))
        registry.register(spec1)
        registry.register(spec2)
        registry.register(spec3)
        result = registry.list_by_tag("rag")
        assert spec1 in result
        assert spec2 in result
        assert spec3 not in result

    def test_unregister_existing_returns_true(self, registry: SkillRegistry) -> None:
        registry.register(make_spec("x"))
        assert registry.unregister("x") is True
        assert registry.get("x") is None

    def test_unregister_missing_returns_false(self, registry: SkillRegistry) -> None:
        assert registry.unregister("nonexistent") is False


# ---------------------------------------------------------------------------
# SkillComposer.compose_prompt tests
# ---------------------------------------------------------------------------


class TestComposePrompt:
    BASE = "You are a helpful assistant."

    def test_no_bindings_returns_base_unchanged(self, composer: SkillComposer) -> None:
        result = composer.compose_prompt(self.BASE, [])
        assert result == self.BASE

    def test_single_skill_single_fragment_appended(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        fragment = make_fragment(section="My Section", content="My content.")
        spec = make_spec("s1", prompt_fragments=(fragment,))
        registry.register(spec)
        binding = make_binding("s1")
        result = composer.compose_prompt(self.BASE, [binding])
        assert result == f"{self.BASE}\n\n## My Section\nMy content."

    def test_multiple_skills_sorted_by_global_key(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        # skill A: binding.order=2, fragment.order=10  → key=2010
        # skill B: binding.order=1, fragment.order=50  → key=1050
        # Expected order: B (1050) then A (2010)
        frag_a = make_fragment(section="A Section", content="A content.", order=10)
        frag_b = make_fragment(section="B Section", content="B content.", order=50)
        registry.register(make_spec("skill_a", prompt_fragments=(frag_a,)))
        registry.register(make_spec("skill_b", prompt_fragments=(frag_b,)))

        bindings = [
            make_binding("skill_a", order=2),
            make_binding("skill_b", order=1),
        ]
        result = composer.compose_prompt(self.BASE, bindings)
        b_pos = result.index("B Section")
        a_pos = result.index("A Section")
        assert b_pos < a_pos

    def test_skill_not_in_registry_skips_silently(
        self, composer: SkillComposer, caplog: pytest.LogCaptureFixture
    ) -> None:
        binding = make_binding("missing_skill")
        with caplog.at_level(logging.WARNING):
            result = composer.compose_prompt(self.BASE, [binding])
        assert result == self.BASE
        assert "missing_skill" in caplog.text

    def test_disabled_binding_not_included(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        fragment = make_fragment(content="Should not appear.")
        registry.register(make_spec("s1", prompt_fragments=(fragment,)))
        binding = make_binding("s1", is_enabled=False)
        result = composer.compose_prompt(self.BASE, [binding])
        assert result == self.BASE

    def test_template_var_rendered_from_config(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        fragment = make_fragment(content="Max results: {config.max_results}.")
        registry.register(make_spec("s1", prompt_fragments=(fragment,)))
        binding = make_binding("s1", config={"max_results": "10"})
        result = composer.compose_prompt(self.BASE, [binding])
        assert "Max results: 10." in result

    def test_unknown_template_var_kept_verbatim_and_warns(
        self, registry: SkillRegistry, composer: SkillComposer, caplog: pytest.LogCaptureFixture
    ) -> None:
        fragment = make_fragment(content="Value: {config.missing_key}.")
        registry.register(make_spec("s1", prompt_fragments=(fragment,)))
        binding = make_binding("s1")
        with caplog.at_level(logging.WARNING):
            result = composer.compose_prompt(self.BASE, [binding])
        assert "{config.missing_key}" in result
        assert "missing_key" in caplog.text

    def test_runtime_config_overrides_binding_config(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        fragment = make_fragment(content="Value: {config.key}.")
        registry.register(make_spec("s1", prompt_fragments=(fragment,)))
        binding = make_binding("s1", config={"key": "binding_value"})
        result = composer.compose_prompt(
            self.BASE, [binding], runtime_config={"key": "runtime_value"}
        )
        assert "runtime_value" in result
        assert "binding_value" not in result

    def test_all_disabled_returns_base_unchanged(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        fragment = make_fragment(content="Should not appear.")
        registry.register(make_spec("s1", prompt_fragments=(fragment,)))
        binding = make_binding("s1", is_enabled=False)
        assert composer.compose_prompt(self.BASE, [binding]) == self.BASE


# ---------------------------------------------------------------------------
# SkillComposer.compose_tool_bindings tests
# ---------------------------------------------------------------------------


class TestComposeToolBindings:
    def _tb(
        self,
        name: str,
        *,
        is_enabled: bool = True,
        invocation_mode: str = "auto",
        description: str | None = None,
        config: dict | None = None,
    ) -> ToolBinding:
        return ToolBinding(
            tool_name=name,
            is_enabled=is_enabled,
            invocation_mode=invocation_mode,  # type: ignore[arg-type]
            description=description,
            config=config or {},
        )

    def test_no_skill_bindings_returns_base_unchanged(
        self, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a"), self._tb("tool_b")]
        result = composer.compose_tool_bindings(base, [])
        assert result == base

    def test_any_false_is_enabled_disables_tool(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", is_enabled=True)]
        override = self._tb("tool_a", is_enabled=False)
        skill_binding = make_binding("s1", tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        assert merged["tool_a"].is_enabled is False

    def test_invocation_mode_most_permissive_wins(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", invocation_mode="manual_only")]
        override = self._tb("tool_a", invocation_mode="auto")
        skill_binding = make_binding("s1", tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        assert merged["tool_a"].invocation_mode == "auto"

    def test_invocation_mode_manual_only_beats_disabled(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", invocation_mode="disabled")]
        override = self._tb("tool_a", invocation_mode="manual_only")
        skill_binding = make_binding("s1", tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        assert merged["tool_a"].invocation_mode == "manual_only"

    def test_invocation_mode_auto_beats_disabled(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", invocation_mode="disabled")]
        override = self._tb("tool_a", invocation_mode="auto")
        skill_binding = make_binding("s1", tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        assert merged["tool_a"].invocation_mode == "auto"

    def test_description_last_explicit_wins(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", description="Base description")]
        override = self._tb("tool_a", description="Override description")
        skill_binding = make_binding("s1", order=50, tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        assert merged["tool_a"].description == "Override description"

    def test_description_none_does_not_override_existing(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", description="Base description")]
        override = self._tb("tool_a", description=None)
        skill_binding = make_binding("s1", tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        assert merged["tool_a"].description == "Base description"

    def test_config_shallow_merge_later_overrides_earlier(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", config={"a": 1, "b": 2})]
        override = self._tb("tool_a", config={"b": 99, "c": 3})
        skill_binding = make_binding("s1", tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        assert merged["tool_a"].config == {"a": 1, "b": 99, "c": 3}

    def test_base_bindings_preserved_if_no_overrides(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a"), self._tb("tool_b")]
        skill_binding = make_binding("s1")  # no tool_overrides
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        names = {tb.tool_name for tb in result}
        assert "tool_a" in names
        assert "tool_b" in names

    def test_disabled_skill_binding_tool_overrides_ignored(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        base = [self._tb("tool_a", is_enabled=True)]
        override = self._tb("tool_a", is_enabled=False)
        skill_binding = make_binding("s1", is_enabled=False, tool_overrides=(override,))
        registry.register(make_spec("s1"))
        result = composer.compose_tool_bindings(base, [skill_binding])
        merged = {tb.tool_name: tb for tb in result}
        # Skill binding is disabled, so override is ignored — tool stays enabled.
        assert merged["tool_a"].is_enabled is True


# ---------------------------------------------------------------------------
# SkillBinding defaults
# ---------------------------------------------------------------------------


class TestSkillBindingDefaults:
    def test_defaults(self) -> None:
        binding = SkillBinding(skill_key="x")
        assert binding.is_enabled is True
        assert binding.order == 100
        assert binding.config == {}
        assert binding.tool_overrides == ()


# ---------------------------------------------------------------------------
# Built-in skills validity
# ---------------------------------------------------------------------------


class TestBuiltinSkills:
    def test_rag_qa_skill_is_valid_spec(self) -> None:
        spec = RagQaSkill.spec
        assert isinstance(spec, SkillSpec)
        assert spec.skill_key == "rag_qa_v1"
        assert "rag" in spec.tags
        assert len(spec.prompt_fragments) >= 1
        assert "knowledge_search" in spec.recommended_tools

    def test_customer_support_skill_is_valid_spec(self) -> None:
        spec = CustomerSupportSkill.spec
        assert isinstance(spec, SkillSpec)
        assert spec.skill_key == "customer_support_v1"
        assert "customer_support" in spec.tags
        assert len(spec.prompt_fragments) >= 1

    def test_builtin_skills_register_and_compose(self) -> None:
        reg = SkillRegistry()
        reg.register(RagQaSkill.spec)
        reg.register(CustomerSupportSkill.spec)
        composer = SkillComposer(reg)
        bindings = [
            SkillBinding(skill_key="rag_qa_v1"),
            SkillBinding(skill_key="customer_support_v1"),
        ]
        result = composer.compose_prompt("Base.", bindings)
        assert "知识库检索指令" in result
        assert "客服行为规范" in result
