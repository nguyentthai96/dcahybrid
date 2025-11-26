from flask import Flask, request, jsonify
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError
from nacl import signing as nacl_signing
import hashlib, base64, json, time

from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, json, os, base64
from ecdsa import SigningKey, NIST256p, VerifyingKey, BadSignatureError
import subprocess, shlex
from nacl import signing
from nacl.signing import VerifyKey
from jwcrypto import jwk

app = Flask(__name__)
CORS(app)  # This allows all origins by default


# ------------------ helpers ------------------
def b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def b64url_decode(s: str) -> bytes:
    padding = (-len(s)) % 4
    return base64.urlsafe_b64decode(s + ("=" * padding))


# convert secp256k1 VerifyingKey to JWK
def secp_pubkey_to_jwk(vk: VerifyingKey):
    raw = vk.to_string()
    x = raw[:32]
    y = raw[32:]
    return {
        "kty": "EC",
        "crv": "secp256k1",
        "x": b64url_encode(x),
        "y": b64url_encode(y)
    }


# convert ed25519 verify key (bytes) to JWK
def ed_pubkey_to_jwk(pub_bytes: bytes):
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": b64url_encode(pub_bytes)
    }


# simple demo DID builder (NOT did:key; demo-only)
def make_demo_did_from_pub(pub_bytes: bytes, method="example"):
    return f"did:{method}:" + b64url_encode(pub_bytes)


# ------------------ in-memory CT log (Merkle tree) ------------------
class CTLog:
    def __init__(self):
        self.leaves = []

    def append(self, entry_bytes: bytes):
        self.leaves.append(hashlib.sha256(entry_bytes).digest())
        return len(self.leaves) - 1

    def merkle_root(self):
        nodes = self.leaves.copy()
        if not nodes:
            return None
        while len(nodes) > 1:
            next_nodes = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                next_nodes.append(hashlib.sha256(left + right).digest())
            nodes = next_nodes
        return nodes[0]


ctlog = CTLog()


# ------------------ DID endpoints ------------------
@app.route('/did/ed25519', methods=['GET'])
def did_ed25519():
    # generate ed25519 keypair using PyNaCl
    sk = nacl_signing.SigningKey.generate()
    vk = sk.verify_key
    pub = vk.encode()

    jwk = ed_pubkey_to_jwk(pub)
    did = make_demo_did_from_pub(pub, method="example")

    did_doc = {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": did,
        "verificationMethod": [{
            "id": did + "#key-1",
            "type": "JsonWebKey2020",
            "controller": did,
            "publicKeyJwk": jwk
        }],
        "assertionMethod": [did + "#key-1"]
    }

    return jsonify({
        "keypair": {
            "privateKey": b64url_encode(sk.encode()),
            "publicKey": b64url_encode(pub)
        },
        "jwk": jwk,
        "didDocument": did_doc
    })


@app.route('/did/secp256k1', methods=['GET'])
def did_secp256k1():
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()
    pub_raw = vk.to_string()
    jwk = secp_pubkey_to_jwk(vk)
    did = make_demo_did_from_pub(pub_raw, method="example")

    did_doc = {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": did,
        "verificationMethod": [{
            "id": did + "#key-1",
            "type": "JsonWebKey2020",
            "controller": did,
            "publicKeyJwk": jwk
        }],
        "assertionMethod": [did + "#key-1"]
    }

    return jsonify({
        "keypair": {
            "privateKey": b64url_encode(sk.to_string()),
            "publicKey": b64url_encode(pub_raw)
        },
        "jwk": jwk,
        "didDocument": did_doc
    })


