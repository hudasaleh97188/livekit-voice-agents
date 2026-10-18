"""Fictional order store with ownership checks done in code, not by the model."""
import json
import re
from pathlib import Path

ORDERS_PATH = Path(__file__).resolve().parents[1] / "data" / "orders.json"
ORDER_ID = re.compile(r"^NR-\d{4}$")


def find_order(customer_id: str | None, order_id: str) -> dict:
    if not customer_id:
        return {"found": False, "reason": "Caller is not verified. Ask them to sign in."}
    order_id = order_id.strip().upper()
    if not ORDER_ID.match(order_id):
        return {"found": False, "reason": "Order numbers look like NR-1234."}
    for order in json.loads(ORDERS_PATH.read_text(encoding="utf-8")):
        # Same reply for "missing" and "someone else's" so IDs cannot be probed.
        if order["order_id"] == order_id and order["customer_id"] == customer_id:
            return {"found": True, **{k: order[k] for k in ("order_id", "status", "eta", "item")}}
    return {"found": False, "reason": "No order with that number on this account."}
