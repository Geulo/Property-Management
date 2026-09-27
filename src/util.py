import bcrypt 

def hash_password(input_password):
    return bcrypt.hashpw(input_password.encode('utf-8'), bcrypt.gensalt())

def check_password(input_password,password_hash):
    return bcrypt.checkpw(input_password.encode('utf-8'), password_hash)
    

