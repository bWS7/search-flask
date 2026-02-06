from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

hash_senha = bcrypt.generate_password_hash("ars291576").decode("utf-8")
print(hash_senha)