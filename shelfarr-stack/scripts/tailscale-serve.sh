#!/usr/bin/env bash
# Zet Shelfarr achter HTTPS op je tailnet: https://<machine>.<tailnet>.ts.net
# Alleen bereikbaar voor apparaten in je eigen tailnet.
#
#   ./scripts/tailscale-serve.sh          # gebruikt poort 5056
#   ./scripts/tailscale-serve.sh 5056
#   ./scripts/tailscale-serve.sh --off    # zet de proxy weer uit

set -euo pipefail

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale niet gevonden. Installeer met: curl -fsSL https://tailscale.com/install.sh | sh" >&2
  exit 1
fi

if [[ "${1:-}" == "--off" ]]; then
  tailscale serve --https=443 off
  echo "Tailscale serve uitgezet."
  exit 0
fi

PORT="${1:-5056}"

if ! tailscale status >/dev/null 2>&1; then
  echo "Tailscale draait niet of is niet ingelogd. Start met: sudo tailscale up" >&2
  exit 1
fi

# MagicDNS moet aanstaan voor een ts.net-naam met geldig certificaat.
if ! tailscale status --json | grep -q '"MagicDNSSuffix"'; then
  echo "Waarschuwing: MagicDNS lijkt uit te staan. Zet het aan in de Tailscale admin console." >&2
fi

tailscale serve --bg --https=443 "http://127.0.0.1:${PORT}"

DNSNAME="$(tailscale status --json | sed -n 's/.*"DNSName": *"\([^"]*\)".*/\1/p' | head -1 | sed 's/\.$//')"
echo
echo "Shelfarr staat nu op: https://${DNSNAME:-<jouw-machine>.<tailnet>.ts.net}"
echo
echo "Tip: zet BIND_ADDRESS=127.0.0.1 in .env en herstart (docker compose up -d),"
echo "     dan is poort ${PORT} niet meer los benaderbaar op je LAN."
echo "Let op: gebruik GEEN 'tailscale funnel' — dat zet Shelfarr op het publieke internet."
