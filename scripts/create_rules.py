#!/usr/bin/env python3
"""
Docker のネットワーク名から br-<id> を解決し、NAT 断片 (iptables-restore 形式) を生成する。
compose のサブネット・コンテナ IP と齟齬がないよう、定数は compose.yml と揃えてある。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# compose.yml networks.wg / services と一致させる
DEFAULT_SUBNET_WG = "10.42.42.0/24"
DEFAULT_SUBNET_DEFAULT = "172.18.0.0/16"
DEFAULT_SUBNET_DOCKER0 = "172.17.0.0/16"
DEFAULT_IP_NPM = "10.42.42.41"
DEFAULT_IP_WG_EASY = "10.42.42.42"
DEFAULT_PORT_WG_UDP = 51820
DEFAULT_PORT_WG_UI = 51821


def docker_bridge_name(network: str) -> str:
    proc = subprocess.run(
        ["docker", "network", "inspect", network, "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"docker network inspect failed for {network!r}: {proc.stderr.strip()}"
        )
    nid = proc.stdout.strip()
    if len(nid) < 12:
        raise RuntimeError(f"unexpected network id: {nid!r}")
    return f"br-{nid[:12]}"


def render_nat_fragment(
    template_dir: Path,
    *,
    bridge_wg: str,
    bridge_default: str | None,
    subnet_wg: str,
    subnet_default: str,
    subnet_docker0: str,
    ip_npm: str,
    ip_wg_easy: str,
    port_wg_udp: int,
    port_wg_ui: int,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template("nat.fragment.j2")
    return tpl.render(
        bridge_wg=bridge_wg,
        bridge_default=bridge_default,
        subnet_wg=subnet_wg,
        subnet_default=subnet_default,
        subnet_docker0=subnet_docker0,
        ip_npm=ip_npm,
        ip_wg_easy=ip_wg_easy,
        port_wg_udp=port_wg_udp,
        port_wg_ui=port_wg_ui,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render iptables NAT fragment for myGateway.")
    parser.add_argument(
        "--network-wg",
        default=os.environ.get("DOCKER_NETWORK_WG", "mygateway_wg"),
        help="Docker network name for wg (compose: networks.wg)",
    )
    parser.add_argument(
        "--network-default",
        default=os.environ.get("DOCKER_NETWORK_DEFAULT", "mygateway_default"),
        help="Docker network name for project default bridge (optional)",
    )
    parser.add_argument(
        "--no-default-bridge",
        action="store_true",
        help="Do not emit MASQUERADE for compose default network",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "templates",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument("--subnet-wg", default=DEFAULT_SUBNET_WG)
    parser.add_argument("--subnet-default", default=DEFAULT_SUBNET_DEFAULT)
    parser.add_argument("--subnet-docker0", default=DEFAULT_SUBNET_DOCKER0)
    parser.add_argument("--ip-npm", default=DEFAULT_IP_NPM)
    parser.add_argument("--ip-wg-easy", default=DEFAULT_IP_WG_EASY)
    parser.add_argument("--port-wg-udp", type=int, default=DEFAULT_PORT_WG_UDP)
    parser.add_argument("--port-wg-ui", type=int, default=DEFAULT_PORT_WG_UI)
    args = parser.parse_args()

    try:
        bridge_wg = docker_bridge_name(args.network_wg)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1

    bridge_default: str | None = None
    if not args.no_default_bridge:
        try:
            bridge_default = docker_bridge_name(args.network_default)
        except RuntimeError as e:
            print(f"warning: {e}", file=sys.stderr)
            print(
                "hint: use --no-default-bridge if this project has no default network",
                file=sys.stderr,
            )

    text = render_nat_fragment(
        args.template_dir,
        bridge_wg=bridge_wg,
        bridge_default=bridge_default,
        subnet_wg=args.subnet_wg,
        subnet_default=args.subnet_default,
        subnet_docker0=args.subnet_docker0,
        ip_npm=args.ip_npm,
        ip_wg_easy=args.ip_wg_easy,
        port_wg_udp=args.port_wg_udp,
        port_wg_ui=args.port_wg_ui,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
