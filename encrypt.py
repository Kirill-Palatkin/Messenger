from utils import *
import math
import base64
from Crypto.Util.number import getPrime, getRandomRange


p = getPrime(256)
g = 2


def generate_dh_keys():
    private_key = getRandomRange(1, p - 1)
    public_key = pow(g, private_key, p)
    return private_key, public_key


def compute_shared_secret(private_key, other_public_key):
    return pow(other_public_key, private_key, p)


def encrypt(message):
    w = 32
    r = 20

    private_key_alice, public_key_alice = generate_dh_keys()
    private_key_bob, public_key_bob = generate_dh_keys()

    shared_secret_alice = compute_shared_secret(private_key_alice, public_key_bob)
    shared_secret_bob = compute_shared_secret(private_key_bob, public_key_alice)

    assert shared_secret_alice == shared_secret_bob

    shared_secret = shared_secret_alice

    Key = str(shared_secret)
    Key_bit = base64.b64encode(bytes(Key, 'utf-8'))
    Key_bit = bytesToBin(Key_bit)

    while len(Key_bit) % w != 0:
        Key_bit = "0" + Key_bit

    l = int(len(Key_bit) / 8)

    Pw = {16: 0xb7e1, 32: 0xb7e15163, 64: 0xb7e151628aed2a6b}
    Qw = {16: 0x9e37, 32: 0x9e3779b9, 64: 0x9e3779b97f4a7c15}


    W = [Pw[w], ]

    c = int(8 * l / w)

    L = []
    for i in range(c):
        L.append(int("0b" + Key_bit[i:i + w], 2))

    for i in range(2 * r + 4 - 1):
        W.append(mod((W[-1] + Qw[w]), (2 ** w)))

    i, j, a, b = 0, 0, 0, 0

    for count in range(3 * c):
        W[i] = circular_shift(mod((W[i] + a + b), (2 ** w)), w, 3, 'left')
        a = W[i]
        L[j] = circular_shift(mod((L[j] + a + b), (2 ** w)), w, mod((a + b), (2 ** w)), 'left')
        b = L[j]
        i = mod((i + 1), (2 * r + 4))
        j = mod((j + 1), c)

    print("\nСообщение:", message)

    message_bit = base64.b64encode(bytes(message, 'utf-8'))
    message_bit = bytesToBin(message_bit)

    while len(message_bit) % (4 * w) != 0:
        message_bit = "0" + message_bit

    print("Бинарное сообщение:", message_bit)

    encoded_message_bit = ""

    for i in range(0, len(message_bit), 4 * w):
        A = int('0b' + message_bit[i:i + w], 2)
        B = int('0b' + message_bit[i + w:i + 2 * w], 2)
        C = int('0b' + message_bit[i + 2 * w:i + 3 * w], 2)
        D = int('0b' + message_bit[i + 3 * w:i + 4 * w], 2)

        B = mod(B + W[0], 2 ** w)
        D = mod(D + W[1], 2 ** w)

        for i in range(1, r + 1):
            t = circular_shift((B * (2 * B + 1)) % (2 ** w), w, int(math.log(w)), "left")
            u = circular_shift((D * (2 * D + 1)) % (2 ** w), w, int(math.log(w)), "left")

            A = mod((circular_shift(XOR(A, t), w, u, 'left') + W[2 * i]), (2 ** w))
            C = mod((circular_shift(XOR(C, u), w, t, 'left') + W[2 * i + 1]), (2 ** w))

            aa, bb, cc, dd = B, C, D, A
            A, B, C, D = aa, bb, cc, dd

        A = mod(A + W[2 * r + 2], 2 ** w)
        C = mod(C + W[2 * r + 3], 2 ** w)

        encoded_message_bit += bin_expansion(bin(A), w)[2:] + bin_expansion(bin(B), w)[2:] + \
                               bin_expansion(bin(C), w)[2:] + bin_expansion(bin(D), w)[2:]

    return encoded_message_bit, shared_secret