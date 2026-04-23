import base64
import json
from typing import Union, List


MULTIBASE_BASE58_BTC = "z"


def bytes_to_multibase(data: bytes) -> str:
    import base58

    return MULTIBASE_BASE58_BTC + base58.b58encode(data).decode()


def base58_encode(data: bytes) -> str:
    import base58

    return base58.b58encode(data).decode()


def base58_decode(data: str) -> bytes:
    import base58

    return base58.b58decode(data)


def multibase_to_bytes(data: str) -> bytes:
    if data.startswith(MULTIBASE_BASE58_BTC):
        import base58

        return base58.b58decode(data[1:])
    raise ValueError(f"Unsupported multibase prefix: {data[0]}")


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def hex_to_bytes(data: Union[str, bytes]) -> bytes:
    if isinstance(data, str):
        return bytes.fromhex(data)
    return data


def bytes_to_hex(data: bytes) -> str:
    return data.hex()


def encode_hex(data: bytes) -> str:
    return data.hex()


def decode_hex(data: Union[str, bytes]) -> bytes:
    if isinstance(data, str):
        return bytes.fromhex(data)
    return data


def encode_uint64(value: int) -> bytes:
    result = []
    while value > 0:
        result.insert(0, value & 0x7F)
        value >>= 7
        if result[0] != value:
            result[0] |= 0x80
    return bytes(result) if result else bytes([0])


def decode_uint64(data: bytes) -> int:
    result = 0
    shift = 0
    for byte in data:
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result


def canonicalize(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def encode_varint(value: int) -> bytes:
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)
