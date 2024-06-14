def id_to_ip(host_id: int) -> str:
    if host_id >= 65536:
        raise ValueError('max 65535 hosts')
    return f"2001:db8:1:{host_id:x}::1"


def ip_to_id(ip: str) -> int:
    try:
        _, _, _, id_hex, _ = ip.split(':')
        return int(id_hex, 16)
    except Exception:
        raise ValueError('invalid ip')

def id_to_mac(host_id: int) -> str:
    return '24:CD:AB:CD:AB:CD'