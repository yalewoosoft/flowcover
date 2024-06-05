def id_to_ip(host_id: int) -> str:
    if host_id >= 65536:
        raise ValueError('max 65535 hosts')
    pos_3 = host_id // 256
    pos_4 = host_id % 256
    return f"11.22.{pos_3}.{pos_4}"


def ip_to_id(ip: str) -> int:
    try:
        _, _, pos_3, pos_4 = ip.split('.')
        pos_3 = int(pos_3)
        pos_4 = int(pos_4)
        return pos_3 * 256 + pos_4
    except Exception:
        raise ValueError('invalid ip')
