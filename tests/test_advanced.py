"""Offline checks for the advanced desk: authorization, tokens and state."""
import os
import unittest
from unittest.mock import patch

import jwt

from examples.orders import find_order
from examples.room_access import create_token

DEV = {"LIVEKIT_API_KEY": "devkey", "LIVEKIT_API_SECRET": "a-test-secret-of-32-characters!!"}


class AdvancedOfflineTests(unittest.TestCase):
    def test_orders_are_scoped_to_verified_customer(self):
        self.assertEqual(find_order("cust-amal", "nr-1001 ")["status"], "Shipped")
        self.assertFalse(find_order(None, "NR-1001")["found"])
        self.assertFalse(find_order("cust-amal", "NR-1001; drop table")["found"])
        # Someone else's order and a missing one look identical to the caller.
        self.assertEqual(find_order("cust-amal", "NR-2001"), find_order("cust-amal", "NR-9999"))
        self.assertNotIn("customer_id", find_order("cust-amal", "NR-1001"))

    def test_token_carries_attributes_and_dispatch(self):
        with patch.dict(os.environ, DEV, clear=True):
            token = create_token("room-a", "user-1", {"customer_id": "cust-amal"},
                                 agent="tutorial-desk")
        claims = jwt.decode(token, DEV["LIVEKIT_API_SECRET"], algorithms=["HS256"])
        self.assertEqual(claims["sub"], "user-1")
        self.assertEqual(claims["video"]["room"], "room-a")
        self.assertEqual(claims["attributes"], {"customer_id": "cust-amal"})
        self.assertEqual(claims["roomConfig"]["agents"][0]["agentName"], "tutorial-desk")

    def test_plain_token_has_no_extras(self):
        with patch.dict(os.environ, DEV, clear=True):
            claims = jwt.decode(create_token("room-a", "user-1"),
                                DEV["LIVEKIT_API_SECRET"], algorithms=["HS256"])
        self.assertFalse(claims.get("attributes"))
        self.assertNotIn("roomConfig", claims)

    def test_desk_state_snapshot(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy"}):
            from examples.livekit_advanced_agent import DeskState
        state = DeskState(customer_id="cust-amal", active="orders",
                          handoffs=["triage", "orders"], ttft=[0.8, 0.4567])
        self.assertEqual(state.snapshot(), {"active": "orders", "handoffs": ["triage", "orders"],
                                            "verified": True, "turns": 2, "last_llm_ttft": 0.457})

    def test_llm_never_disables_reasoning(self):
        # Some free models return HTTP 400 when reasoning is disabled.
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy",
                                     "OPENROUTER_MODEL": "openrouter/free"}):
            from examples.livekit_common import make_llm
            body = make_llm()._opts.extra_body
        self.assertNotEqual(body["reasoning"].get("enabled"), False)
        self.assertEqual(body["provider"]["max_price"], {"prompt": 0, "completion": 0})


if __name__ == "__main__":
    unittest.main()
