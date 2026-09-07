from app.schemas.notification import NotificationListFilters, NotificationMarkReadRequest


def test_notification_filters_defaults() -> None:
    filters = NotificationListFilters()
    assert filters.page == 1
    assert filters.page_size == 20


def test_notification_mark_read_request_defaults() -> None:
    payload = NotificationMarkReadRequest()
    assert payload.status == "read"
