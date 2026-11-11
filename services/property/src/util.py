import bcrypt


def hash_password(input_password):
    # stored as text: SQL Server's NVARCHAR column holds a str, not bytes
    return bcrypt.hashpw(input_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(input_password, password_hash):
    return bcrypt.checkpw(input_password.encode("utf-8"), password_hash.encode("utf-8"))
