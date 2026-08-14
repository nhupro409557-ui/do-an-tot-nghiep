import unittest

from app.application.commerce.use_cases.payment import is_momo_terminal_failure


class MoMoPaymentStatusTest(unittest.TestCase):
    def test_user_denied_result_is_terminal_failure(self) -> None:
        self.assertTrue(is_momo_terminal_failure({"resultCode": 1006}))

    def test_pending_and_success_results_are_not_failures(self) -> None:
        self.assertFalse(is_momo_terminal_failure({"resultCode": 0}))
        self.assertFalse(is_momo_terminal_failure({"resultCode": 1000}))
        self.assertFalse(is_momo_terminal_failure({"resultCode": 7002}))


if __name__ == "__main__":
    unittest.main()
