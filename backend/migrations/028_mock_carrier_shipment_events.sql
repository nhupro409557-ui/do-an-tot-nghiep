-- Cho phép luồng vận chuyển thử nghiệm ghi thêm trạng thái vận đơn
-- mà không gọi API thật của GHN/GHTK.

ALTER TABLE shipment_events DROP CONSTRAINT IF EXISTS shipment_events_event_code_check;

ALTER TABLE shipment_events
    ADD CONSTRAINT shipment_events_event_code_check
    CHECK (
        event_code IN (
            'CREATED',
            'CONFIRMED',
            'PACKED',
            'HANDED_TO_CARRIER',
            'IN_TRANSIT',
            'DELIVERED',
            'DELIVERY_FAILED',
            'CANCELLED'
        )
    );
