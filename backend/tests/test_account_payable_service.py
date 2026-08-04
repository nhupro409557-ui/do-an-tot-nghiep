from datetime import datetime, timezone
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.schemas.admin.account_payable import (
    AccountPayableAdjustmentPayload,
    SupplierPaymentPayload,
    SupplierPaymentReversalPayload,
)
from app.application.services import account_payable_service


class AccountPayableServiceTest(IsolatedAsyncioTestCase):
    async def test_payment_without_idempotency_key_is_rejected(self) -> None:
        payable_id = uuid4()
        session = AsyncMock()
        payable = {
            "id": payable_id,
            "status": "OPEN",
            "principal_amount": Decimal("500000.00"),
            "paid_amount": Decimal("0.00"),
            "remaining_amount": Decimal("500000.00"),
            "supplier_id": uuid4(),
        }

        with patch.object(
            account_payable_service.account_payable_repo,
            "get_account_payable_for_update",
            AsyncMock(return_value=payable),
        ):
            with self.assertRaises(HTTPException) as raised:
                await account_payable_service.create_supplier_payment(
                    session,
                    payable_id=payable_id,
                    payload=SupplierPaymentPayload(amount=Decimal("125000.00")),
                    current_user_id=uuid4(),
                    idempotency_key=None,
                )

        self.assertEqual(raised.exception.status_code, 400)

    async def test_reused_idempotency_key_with_different_payload_is_rejected(self) -> None:
        payable_id = uuid4()
        session = AsyncMock()
        payable = {
            "id": payable_id,
            "status": "OPEN",
            "principal_amount": Decimal("500000.00"),
            "paid_amount": Decimal("125000.00"),
            "remaining_amount": Decimal("375000.00"),
            "supplier_id": uuid4(),
        }
        existing = {
            "id": str(uuid4()),
            "paymentCode": "TTNCC-EXISTING",
            "amount": Decimal("125000.00"),
            "requestFingerprint": "fingerprint-cua-payload-cu",
        }

        with (
            patch.object(account_payable_service.account_payable_repo, "get_account_payable_for_update", AsyncMock(return_value=payable)),
            patch.object(account_payable_service.account_payable_repo, "get_supplier_payment_by_idempotency_key", AsyncMock(return_value=existing)),
        ):
            with self.assertRaises(HTTPException) as raised:
                await account_payable_service.create_supplier_payment(
                    session,
                    payable_id=payable_id,
                    payload=SupplierPaymentPayload(amount=Decimal("150000.00")),
                    current_user_id=uuid4(),
                    idempotency_key="payment-request-001",
                )

        self.assertEqual(raised.exception.status_code, 409)

    async def test_legacy_idempotency_row_with_different_amount_is_rejected(self) -> None:
        payable_id = uuid4()
        session = AsyncMock()
        payable = {
            "id": payable_id,
            "status": "PARTIAL",
            "principal_amount": Decimal("500000.00"),
            "paid_amount": Decimal("125000.00"),
            "remaining_amount": Decimal("375000.00"),
            "supplier_id": uuid4(),
        }
        existing = {
            "id": str(uuid4()),
            "amount": Decimal("125000.00"),
            "method": "BANK_TRANSFER",
            "referenceNo": "UNC-001",
            "note": None,
            "paymentDate": datetime(2026, 8, 2, tzinfo=timezone.utc),
            "requestFingerprint": None,
        }

        with (
            patch.object(account_payable_service.account_payable_repo, "get_account_payable_for_update", AsyncMock(return_value=payable)),
            patch.object(account_payable_service.account_payable_repo, "get_supplier_payment_by_idempotency_key", AsyncMock(return_value=existing)),
        ):
            with self.assertRaises(HTTPException) as raised:
                await account_payable_service.create_supplier_payment(
                    session,
                    payable_id=payable_id,
                    payload=SupplierPaymentPayload(
                        amount=Decimal("150000.00"),
                        method="BANK_TRANSFER",
                        referenceNo="UNC-001",
                    ),
                    current_user_id=uuid4(),
                    idempotency_key="payment-request-legacy-001",
                )

        self.assertEqual(raised.exception.status_code, 409)

    async def test_receipt_prepayment_creates_payment_and_audit_event(self) -> None:
        document_id = uuid4()
        payable_id = uuid4()
        supplier_id = uuid4()
        actor_id = uuid4()
        session = AsyncMock()
        source = {
            "documentId": document_id,
            "referenceCode": "PN-TRA-TRUOC-001",
            "supplierName": "Nhà cung cấp kiểm thử",
            "reason": "NK_MUA",
            "principalAmount": Decimal("500000.00"),
            "postedAt": datetime.now(timezone.utc),
            "metadata": {
                "supplierId": str(supplier_id),
                "invoiceNumber": "HD-TRA-TRUOC-001",
                "paymentMode": "DEBT",
                "paidAmount": "125000.00",
            },
        }
        payment = {"id": str(uuid4()), "amount": Decimal("125000.00")}

        with (
            patch.object(account_payable_service.account_payable_repo, "get_receipt_payable_source", AsyncMock(return_value=source)),
            patch.object(account_payable_service.account_payable_repo, "ensure_supplier_invoice_available", AsyncMock()),
            patch.object(account_payable_service.account_payable_repo, "upsert_payable_from_receipt", AsyncMock(return_value={"id": str(payable_id)})),
            patch.object(account_payable_service.account_payable_repo, "get_supplier_payment_by_idempotency_key", AsyncMock(return_value=None)),
            patch.object(account_payable_service.account_payable_repo, "insert_supplier_payment", AsyncMock(return_value=payment)) as insert_payment,
            patch.object(account_payable_service.account_payable_repo, "insert_payable_event", AsyncMock()) as insert_event,
        ):
            await account_payable_service.ensure_payable_for_completed_receipt(
                session,
                document_id=document_id,
                actor_id=actor_id,
            )

        insert_payment.assert_awaited_once()
        payment_events = [
            call.kwargs for call in insert_event.await_args_list
            if call.kwargs.get("event_type") == "PAYMENT_RECORDED"
        ]
        self.assertEqual(len(payment_events), 1)
        self.assertEqual(payment_events[0]["amount"], Decimal("125000.00"))

    async def test_repeated_idempotency_key_returns_existing_payment(self) -> None:
        payable_id = uuid4()
        session = AsyncMock()
        existing = {
            "id": str(uuid4()),
            "paymentCode": "TTNCC-EXISTING",
            "amount": Decimal("125000.00"),
        }
        payable = {
            "id": payable_id,
            "status": "OPEN",
            "principal_amount": Decimal("500000.00"),
            "paid_amount": Decimal("0.00"),
            "remaining_amount": Decimal("500000.00"),
            "supplier_id": uuid4(),
        }
        payload = SupplierPaymentPayload(amount=Decimal("125000.00"))
        existing["requestFingerprint"] = account_payable_service.supplier_payment_request_fingerprint(payload)

        with (
            patch.object(account_payable_service.account_payable_repo, "get_account_payable_for_update", AsyncMock(return_value=payable)),
            patch.object(account_payable_service.account_payable_repo, "get_supplier_payment_by_idempotency_key", AsyncMock(return_value=existing)),
            patch.object(account_payable_service.account_payable_repo, "insert_supplier_payment", AsyncMock()) as insert_payment,
        ):
            result = await account_payable_service.create_supplier_payment(
                session,
                payable_id=payable_id,
                payload=payload,
                current_user_id=uuid4(),
                idempotency_key="payment-request-001",
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["idempotentReplay"])
        self.assertEqual(result["payment"], existing)
        insert_payment.assert_not_awaited()

    async def test_credit_adjustment_cannot_reduce_principal_below_paid_amount(self) -> None:
        payable_id = uuid4()
        session = AsyncMock()
        payable = {
            "id": payable_id,
            "status": "PARTIAL",
            "principal_amount": Decimal("500000.00"),
            "paid_amount": Decimal("400000.00"),
            "remaining_amount": Decimal("100000.00"),
        }
        payload = AccountPayableAdjustmentPayload(
            type="CREDIT",
            amount=Decimal("150000.00"),
            reason="Giảm giá sau đối soát",
        )

        with patch.object(
            account_payable_service.account_payable_repo,
            "get_account_payable_for_update",
            AsyncMock(return_value=payable),
        ):
            with self.assertRaises(HTTPException) as raised:
                await account_payable_service.create_account_payable_adjustment(
                    session,
                    payable_id=payable_id,
                    payload=payload,
                    current_user_id=uuid4(),
                )

        self.assertEqual(raised.exception.status_code, 400)

    async def test_payment_reversal_reopens_paid_payable(self) -> None:
        payable_id = uuid4()
        payment_id = uuid4()
        session = AsyncMock()
        payable = {
            "id": payable_id,
            "status": "PAID",
            "principal_amount": Decimal("500000.00"),
            "paid_amount": Decimal("500000.00"),
            "remaining_amount": Decimal("0.00"),
        }
        payment = {
            "id": payment_id,
            "amount": Decimal("500000.00"),
            "status": "POSTED",
        }
        payload = SupplierPaymentReversalPayload(
            paymentId=payment_id,
            reason="Ngân hàng hoàn giao dịch",
        )

        with (
            patch.object(account_payable_service.account_payable_repo, "get_account_payable_for_update", AsyncMock(return_value=payable)),
            patch.object(account_payable_service.account_payable_repo, "get_supplier_payment_for_update", AsyncMock(return_value=payment)),
            patch.object(account_payable_service.account_payable_repo, "reverse_supplier_payment", AsyncMock()),
            patch.object(account_payable_service.account_payable_repo, "update_payable_payment_totals", AsyncMock()) as update_totals,
            patch.object(account_payable_service.account_payable_repo, "insert_payable_event", AsyncMock()),
        ):
            result = await account_payable_service.reverse_supplier_payment(
                session,
                payable_id=payable_id,
                payload=payload,
                current_user_id=uuid4(),
            )

        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["remainingAmount"], Decimal("500000.00"))
        update_totals.assert_awaited_once()

    async def test_completed_purchase_receipt_requires_supplier_and_invoice(self) -> None:
        session = AsyncMock()
        source = {
            "documentId": uuid4(),
            "referenceCode": "PN-001",
            "reason": "NK_MUA",
            "principalAmount": Decimal("100000.00"),
            "postedAt": datetime.now(timezone.utc),
            "metadata": {"supplierId": None, "invoiceNumber": None},
        }

        with patch.object(
            account_payable_service.account_payable_repo,
            "get_receipt_payable_source",
            AsyncMock(return_value=source),
        ):
            with self.assertRaises(HTTPException) as raised:
                await account_payable_service.ensure_payable_for_completed_receipt(
                    session,
                    document_id=source["documentId"],
                    actor_id=uuid4(),
                )

        self.assertEqual(raised.exception.status_code, 400)
