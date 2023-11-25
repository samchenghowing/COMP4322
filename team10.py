import os
import socket
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, dh
from cryptography.hazmat.primitives import hashes, serialization, hmac
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import algorithms

debugMode = False

class P2PChat:
    def __init__(self, port):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', self.port))
        self.socket.listen(1)

        # generate RSA private and public key pair
        # self.rsa_private_key = rsa.generate_private_key( 
        #     public_exponent=65537,
        #     key_size=2048,
        # )
        # self.rsa_public_key = self.rsa_private_key.public_key()
        # self.rsa_public_key_bytes = self.rsa_public_key.public_bytes(
        #     encoding=serialization.Encoding.PEM,
        #     format=serialization.PublicFormat.SubjectPublicKeyInfo
        # )

        # Pre-defined DH parameters for key exchange from RFC 3526, Group 14 (2048-bit MODP Group)
        p = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
        g = 2
        parameters_numbers = dh.DHParameterNumbers(p, g)
        self.dh_parameters = parameters_numbers.parameters(default_backend())

        # Used for preventing replay attack
        self.num_of_send = 0
        self.num_of_receive = 0

    def dh_key_exchange(self, client_socket):
        # Generate private and public keys for DH key exchange
        private_key = self.dh_parameters.generate_private_key()
        public_key = private_key.public_key()

        # Serialize public key for transmission
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Send public key
        client_socket.sendall(public_key_bytes)
        if debugMode: print("Sending Public Key:", public_key_bytes)

        # Receive peer's public key
        peer_public_key_bytes = client_socket.recv(1024)
        peer_public_key = serialization.load_pem_public_key(peer_public_key_bytes)
        if debugMode: print("Received Peer Public Key:", peer_public_key_bytes)

        # Generate shared key
        shared_key = private_key.exchange(peer_public_key)

        # Derive a key for symmetric encryption and HMAC
        self.derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'handshake data',
            backend=default_backend()
        ).derive(shared_key)

        if debugMode: print(f"Derived Key: {self.derived_key}")

    def encrypt_message(self, message):
        # Generate random IV
        iv = os.urandom(16)
        # CFB mode more secure
        cipher = Cipher(algorithms.AES(self.derived_key), modes.CFB(iv),
                        backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(message.encode()) + encryptor.finalize()
        # Concat iv and ciphertext as one single message
        return iv + ciphertext

    def decrypt_message(self, ciphertext):
        iv = ciphertext[:16]
        cipher = Cipher(algorithms.AES(self.derived_key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return (decryptor.update(ciphertext[16:]) + decryptor.finalize()).decode()

    def generate_hmac(self, message):
        h = hmac.HMAC(self.derived_key, hashes.SHA256(), backend=default_backend())
        h.update(message)
        return h.finalize()

    def verify_hmac(self, message, received_hmac):
        h = hmac.HMAC(self.derived_key, hashes.SHA256(), backend=default_backend())
        h.update(message)
        try:
            h.verify(received_hmac)
            return True
        except InvalidSignature:
            return False

    def start_server(self):
        while True:
            try:
                client_socket, address = self.socket.accept()
                print(f"\nConnection from {address} formed.")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except OSError:
                break

    def handle_client(self, client_socket):
        self.dh_key_exchange(client_socket)

        while True:
            try:
                received_data = client_socket.recv(2048)

                # Split the whole message into different parts
                encrypted_message, received_hmac, received_count = received_data.rsplit(b'||', 2)

                if debugMode:
                    print(f"\nReceived message (message only): {encrypted_message}")
                    print(f"Received messgae (hmac only): {received_hmac}")
                    print(f"Received messgae (received_count only): {received_count}")
                    print(f"Received message (entire): {received_data}")

                # received_count = int(received_count.decode())
                received_count = int(self.decrypt_message(received_count))

                if received_count != self.num_of_receive:
                    # num_of_receive not increased, as the message is not reliable
                    print("Warning: Possible replay attack detected")
                else:
                    self.num_of_receive += 1

                if self.verify_hmac(encrypted_message, received_hmac):
                    decrypted_message = self.decrypt_message(encrypted_message)
                    print(f"Received: {decrypted_message}")
                else:
                    print("HMAC Verification failed.")

            except Exception as e:
                print(f"\nSome problems occurred: {e}")
                break

        client_socket.close()

    def send_message(self, message):
        encrypted_message = self.encrypt_message(message)
        message_hmac = self.generate_hmac(encrypted_message)
        send_count = self.encrypt_message(str(self.num_of_send))

        if debugMode:
            print(f"Sent message (mesaage only): {encrypted_message}")
            print(f"Sent message (hmac only:) {message_hmac}")
            print(f"Sent message (send_count only): {send_count}")
            print(f"Sent message (entire): {encrypted_message + b'||' + message_hmac + b'||' + send_count}")
        self.peer_socket.sendall(encrypted_message + b'||' + message_hmac + b'||' + send_count)
        self.num_of_send += 1
        return None

    def run(self):
        while True:
            command = input("Enter command (send, exit): ")
            if command == "send":
                message = input("Enter message: ").strip()
                self.send_message(message)
            elif command == "exit":
                self.socket.close()  # Close the listening socket
                if hasattr(self, 'peer_socket'):
                    self.peer_socket.close()  # Close the peer socket if it exists
                print("Program terminated.")
                exit(0)

    def connect_to_peer(self, peer_host, peer_port):
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_socket.connect((peer_host, peer_port))
        self.dh_key_exchange(self.peer_socket)


if __name__ == "__main__":
    port = int(input("Enter your server port: ").strip())
    chat = P2PChat(port)
    server_thread = threading.Thread(target=chat.start_server)
    server_thread.start()

    peer_ip = input("Enter peer's ip: ")
    peer_port = int(input("Enter peer's port: "))
    chat.connect_to_peer(peer_ip, peer_port)

    chat.run()
    server_thread.join()