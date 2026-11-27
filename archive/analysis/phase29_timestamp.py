"""Request a third-party RFC 3161 timestamp for the immutable Phase 29 capture report."""
import hashlib
import os
import urllib.request
from pathlib import Path

ROOT = Path('docs')
DOCUMENT = ROOT / 'phase29_gw12_capture.json'
URL = 'https://freetsa.org/tsr'


def tlv(tag, value):
    n = len(value)
    length = bytes([n]) if n < 128 else bytes([0x80 | ((n.bit_length()+7)//8)]) + n.to_bytes((n.bit_length()+7)//8, 'big')
    return bytes([tag]) + length + value


def child(data, offset):
    tag = data[offset]
    start = offset
    offset += 1
    n = data[offset]
    offset += 1
    if n & 0x80:
        count = n & 0x7f
        n = int.from_bytes(data[offset:offset+count], 'big')
        offset += count
    return tag, data[offset:offset+n], data[start:offset+n], offset+n


def main():
    digest = hashlib.sha256(DOCUMENT.read_bytes()).digest()
    algorithm = tlv(0x30, tlv(0x06, bytes.fromhex('608648016503040201')) + tlv(0x05, b''))
    imprint = tlv(0x30, algorithm + tlv(0x04, digest))
    nonce = int.from_bytes(os.urandom(8), 'big')
    nonce_bytes = nonce.to_bytes((nonce.bit_length()+7)//8, 'big')
    if nonce_bytes[0] & 0x80:
        nonce_bytes = b'\0' + nonce_bytes
    query = tlv(0x30, tlv(0x02, b'\x01') + imprint + tlv(0x02, nonce_bytes) + tlv(0x01, b'\xff'))
    qpath = ROOT / 'phase29_capture.tsq'
    rpath = ROOT / 'phase29_capture.tsr'
    qpath.write_bytes(query)
    request = urllib.request.Request(URL, data=query,
        headers={'Content-Type':'application/timestamp-query','Accept':'application/timestamp-reply'})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = response.read()
    tag, body, _, end = child(result, 0)
    if tag != 0x30 or end != len(result):
        raise RuntimeError('Invalid timestamp response sequence')
    status_tag, status_body, _, pos = child(body, 0)
    if status_tag != 0x30:
        raise RuntimeError('Invalid timestamp status')
    code_tag, code, _, _ = child(status_body, 0)
    if code_tag != 0x02 or int.from_bytes(code, 'big') not in (0, 1):
        raise RuntimeError(f'Timestamp authority rejected request: {code.hex()}')
    token_tag, _, token, _ = child(body, pos)
    if token_tag != 0x30:
        raise RuntimeError('Missing signed timestamp token')
    rpath.write_bytes(result)
    (ROOT / 'phase29_capture_token.p7s').write_bytes(token)
    print('document_sha256', digest.hex(), 'response_bytes', len(result), 'token_bytes', len(token))


if __name__ == '__main__':
    main()
