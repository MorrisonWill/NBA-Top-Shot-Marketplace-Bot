import base64
import hmac
import struct
import time

def totp(key):
    key = base64.b32decode(key.upper() + '=' * ((8 - len(key)) % 8))
    counter = struct.pack('>Q', int(time.time() / 30))
    mac = hmac.new(key, counter, 'sha1').digest()
    offset = mac[-1] & 0x0f
    binary = struct.unpack('>L', mac[offset:offset + 4])[0] & 0x7fffffff
    return str(binary)[-6:].zfill(6)