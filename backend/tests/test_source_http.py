from app.sources.http import default_client


def test_http_client_does_not_follow_redirects():
    client = default_client()
    try:
        assert client.follow_redirects is False
    finally:
        client.close()
