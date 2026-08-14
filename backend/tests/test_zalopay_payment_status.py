import unittest

from app.application.commerce.use_cases.payment import is_zalopay_terminal_failure


class ZaloPayPaymentStatusTest(unittest.TestCase):
    def test_failed_query_result_is_terminal_failure(self) -> None:
        self.assertTrue(is_zalopay_terminal_failure({"return_code": 2}))

    def test_success_and_processing_results_are_not_failures(self) -> None:
        self.assertFalse(is_zalopay_terminal_failure({"return_code": 1}))
        self.assertFalse(is_zalopay_terminal_failure({"return_code": 3}))
        self.assertFalse(is_zalopay_terminal_failure({"return_code": "invalid"}))


if __name__ == "__main__":
    unittest.main()
