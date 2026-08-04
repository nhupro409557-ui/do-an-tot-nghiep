import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.application.reporting.export_job_service import write_report_export_file


def _order_item(index: int) -> SimpleNamespace:
    return SimpleNamespace(
        orderCode=f"EMV{index:010d}",
        customerName=f"Khách hàng {index}",
        email=f"customer{index}@example.com",
        status="COMPLETED",
        channel="ONLINE",
        paymentMethod="COD",
        paymentStatus="PAID",
        fulfillmentMethod="DELIVERY",
        totalAmount=1000,
        createdAt="2026-07-01T00:00:00+00:00",
        completedAt="2026-07-02T00:00:00+00:00",
    )


class ReportExportBatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_order_export_writes_fixed_batches(self) -> None:
        total = 1_200

        async def report_page(*_args, page: int, limit: int, **_kwargs):
            start = (page - 1) * limit
            end = min(start + limit, total)
            return SimpleNamespace(
                items=[_order_item(index) for index in range(start, end)],
                pagination=SimpleNamespace(total=total),
            )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.csv"
            mocked = AsyncMock(side_effect=report_page)
            with patch(
                "app.application.reporting.export_job_service.get_order_report",
                new=mocked,
            ):
                row_count = await write_report_export_file(
                    AsyncMock(),
                    "orders",
                    {
                        "from": date(2026, 7, 1).isoformat(),
                        "to": date(2026, 8, 1).isoformat(),
                    },
                    path,
                    batch_size=500,
                )

            content = path.read_text(encoding="utf-8-sig").splitlines()

        self.assertEqual(row_count, total)
        self.assertEqual(len(content), total + 1)
        self.assertEqual([call.kwargs["page"] for call in mocked.await_args_list], [1, 2, 3])
        self.assertTrue(all(
            call.kwargs["limit"] == 500
            for call in mocked.await_args_list
        ))


if __name__ == "__main__":
    unittest.main()
