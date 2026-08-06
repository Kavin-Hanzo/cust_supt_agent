import json
from pathlib import Path
from typing import Dict, Optional, List
from src.utils.models import Order, Customer


class DataLoader:
    """
    In-memory data management layer for Trendly customer records, orders, and policy.
    Matches the exact schema of the Trendly dataset.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.data_dir = base_dir / "data"
        else:
            self.data_dir = Path(data_dir)

        self._customers_by_id: Dict[str, Customer] = {}
        self._customers_by_email: Dict[str, Customer] = {}
        self._orders_by_id: Dict[str, Order] = {}
        self._orders_by_customer_id: Dict[str, List[Order]] = {}
        self._policy_content: str = ""

        self.load_all()

    def load_all(self) -> None:
        self._load_dataset()
        self._load_policy()

    def _load_dataset(self) -> None:
        orders_file = self.data_dir / "orders.json"
        if not orders_file.exists():
            return

        with open(orders_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        for raw_c in raw_data.get("customers", []):
            cust = Customer(**raw_c)
            self._customers_by_id[cust.customer_id] = cust
            self._customers_by_email[cust.email.lower().strip()] = cust

        for raw_o in raw_data.get("orders", []):
            order = Order(**raw_o)
            norm_id = self.normalize_order_id(order.order_id)
            self._orders_by_id[norm_id] = order

            cust_id = order.customer_id
            if cust_id not in self._orders_by_customer_id:
                self._orders_by_customer_id[cust_id] = []
            self._orders_by_customer_id[cust_id].append(order)

    def _load_policy(self) -> None:
        policy_file = self.data_dir / "policy.md"
        if not policy_file.exists():
            self._policy_content = "No policy documentation available."
            return

        with open(policy_file, "r", encoding="utf-8") as f:
            self._policy_content = f.read()

    @staticmethod
    def normalize_order_id(order_id: str) -> str:
        return order_id.strip().lstrip("#").upper()

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        return self._orders_by_id.get(self.normalize_order_id(order_id))

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        return self._customers_by_email.get(email.lower().strip())

    def get_customer_by_id(self, customer_id: str) -> Optional[Customer]:
        return self._customers_by_id.get(customer_id)

    def get_orders_by_email(self, email: str) -> List[Order]:
        cust = self.get_customer_by_email(email)
        if not cust:
            return []
        return self._orders_by_customer_id.get(cust.customer_id, [])

    def get_policy_text(self) -> str:
        return self._policy_content


_loader_instance: Optional[DataLoader] = None


def get_data_loader(data_dir: Optional[str] = None) -> DataLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DataLoader(data_dir=data_dir)
    return _loader_instance