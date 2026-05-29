#!/usr/bin/env python3
"""
Generate synthetic VPN/authentication CSV for TrustOps Splunk demos.

Scenario: multiple failed VPN logins for one user, then a successful login
from an unfamiliar geography — mixed with normal activity for that user and
other users.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Fixed seed for reproducible hackathon demos
random.seed(42)

CSV_COLUMNS = [
    "timestamp",
    "user",
    "src_ip",
    "dest_host",
    "action",
    "geo_country",
    "auth_method",
    "risk_score",
    "event_type",
    "alert_id",
    "scenario",
]


def iso(ts: datetime) -> str:
    return ts.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_rows(path: Path) -> int:
    base = datetime(2026, 5, 14, 8, 0, 0, tzinfo=timezone.utc)
    rows: list[dict[str, str]] = []

    def add(
        offset_min: int,
        user: str,
        src_ip: str,
        dest_host: str,
        action: str,
        geo: str,
        auth_method: str,
        risk_score: int,
        event_type: str,
        alert_id: str,
        scenario: str,
    ) -> None:
        ts = base + timedelta(minutes=offset_min)
        rows.append(
            {
                "timestamp": iso(ts),
                "user": user,
                "src_ip": src_ip,
                "dest_host": dest_host,
                "action": action,
                "geo_country": geo,
                "auth_method": auth_method,
                "risk_score": str(risk_score),
                "event_type": event_type,
                "alert_id": alert_id,
                "scenario": scenario,
            }
        )

    # --- Normal baseline activity (jsmith + peers) ---
    for m, user, ip, geo in [
        (0, "jsmith", "203.0.113.10", "United States"),
        (5, "jsmith", "203.0.113.10", "United States"),
        (12, "jdoe", "198.51.100.20", "United States"),
        (18, "jdoe", "198.51.100.20", "United States"),
        (25, "asmith", "192.0.2.55", "Canada"),
        (33, "jsmith", "203.0.113.10", "United States"),
    ]:
        add(
            m,
            user,
            ip,
            "vpn.corp.example",
            "success",
            geo,
            "vpn_saml",
            12 if user == "jsmith" else 8,
            "login_success",
            "",
            "normal_baseline",
        )

    # --- Suspicious chain: failed VPN burst then success from unfamiliar geo ---
    alert_id = "TO-VPN-2026-514"
    fail_ips = [
        ("198.51.100.40", "United States"),
        ("198.51.100.41", "United States"),
        ("198.51.100.42", "United States"),
        ("198.51.100.43", "United States"),
        ("198.51.100.44", "United States"),
        ("198.51.100.45", "United States"),
        ("198.51.100.46", "United States"),
    ]
    t0 = 100
    for i, (ip, geo) in enumerate(fail_ips):
        add(
            t0 + i * 2,
            "jsmith",
            ip,
            "vpn.corp.example",
            "failure",
            geo,
            "vpn_saml",
            45 + i * 5,
            "login_failure",
            alert_id,
            "vpn_brute_then_geo_anomaly",
        )

    add(
        t0 + 20,
        "jsmith",
        "185.220.101.77",
        "vpn.corp.example",
        "success",
        "Romania",
        "vpn_saml",
        88,
        "login_success",
        alert_id,
        "vpn_brute_then_geo_anomaly",
    )

    # --- Other normal users during the same window ---
    for m, user, ip, geo, method in [
        (110, "bwilson", "192.0.2.80", "United Kingdom", "vpn_saml"),
        (115, "jdoe", "198.51.100.20", "United States", "vpn_saml"),
        (122, "asmith", "192.0.2.55", "Canada", "vpn_saml"),
        (130, "mlee", "203.0.113.200", "Japan", "vpn_saml"),
        (140, "bwilson", "192.0.2.80", "United Kingdom", "vpn_saml"),
    ]:
        add(
            m,
            user,
            ip,
            "vpn.corp.example",
            "success",
            geo,
            method,
            10,
            "login_success",
            "",
            "normal_baseline",
        )

    # --- Random noise failures (not tied to main alert) ---
    for i in range(6):
        add(
            160 + i * 4,
            random.choice(["jdoe", "asmith", "mlee"]),
            f"198.51.100.{120 + i}",
            "vpn.corp.example",
            "failure",
            "United States",
            "vpn_saml",
            22,
            "login_failure",
            "",
            "normal_noise",
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write synthetic TrustOps auth CSV for Splunk ingestion."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "synthetic_auth_logs.csv",
        help="Output CSV path (default: ../data/synthetic_auth_logs.csv)",
    )
    args = parser.parse_args()
    n = write_rows(args.output)
    print(f"Wrote {n} data rows (+ header) to {args.output}")


if __name__ == "__main__":
    main()
