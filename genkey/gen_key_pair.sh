# https://www.openssl.org/source/

# Generate a private key
# openssl genpkey -algorithm RSA -out private_key.pem

# Generate a private key with the pre-agreed number within 2 party
openssl genpkey -algorithm RSA -out private_key.pem -rand 12345

# Generate a public key with the corrensponding private key
openssl rsa -pubout -in private_key.pem -out public_key.pem
