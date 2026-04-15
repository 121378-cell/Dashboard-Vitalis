with open('generate_garmin_tokens.py', 'r') as f: 
    content = f.read() 
content = content.replace('Token.garmin_email != None', 'Token.email != None') 
content = content.replace('token_record.garmin_email', 'token_record.email') 
content = content.replace('token_record.garmin_password', 'token_record.password') 
with open('generate_garmin_tokens.py', 'w') as f: 
    f.write(content) 
print('Fix aplicado') 
