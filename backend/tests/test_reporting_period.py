import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from app.application.reporting.period import (
    build_report_period,
    calculate_percentage_change,
)


class ReportingPeriodTest(unittest.TestCase):
    def test_converts_local_dates_to_half_open_utc_range(self) -> None:
        period = build_report_period(
            from_date=date(2026, 7, 1),
            to_date=date(2026, 8, 1),
            timezone_name="Asia/Bangkok",
            bucket="day",
        )

        self.assertEqual(
            period.from_utc,
            datetime(2026, 6, 30, 17, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            period.to_utc,
            datetime(2026, 7, 31, 17, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            period.previous_from_utc,
            datetime(2026, 5, 30, 17, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(period.previous_to_utc, period.from_utc)

    def test_rejects_reversed_or_empty_period(self) -> None:
        with self.assertRaisesRegex(HTTPException, "Ngày bắt đầu phải trước ngày kết thúc"):
            build_report_period(
                from_date=date(2026, 7, 1),
                to_date=date(2026, 7, 1),
                timezone_name="Asia/Bangkok",
                bucket="day",
            )

    def test_rejects_period_longer_than_one_year(self) -> None:
        with self.assertRaisesRegex(HTTPException, "không được vượt quá 366 ngày"):
            build_report_period(
                from_date=date(2025, 1, 1),
                to_date=date(2026, 7, 1),
                timezone_name="Asia/Bangkok",
                bucket="month",
            )

    def test_rejects_unknown_timezone(self) -> None:
        with self.assertRaisesRegex(HTTPException, "Múi giờ báo cáo không hợp lệ"):
            build_report_period(
                from_date=date(2026, 7, 1),
                to_date=date(2026, 8, 1),
                timezone_name="Mars/Olympus",
                bucket="day",
            )

    def test_previous_period_keeps_local_midnight_across_dst_change(self) -> None:
        period = build_report_period(
            from_date=date(2026, 3, 8),
            to_date=date(2026, 3, 10),
            timezone_name="America/New_York",
            bucket="day",
        )

        self.assertEqual(
            period.previous_from_utc,
            datetime(2026, 3, 6, 5, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            period.previous_to_utc,
            datetime(2026, 3, 8, 5, 0, tzinfo=timezone.utc),
        )

    def test_calculates_change_and_handles_zero_baseline(self) -> None:
        self.assertEqual(
            calculate_percentage_change(Decimal("150"), Decimal("100")),
            Decimal("50.00"),
        )
        self.assertIsNone(calculate_percentage_change(Decimal("10"), Decimal("0")))
        self.assertEqual(calculate_percentage_change(Decimal("0"), Decimal("0")), Decimal("0"))


if __name__ == "__main__":
    unittest.main()