# ------------------ VCDM 2.0-style sign/verify (simplified) ------------------
@app.route('/sign/vc', methods=['POST'])
def sign_vc():
    body = request.get_json(force=True)
    credential = body.get('credential')
    if credential is None:
        return jsonify({"error": "credential required"}), 400

    # canonicalize (simple sorted JSON for demo only)
    canonical = json.dumps(credential, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).digest()

    priv_b64 = body.get('use_private')
    curve = body.get('curve', 'secp256k1')

    if priv_b64:
        priv = b64url_decode(priv_b64)
        if curve == 'ed25519':
            sk = nacl_signing.SigningKey(priv)
            signature = sk.sign(digest).signature
            vk_bytes = sk.verify_key.encode()
            jwk = ed_pubkey_to_jwk(vk_bytes)
            did = make_demo_did_from_pub(vk_bytes, method='example')
        else:
            sk = SigningKey.from_string(priv, curve=SECP256k1)
            signature = sk.sign_digest(digest)
            vk = sk.get_verifying_key()
            jwk = secp_pubkey_to_jwk(vk)
            did = make_demo_did_from_pub(vk.to_string(), method='example')
    else:
        # generate ephemeral pair
        if curve == 'ed25519':
            sk = nacl_signing.SigningKey.generate()
            vk = sk.verify_key
            signature = sk.sign(digest).signature
            vk_bytes = vk.encode()
            jwk = ed_pubkey_to_jwk(vk_bytes)
            did = make_demo_did_from_pub(vk_bytes, method='example')
        else:
            sk = SigningKey.generate(curve=SECP256k1)
            vk = sk.get_verifying_key()
            signature = sk.sign_digest(digest)
            jwk = secp_pubkey_to_jwk(vk)
            did = make_demo_did_from_pub(vk.to_string(), method='example')

    proof = {
        "type": "EcdsaSecp256k1Signature2019" if curve != 'ed25519' else "Ed25519Signature2018",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "proofPurpose": "assertionMethod",
        "verificationMethod": did + "#key-1",
        "proofValue": b64url_encode(signature)
    }

    signed_cred = dict(credential)
    signed_cred['proof'] = proof

    response = {
        'credential': signed_cred,
        'proof': proof,
        'didDocument': {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": did,
            "verificationMethod": [{
                "id": did + "#key-1",
                "type": "JsonWebKey2020",
                "controller": did,
                "publicKeyJwk": jwk
            }]
        },
    }

    # return ephemeral private key for demo flows only (DO NOT return in prod)
    if not priv_b64:
        if curve == 'ed25519':
            response['ephemeral_privateKey'] = b64url_encode(sk.encode())
        else:
            response['ephemeral_privateKey'] = b64url_encode(sk.to_string())

    # append CT log entry
    ct_entry = json.dumps({
        'timestamp': int(time.time()),
        'did': did,
        'proof': proof
    }).encode()
    idx = ctlog.append(ct_entry)
    response['ct_index'] = idx
    response['ct_root'] = b64url_encode(ctlog.merkle_root()) if ctlog.merkle_root() else None

    return jsonify(response)


@app.route('/verify/vc', methods=['POST'])
def verify_vc():
    body = request.get_json(force=True)
    credential = body.get('credential')
    if credential is None:
        return jsonify({"error": "credential required"}), 400
    proof = credential.get('proof')
    if proof is None:
        return jsonify({"valid": False, "error": "no proof found"}), 400

    # get pubkey from didDocument or explicit pubkey
    pub_b64 = body.get('pubkey')
    pub_bytes = None
    if pub_b64:
        pub_bytes = b64url_decode(pub_b64)
    else:
        dd = body.get('didDocument')
        if dd:
            vm = dd.get('verificationMethod', [])[0]
            jwk = vm.get('publicKeyJwk')
            if jwk:
                if jwk.get('kty') == 'OKP' and jwk.get('crv') == 'Ed25519':
                    pub_bytes = b64url_decode(jwk['x'])
                else:
                    x = b64url_decode(jwk['x']);
                    y = b64url_decode(jwk['y']);
                    pub_bytes = x + y

    if pub_bytes is None:
        # try parse verificationMethod string
        vm = proof.get('verificationMethod', '')
        if vm.startswith('did:example:'):
            raw = vm.split('did:example:')[1].split('#')[0]
            pub_bytes = b64url_decode(raw)

    if pub_bytes is None:
        return jsonify({"valid": False, "error": "no pubkey provided"}), 400

    # reconstruct digest (credential without proof)
    cred_no_proof = dict(credential)
    cred_no_proof.pop('proof', None)
    canonical = json.dumps(cred_no_proof, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).digest()

    sig = b64url_decode(proof.get('proofValue'))

    # attempt verify ed25519 then secp256k1
    valid = False
    try:
        # if length matches ed25519 pub (32) try ed25519
        if len(pub_bytes) == 32:
            vk = nacl_signing.VerifyKey(pub_bytes)
            vk.verify(digest, sig)
            valid = True
        else:
            vk = VerifyingKey.from_string(pub_bytes, curve=SECP256k1)
            valid = vk.verify_digest(sig, digest)
    except BadSignatureError:
        valid = False
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 400

    return jsonify({"valid": bool(valid)})


