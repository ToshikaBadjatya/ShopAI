import re
from collections import Counter

from shopai.crew import Shopai

# "IF <situation> -> CALL <tool>": the condition may not contain an arrow, so a
# rule that ends in "-> answer without a tool" never swallows the next CALL.
RULE = re.compile(r"\bIF\b[^>]*->\s*CALL\s+(\w+)")


def _called(backstory: str) -> list[str]:
    return RULE.findall(" ".join(backstory.split()))


def test_the_clarifier_names_each_tool_it_holds_in_exactly_one_if_call_rule():
    shopai = Shopai()
    held = {t.name for t in shopai.clarification_agent("run-1", "tok").tools}
    called = _called(shopai.agents_config["clarification_agent"]["backstory"])
    assert Counter(called) == Counter(held)


def test_the_clarifier_reads_the_conversation_before_anything_else():
    called = _called(Shopai().agents_config["clarification_agent"]["backstory"])
    assert called[0] == "get_conversation_history"


def test_the_clarifier_has_a_rule_for_when_no_tool_is_needed():
    backstory = " ".join(Shopai().agents_config["clarification_agent"]["backstory"].split())
    assert re.search(r"\bIF none apply\b[^>]*->\s*answer without a tool", backstory)


def test_the_profile_learner_names_each_of_its_tools_in_an_if_call_rule():
    shopai = Shopai()
    held = {t.name for t in shopai.profile_learner_agent("tok", "I always avoid maroon").tools}
    called = _called(shopai.agents_config["profile_learner_agent"]["backstory"])
    assert Counter(called) == Counter(held)
    assert called[0] == "get_user_memory"


def test_the_clarifier_keeps_its_non_tool_rules():
    backstory = " ".join(Shopai().agents_config["clarification_agent"]["backstory"].split())
    assert "exact words" in backstory                  # evidence rule
    assert "one missing category" in backstory         # one question at a time
    assert "culture" in backstory                      # never ask about it
