"""
Controleert afzenderdomeinen via de Spamhaus Domain Blocklist (DBL).
Resultaten worden gecacht zodat elke lookup slechts één keer gebeurt.
"""

import socket

_cache: dict[str, bool] = {}

# Alleen deze returncodes betekenen "geblokkeerd" (Spamhaus spec)
_BLOCKED_PREFIXES = ("127.0.1.", "127.0.2.")


def is_listed(domain: str) -> bool:
    """
    Geeft True als het domein op de Spamhaus DBL staat.
    Mislukt de lookup (timeout, netwerk), dan geeft het False terug.
    """
    domain = domain.lower().strip().rstrip(".")
    if not domain or "." not in domain:
        return False

    if domain in _cache:
        return _cache[domain]

    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(2)
        try:
            results = socket.getaddrinfo(f"{domain}.dbl.spamhaus.org", None)
        finally:
            socket.setdefaulttimeout(old_timeout)

        # Controleer of het een echte blokkering is (niet een NXDOMAIN-workaround)
        listed = any(
            str(r[4][0]).startswith(_BLOCKED_PREFIXES)
            for r in results
        )
        _cache[domain] = listed
        return listed

    except (socket.gaierror, OSError):
        _cache[domain] = False
        return False
