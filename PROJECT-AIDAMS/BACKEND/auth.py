from flask import Blueprint, render_template, request, jsonify, abort, session,redirect
import psycopg2
from psycopg2 import extras
from configparser import ConfigParser
import hashlib
import os
from .smtp import send_verification_code

auth = Blueprint('auth', __name__)

# Configuration
config = ConfigParser()

# Read the config.ini file
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
config.read(config_path)

#database connection
conn = psycopg2.connect(
    host=config.get('conn', 'host'),
    port=config.get('conn', 'port'),
    database=config.get('conn', 'database'),
    user=config.get('conn', 'user'),
    password=config.get('conn', 'password')
)

 

'''
==============================
         Sign up
==============================
'''

@auth.route('/signup/confirmation/<acc_email>', methods=['GET','POST'])
def confirmation(acc_email):
    if request.method == 'GET':
        session['ver_code'] = send_verification_code(acc_email)
        return render_template('confirmation.htm')
    
    elif request.method =='POST':
        data = request.json 
        if data['code'] == session.get('ver_code'):
            data = data['acc_data']
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT * FROM ACCOUNT WHERE acc_email='"+data['acc_email']+"' OR (acc_fname = '"+data['acc_fname']+"' AND acc_mname = '"+data['acc_lname']+"' AND acc_lname = '"+data['acc_fname']+"' )OR acc_contact = '"+data['acc_contact']+"';")
            rows = cur.fetchone()
            if (rows):
                abort(404)    
            
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("INSERT INTO ACCOUNT (acc_fname, acc_mname, acc_lname, acc_email, acc_contact , acc_password ) VALUES ( '"+data['acc_fname'].title()+"', '"+data['acc_mname'].title()+"','"+data['acc_lname'].title()+"','"+data['acc_email']+"', '"+data['acc_contact']+"' , '"+hash_password(data['acc_password'])+"');")
            conn.commit()
            cur.close()  
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
    abort(404)

@auth.route('/signup/user_verified')
def user_verified():
    return render_template('user_verified.htm')

@auth.route('/signup', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('signup.htm')
    abort(404)


'''
==============================
            Sign In
==============================
'''
 
@auth.route('/signin', methods=['GET','POST'])
def loginAuthentication():
    if request.method == 'GET':
        return render_template('sign_in.htm')
    if request.method == 'POST':
        data = request.json
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT acc_id,acc_type FROM ACCOUNT WHERE acc_email='"+data['acc_email']+"' AND acc_password = '"+hash_password(data['acc_password'])+"' AND acc_status = 'ACTIVE';")
        rows = cur.fetchone()
        cur.close()
        
        if rows:
            session['acc_id'] = rows['acc_id']
            session['acc_type'] = rows['acc_type']
            
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
        else:
            abort(404)        
    abort(404)

'''
==============================
       Logout
==============================
'''  
@auth.route('/logout', methods=['GET','POST'])
def logout():
    session.clear()
    return redirect('/?')

'''
==============================
         Miscellaneous
==============================
''' 

def hash_password(password):
    max_length = 50

    # Using SHA-256 for hashing
    hash_object = hashlib.sha256(password.encode())
    
    # Get the hexadecimal digest
    hex_digest = hash_object.hexdigest()
    
    # Truncate to the desired length
    truncated_digest = hex_digest[:max_length]
    
    return truncated_digest

def compare_passwords(hashed_password1, hashed_password2):
    return hashed_password1 == hashed_password2

