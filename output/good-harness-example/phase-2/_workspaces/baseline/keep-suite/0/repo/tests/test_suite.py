def test_api_version():
    from app.config import API_VERSION

    assert API_VERSION == "1.2.0"


def test_max_retries():
    from app.config import MAX_RETRIES

    assert MAX_RETRIES == 3
