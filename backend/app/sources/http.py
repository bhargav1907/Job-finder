"""One HTTP client policy for every live source."""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx

USER_AGENT = "FLAJobFinder/0.1 (internal demo)"


def default_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        transport=httpx.HTTPTransport(retries=1),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )


@contextmanager
def client_scope(client: httpx.Client | None) -> Iterator[httpx.Client]:
    """Yield the injected client, or own and close a default one."""
    if client is not None:
        yield client
        return
    with default_client() as owned:
        yield owned