# ------------------ File sign/verify endpoints (simple) ------------------
@app.route('/sign/file', methods=['POST'])
def sign_file():
    f = request.files.get('file')
    if not f:
        return jsonify({"error": "file required"}), 400
    data = f.read()
    digest = hashlib.sha256(data).digest()

    # default secp256k1 ephemeral
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()
    signature = sk.sign_digest(digest)

    resp = {
        'hash': b64url_encode(digest),
        'signature': b64url_encode(signature),
        'pubkey': b64url_encode(vk.to_string()),
        'private_key_ephemeral': b64url_encode(sk.to_string())
    }

    # append to CT log
    ct_entry = json.dumps({'timestamp': int(time.time()), 'file_hash': resp['hash']}).encode()
    idx = ctlog.append(ct_entry)
    resp['ct_index'] = idx
    resp['ct_root'] = b64url_encode(ctlog.merkle_root()) if ctlog.merkle_root() else None

    return jsonify(resp)


@app.route('/verify/file', methods=['POST'])
def verify_file():
    pubkey_b64 = request.form.get('pubkey')
    signature_b64 = request.form.get('signature')
    f = request.files.get('file')
    if not (pubkey_b64 and signature_b64 and f):
        return jsonify({"error": "pubkey, signature, file required"}), 400
    pub = b64url_decode(pubkey_b64)
    sig = b64url_decode(signature_b64)
    data = f.read()
    digest = hashlib.sha256(data).digest()
    try:
        if len(pub) == 32:
            vk = nacl_signing.VerifyKey(pub)
            vk.verify(digest, sig)
            valid = True
        else:
            vk = VerifyingKey.from_string(pub, curve=SECP256k1)
            valid = vk.verify_digest(sig, digest)
            valid = bool(valid)
    except BadSignatureError:
        valid = False
    return jsonify({"valid": valid})


# ------------------ Schnorr ZK Proof-of-possession (non-interactive) ------------------
from hashlib import sha256
from ecdsa.ellipticcurve import Point
from ecdsa.ecdsa import generator_secp256k1

G = generator_secp256k1


def int_from_bytes(b):
    return int.from_bytes(b, 'big')


@app.route('/zk/schnorr/prove', methods=['POST'])
def schnorr_prove():
    body = request.get_json(force=True)
    # accept privkey (b64) or generate ephemeral
    priv_b64 = body.get('priv')
    if priv_b64:
        priv = b64url_decode(priv_b64)
        sk_int = int_from_bytes(priv)
    else:
        # generate ephemeral scalar
        sk = SigningKey.generate(curve=SECP256k1)
        priv = sk.to_string()
        sk_int = int_from_bytes(priv)

    # compute pubpoint
    pub_point = sk_int * G
    # nonce r
    r_int = int_from_bytes(hashlib.sha256(b"nonce" + priv + str(time.time()).encode()).digest())
    R_point = r_int * G

    # compute challenge c = H(R || P)
    Rx = R_point.x();
    Ry = R_point.y()
    Px = pub_point.x();
    Py = pub_point.y()
    c = int.from_bytes(sha256(
        Rx.to_bytes(32, 'big') + Ry.to_bytes(32, 'big') + Px.to_bytes(32, 'big') + Py.to_bytes(32, 'big')).digest(),
                       'big')

    z = (r_int + c * sk_int) % G.order()

    proof = {
        'R': b64url_encode(Rx.to_bytes(32, 'big') + Ry.to_bytes(32, 'big')),
        'z': b64url_encode(z.to_bytes(32, 'big'))
    }

    return jsonify({'proof': proof, 'pub': b64url_encode(Px.to_bytes(32, 'big') + Py.to_bytes(32, 'big')),
                    'priv_demo': b64url_encode(priv)})


@app.route('/zk/schnorr/verify', methods=['POST'])
def schnorr_verify():
    body = request.get_json(force=True)
    proof = body.get('proof')
    pub_b64 = body.get('pub')
    if not (proof and pub_b64):
        return jsonify({'valid': False, 'error': 'proof and pub required'}), 400

    R_bytes = b64url_decode(proof['R'])
    z_bytes = b64url_decode(proof['z'])
    pub_bytes = b64url_decode(pub_b64)

    Rx = int_from_bytes(R_bytes[:32]);
    Ry = int_from_bytes(R_bytes[32:])
    Px = int_from_bytes(pub_bytes[:32]);
    Py = int_from_bytes(pub_bytes[32:])
    z = int_from_bytes(z_bytes)

    R_point = Point(G.curve(), Rx, Ry)
    P_point = Point(G.curve(), Px, Py)

    # recompute challenge
    c = int.from_bytes(sha256(
        Rx.to_bytes(32, 'big') + Ry.to_bytes(32, 'big') + Px.to_bytes(32, 'big') + Py.to_bytes(32, 'big')).digest(),
                       'big')

    # check: z*G == R + c*P
    left = z * G
    right = R_point + c * P_point

    valid = (left.x() == right.x() and left.y() == right.y())

    return jsonify({'valid': bool(valid)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
