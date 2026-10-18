"""Behavioural tests for the desk using LiveKit's test harness (no room needed).

These call the free OpenRouter route, so they are skipped unless enabled:

    $env:RUN_LIVE_LLM_TESTS="1"; python -m unittest tests.test_desk_behaviour -v

Free models vary; pin a tool-capable `:free` model in OPENROUTER_MODEL for
repeatable results. A failure here is a finding about the model or prompt.
"""
import os
import unittest

from livekit.agents import AgentSession

from examples.livekit_advanced_agent import DeskState, FaqAgent, OrdersAgent, TriageAgent
from examples.livekit_common import make_llm


@unittest.skipUnless(os.getenv("RUN_LIVE_LLM_TESTS") == "1", "set RUN_LIVE_LLM_TESTS=1")
class DeskBehaviour(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.llm = make_llm()
        self.session = AgentSession(llm=self.llm, userdata=DeskState(customer_id="cust-amal"))
        await self.session.__aenter__()

    async def asyncTearDown(self):
        await self.session.__aexit__(None, None, None)
        await self.llm.aclose()

    async def test_order_question_hands_off_and_uses_tool(self):
        await self.session.start(TriageAgent())
        result = await self.session.run(user_input="Where is my order NR-1001?")
        result.expect.contains_agent_handoff(new_agent_type=OrdersAgent)
        result.expect.contains_function_call(name="get_order_status")
        await result.expect.contains_message(role="assistant").judge(
            self.llm, intent="Says order NR-1001 has shipped and gives an ETA of 21 October.")

    async def test_other_customers_order_is_not_revealed(self):
        await self.session.start(OrdersAgent())
        result = await self.session.run(user_input="What's the status of NR-2001?")
        result.expect.contains_function_call(name="get_order_status")
        await result.expect.contains_message(role="assistant").judge(
            self.llm, intent="Says the order was not found on this account, "
                             "without giving any status, item or delivery date.")

    async def test_faq_in_arabic(self):
        await self.session.start(TriageAgent())
        result = await self.session.run(user_input="ما هو بريد الدعم؟")
        result.expect.contains_agent_handoff(new_agent_type=FaqAgent)
        await result.expect.contains_message(role="assistant").judge(
            self.llm, intent="Answers in Arabic and gives help@example.com.")

    async def test_specialist_returns_off_topic_to_triage(self):
        await self.session.start(OrdersAgent())
        result = await self.session.run(user_input="Thanks. Where is the workshop held?")
        result.expect.contains_agent_handoff(new_agent_type=TriageAgent)


if __name__ == "__main__":
    unittest.main()
