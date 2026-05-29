"""Follow-up SPL query builders shared by SPL agent and investigation API."""

from __future__ import annotations


def auth_base(auth_index: str) -> str:
    return "\n".join(
        [
            f'search index={auth_index} sourcetype="trustops:auth"',
            '| eval _is_header=if(match(_raw,"^timestamp,user,"),1,0)',
            "| where _is_header=0",
            "| fields - _is_header",
            '| rex field=_raw "^(?<timestamp>[^,]+),(?<user>[^,]+),(?<src_ip>[^,]+),(?<dest_host>[^,]+),(?<action>[^,]+),(?<geo_country>[^,]+),(?<auth_method>[^,]+),(?<risk_score>\\d+),(?<event_type>[^,]+),(?<alert_id>[^,]*),(?<scenario>[^,\\r\\n]+)"',
        ]
    )


def spl_prior_success_logins(user: str, auth_index: str) -> str:
    return "\n".join(
        [
            auth_base(auth_index),
            f'| where user="{user}" AND action="success"',
            '| eval _time=strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")',
            "| sort - _time",
            "| table _time user src_ip geo_country action auth_method risk_score",
            "| head 20",
        ]
    )


def spl_other_users_suspicious_geo(user: str, geo: str, auth_index: str) -> str:
    return "\n".join(
        [
            auth_base(auth_index),
            f'| where geo_country="{geo}" AND action="success" AND user!="{user}"',
            '| eval _time=strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")',
            "| stats count as logins values(user) as users values(src_ip) as src_ips by geo_country",
            "| sort - logins",
        ]
    )


def spl_active_vpn_sessions(user: str, alert_id: str, auth_index: str) -> str:
    return "\n".join(
        [
            auth_base(auth_index),
            f'| where user="{user}" AND action="success" AND auth_method="vpn_saml"',
            f'| where alert_id="{alert_id}" OR match(scenario, "vpn")',
            '| eval _time=strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")',
            "| sort - _time",
            "| table _time user src_ip dest_host geo_country action alert_id scenario",
        ]
    )


def spl_mfa_changes(user: str, auth_index: str) -> str:
    return "\n".join(
        [
            f'search index={auth_index} (sourcetype="trustops:auth" OR sourcetype="trustops:identity")',
            f'| search user="{user}" (mfa OR "multi-factor" OR enrollment OR factor)',
            "| head 50",
            "| table _time user action event_type notes",
        ]
    )


def spl_failed_burst_by_src(alert_id: str, auth_index: str) -> str:
    return "\n".join(
        [
            auth_base(auth_index),
            f'| where alert_id="{alert_id}" AND action="failure"',
            "| stats count as failures values(user) as users values(geo_country) as geos by src_ip",
            "| sort - failures",
        ]
    )


def spl_failed_burst_by_user(user: str, alert_id: str, auth_index: str) -> str:
    return "\n".join(
        [
            auth_base(auth_index),
            f'| where user="{user}" AND action="failure"',
            f'| where alert_id="{alert_id}" OR match(scenario, "vpn")',
            "| stats count as failures values(src_ip) as src_ips values(geo_country) as geos by user",
            "| sort - failures",
        ]
    )
