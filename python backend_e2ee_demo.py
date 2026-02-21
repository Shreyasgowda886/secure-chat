from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
import base64
import datetime

# ---------------------------
# CREATE TWO USERS
# ---------------------------

print("Generating RSA keys for demo1 and demo2...\n")

demo1_key = RSA.generate(2048)
demo1_private = demo1_key
demo1_public = demo1_key.publickey()

demo2_key = RSA.generate(2048)
demo2_private = demo2_key
demo2_public = demo2_key.publickey()

print("Keys generated successfully ✅\n")

# ---------------------------
# DEMO1 SENDS MESSAGE
# ---------------------------

message = input("demo1 → Enter message for demo2: ")

# Step 1: Generate AES key
aes_key = get_random_bytes(16)

# Step 2: Encrypt message using AES
cipher_aes = AES.new(aes_key, AES.MODE_EAX)
ciphertext, tag = cipher_aes.encrypt_and_digest(message.encode())

# Step 3: Encrypt AES key using demo2 public key
cipher_rsa = PKCS1_OAEP.new(demo2_public)
encrypted_aes_key = cipher_rsa.encrypt(aes_key)

# ---------------------------
# SERVER STORES ONLY ENCRYPTED DATA
# ---------------------------

server_database = []

encrypted_package = {
    "sender": "demo1",
    "receiver": "demo2",
    "encrypted_aes_key": encrypted_aes_key,
    "ciphertext": ciphertext,
    "nonce": cipher_aes.nonce,
    "tag": tag,
    "timestamp": str(datetime.datetime.now())
}

server_database.append(encrypted_package)

print("\n🔐 Server stored encrypted message only.")
print("Encrypted text:", base64.b64encode(ciphertext).decode())

# ====================================================
# DEMO2 RECEIVES AND DECRYPTS
# ====================================================

print("\n📩 demo2 is decrypting message...\n")

received_data = server_database[0]

# Step 4: Decrypt AES key using demo2 private key
cipher_rsa_receiver = PKCS1_OAEP.new(demo2_private)
decrypted_aes_key = cipher_rsa_receiver.decrypt(received_data["encrypted_aes_key"])

# Step 5: Decrypt message using AES
cipher_aes_receiver = AES.new(
    decrypted_aes_key,
    AES.MODE_EAX,
    nonce=received_data["nonce"]
)

decrypted_message = cipher_aes_receiver.decrypt_and_verify(
    received_data["ciphertext"],
    received_data["tag"]
)

print("✅ Decrypted Message:", decrypted_message.decode())
