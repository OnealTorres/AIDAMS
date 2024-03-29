from flask import Blueprint, render_template, request, redirect, session, jsonify, abort
import psycopg2
from psycopg2 import extras
from configparser import ConfigParser
import hashlib
import os
import base64
from .validator import *
from functools import wraps
from datetime import datetime, time, timedelta

views = Blueprint('views', __name__)
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

auth_key = config.get('device_auth','auth_key')


'''
============================================================
     Decorator to check if the user is logged in or is admin
============================================================
'''
#checks if the current user is already logged in, if not display page not found page
def login_required(f):
    @wraps(f)
    def wrapped_view(*args, **kwargs):
        # Check if the user is logged in
        if not session.get('acc_id'):
            return redirect('/page-not-found')
        # Call the original route function
        return f(*args, **kwargs)
    return wrapped_view
#checks if the current user is already logged in and is an admin, if not display page not found page
def admin_required(f):
    @wraps(f)
    def wrapped_admin(*args, **kwargs):
        # Check if the user is logged in
        if not session.get('acc_id'):
            return redirect('/page-not-found')

        is_admin = True if session.get('acc_type') == 'ADMIN' else False
        # Check if the user is an admin
        if not is_admin:
            return redirect('/page-not-found')
        # Call the original route function
        return f(*args, **kwargs)
    return wrapped_admin

'''
==============================
     Landing page part
==============================
'''
@views.route('/')
def index():
    return render_template('index.htm')

@views.route('/service')
def service():
    return render_template('services.htm')

@views.route('/contact')
def contact():
    return render_template('contact.htm')

'''
==============================
         Dashboard 
==============================
'''

@views.route('/dashboard')
@login_required
def dashboard():
    #display all devices and user information
    if request.method == "GET":
        if session.get('acc_type') == 'ADMIN':
            return redirect('/dashboard_admin')
        
        #get current user information
        user_info = get_account(session.get('acc_id'))
        
        #get user profile picture
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        
        
        if session.get('acc_type') == 'OWNER':
            #get devices where owner is the current user
            
            all_device = None
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT *, FLOOR(EXTRACT(EPOCH FROM current_timestamp - date_updated) / 60) AS minutes_passed FROM DEVICE WHERE acc_id = "+str(session.get('acc_id'))+" ORDER BY(dv_id);")
            rows = cur.fetchall()
            cur.close()
            if rows:
                all_device = rows
            return render_template('dashboard.htm', devices = all_device, user = user_info, profile_pic = profile)
        
        elif session.get('acc_type') == 'USER':
            #get devices where a blc_member belongs to a bloc then gets the owner of the bloc then diplay all his/her devices
            
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT *, BLOC.acc_id as owner_id FROM BLC_MEMBER INNER JOIN BLOC USING(blc_id) WHERE BLC_MEMBER.acc_id = "+str(session.get('acc_id'))+" ; ")
            rows = cur.fetchone()
            all_device = None
            if rows:
                #searches the devices under the owner_id from the past query
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("SELECT *, FLOOR(EXTRACT(EPOCH FROM current_timestamp - date_updated) / 60) AS minutes_passed FROM DEVICE WHERE acc_id = "+str(rows['owner_id'])+" ORDER BY(dv_id);")
                rows = cur.fetchall()
                
                if rows:
                    all_device = rows
                    
            user_info = get_account(session.get('acc_id'))
            cur.close()
            profile = None
            if user_info['acc_profile']:
                img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
                profile =  f'data:image/png;base64, {img_data}'

            return render_template('dashboard.htm', devices = all_device, user = user_info, profile_pic = profile)

#lock and unlock button 
@views.route('/dashboard_btn/<int:dv_id>/<dv_status>', methods = ['GET', 'POST'])
@login_required
def dashboard_btn_lock(dv_status, dv_id):
    if request.method == "POST":
        # Convert dv_status from string to boolean
        dv_status = True  if dv_status == 'False' else False
        user_info = get_account(session.get('acc_id'))
        
        # Check if the user is an owner
        if session.get('acc_type') == 'OWNER':
            # Insert history record
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("INSERT INTO HISTORY (acc_id,dv_id,his_dv_status) VALUES ( "+str(session.get('acc_id'))+", "+str(dv_id)+", "+str(dv_status)+" ); ")
            conn.commit()

            # Update device status
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("UPDATE DEVICE SET is_open_toggled = '1' WHERE dv_id = "+str(dv_id)+" ;")
            conn.commit()
            cur.close()
            
            # Fetch device information
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
        
       
        # Check if the user is a regular user
        elif session.get('acc_type') == 'USER':
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT * FROM DEVICE WHERE dv_id = "+str(dv_id)+";")
            row = cur.fetchone()
            
            # Check if device information is retrieved
            if row:
                # Get current time
                current_time = datetime.now().time()

                # Convert the current time to a datetime object with a dummy date
                current_datetime = datetime.combine(datetime.today(), current_time)

                # Add 8 hours to the current datetime
                new_datetime = current_datetime + timedelta(hours=8)

                # Extract the time part from the new datetime
                new_current_time = new_datetime.time
                
                 # Define curfew time and limit
                curfew_time_str = row['dv_curfew_time']
                curfew_limit_time = time(5, 0, 0) #5 AM
                
                # Check if device has curfew and if the current time is within curfew
                if row['dv_curfew'] and new_current_time < curfew_time_str and new_current_time > curfew_limit_time:
                    # Insert history record
                    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                    cur.execute("INSERT INTO HISTORY (acc_id,dv_id,his_dv_status) VALUES ( "+str(session.get('acc_id'))+", "+str(dv_id)+", "+str(dv_status)+" ); ")
                    conn.commit()
                    
                     # Update device status
                    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                    cur.execute("UPDATE DEVICE SET is_open_toggled = '1' WHERE dv_id = "+str(dv_id)+" ; ")
                    conn.commit()
                    cur.close()
                    
                     # Return success message
                    response_data = {"message": "Success"}
                    return jsonify(response_data), 200
                
                # Check if device has curfew and if the current time is outside curfew
                if row['dv_curfew'] and new_current_time > curfew_time_str and new_current_time < curfew_limit_time:
                    abort(404)
                
                else:
                    # If no curfew or not within curfew, update device status
                    # Insert history record
                    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                    cur.execute("INSERT INTO HISTORY (acc_id,dv_id,his_dv_status) VALUES ( "+str(session.get('acc_id'))+", "+str(dv_id)+", "+str(dv_status)+" ); ")
                    conn.commit()
                    
                    # Update device status
                    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                    cur.execute("UPDATE DEVICE SET is_open_toggled = 'True' WHERE dv_id = "+str(dv_id)+" ; ")
                    conn.commit()
                    cur.close()
                    
                     # Return success message
                    response_data = {"message": "Success"}
                    return jsonify(response_data), 200
                    
 
# Dashboard auto-lock route
@views.route('/dashboard-auto-lock/<dv_auto_lock>', methods=['GET', 'POST'])
@login_required
def dashboard_auto_lock(dv_auto_lock):
    # Check if the request method is POST
    if request.method == "POST":
        # Convert dv_auto_lock from string to boolean
        dv_auto_lock = True if dv_auto_lock == 'False' else False

        # Update auto-lock status in the database for the current user
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("UPDATE DEVICE SET is_auto_lock_toggled = 'True' WHERE acc_id = "+str(session.get('acc_id'))+" ;")
        conn.commit()
        cur.close()

        # Return success message
        response_data = {"message": "Success"}
        return jsonify(response_data), 200



# Dashboard curfew route
@views.route('/dashboard-curfew/<dv_curfew>', methods=['GET', 'POST'])
@login_required
def dashboard_curfew(dv_curfew):
    # Check if the request method is POST
    if request.method == "POST":
        # Convert dv_curfew from string to boolean
        dv_curfew = True if dv_curfew == 'False' else False

        # Update curfew status in the database for the current user
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("UPDATE DEVICE SET dv_curfew = "+str(dv_curfew)+", is_curfew_toggled = 'True' WHERE acc_id = "+str(session.get('acc_id'))+" ; ")
        conn.commit()
        cur.close()

        # Return success message
        response_data = {"message": "Success"}
        return jsonify(response_data), 200


'''
==============================
           Profile 
==============================
''' 
#displays the user account information
@views.route('/account', methods = ['GET', 'POST'])
@login_required
def user_account():
    if request.method == "GET":
        img_data = None
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
        return render_template('account.htm', user = user_info, user_profile = f"data:image/png;base64, {img_data}", profile_pic = profile)
 
#sets the new profile picture using change photo button
@views.route('/account/profile', methods = ['GET', 'POST'])
@login_required
def account_profile():
    if request.method == "POST":
        acc_profile = None
        if request.files.get('acc_profile'):
            acc_profile = request.files.get('acc_profile').read()
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("UPDATE ACCOUNT SET acc_profile = (%s)  WHERE acc_id = (%s) ;", (psycopg2.Binary(acc_profile), str(session.get('acc_id'))))
        conn.commit()
        cur.close()
        response_data = {"message": "Success"}
        return jsonify(response_data), 200

#updateds the password of the current user
@views.route('/account/details', methods = ['GET', 'POST'])
@login_required
def account_details():
    if request.method == "POST":
        data = request.json
        #checks if data sent is not empty
        if data:
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            #gets current user information
            user_data = get_account(session.get('acc_id'))
            #checks if the old password matches the new password
            if compare_passwords(hash_password(data['acc_password']),user_data['acc_password']):
                #updates the password
                cur.execute("UPDATE ACCOUNT SET acc_password = '"+hash_password(data['new_acc_password'])+"' WHERE acc_id = "+str(user_data['acc_id'])+" ;")
                conn.commit()
                cur.close()
            else: 
                abort(404)
            #send success message
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
        
    abort(404)

'''
==============================
           Devices 
==============================
'''  
#display the search device page
@views.route('/add_device')
@login_required
def add_device():
   if request.method == "GET":
        all_devices = None
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        return render_template('add_device.htm', devices = all_devices, user = user_info, profile_pic = profile)

#searches the device in the database
@views.route('/add_device/<searched_data>', methods = ['GET', 'POST'])
@login_required
def search_device(searched_data):
    if request.method == 'GET':
        all_devices = None
        #checks if there is an owner
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM DEVICE WHERE dv_key = '"+str(searched_data)+"' AND acc_id IS NULL")
        rows = cur.fetchall()
        cur.close()
        if rows:
            all_devices = rows
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        return render_template('add_device.htm', devices = all_devices, user = user_info , profile_pic = profile)
    
    elif request.method == 'POST':
        data = request.json
        #checks if the current user is already a member if he/she is thn abort
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM BLC_MEMBER WHERE acc_id = "+str(session.get('acc_id'))+" ;")
        row = cur.fetchone()
        if row:
            abort(404)
        
        #if the device exist
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM DEVICE WHERE dv_key = '"+str(searched_data)+"'")
        rows = cur.fetchone()
        
        if rows:
            #checks if the password entered and password of the device matched
            if compare_passwords(hash_password(data['dv_password']),rows['dv_password']):
                #updates the device owner 
                cur.execute("UPDATE DEVICE SET acc_id = '"+str(session.get('acc_id'))+"' WHERE dv_id = "+str(rows['dv_id'])+" ;")
                conn.commit()
                if session.get('acc_type') == 'USER':
                    #updates the current user type to owner
                    cur.execute("UPDATE ACCOUNT SET acc_type = 'OWNER'  WHERE acc_id = "+str(session.get('acc_id'))+" ;")
                    conn.commit()
                    session['acc_type'] = 'OWNER'
                
                cur.close()
                response_data = {"message": "Success"}
                return jsonify(response_data), 200

    abort(404)
'''
==============================
           MEMBERS 
==============================
''' 
#displays all the members in a bloc/ view members   
@views.route('/members')
@login_required
def members():
    if request.method == 'GET':
        all_members = None
        all_profile = []
        #gets all the members in a specific BLOC
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM ACCOUNT LEFT JOIN BLC_MEMBER USING (acc_id) WHERE blc_id IS NOT NULL AND acc_id != "+str(session.get('acc_id'))+" ; ")
        rows = cur.fetchall()
        
        #if the  current user is a member of a bloc
        if rows:
            all_members = rows
            for user in rows:
                if user['acc_profile']:
                    img_data = base64.b64encode(user['acc_profile']).decode('utf-8')
                    all_profile.append( f'data:image/png;base64, {img_data}')
                
                elif not user['acc_profile']:
                    all_profile.append(None)
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        return render_template('members.htm', members = all_members, profiles = all_profile, user = user_info, profile_pic = profile)

#search a member page
@views.route('/members/add_members' , methods = ['GET', 'POST'])
@login_required
def add_members():
    if request.method == 'GET':
        all_members = None
        
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        return render_template('add_members.htm', members = all_members, user = user_info, profile_pic = profile)
    
    elif request.method == 'POST':
        data = request.json
        if data:
            #checks if there is a bloc where current user is a member
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT * FROM BLOC WHERE acc_id = "+str(session.get('acc_id'))+"; ")
            rows = cur.fetchone()
            
            #if owner does not have a bloc yet
            if not rows:
                #create new bloc where the current user is the owner
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("INSERT INTO BLOC (acc_id) VALUES ("+str(session.get('acc_id'))+") RETURNING blc_id; ")
                conn.commit()
                row = cur.fetchone()
                
                #insert the searched member to the bloc of the owner
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("INSERT INTO BLC_MEMBER  (acc_id, blc_id) VALUES ("+str(data['acc_id'])+", "+str(row['blc_id'])+"); ")
                conn.commit()
                
            else:
                #if owner has already a bloc then we insert the new member to the blc_member table
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("INSERT INTO BLC_MEMBER (acc_id, blc_id) VALUES ("+str(data['acc_id'])+", "+str(rows['blc_id'])+"); ")
                conn.commit()
            
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
                
    abort(404)
    
#remove the member in a bloc
@views.route('/members/remove_member' , methods = ['GET', 'POST'])
@login_required
def remove_member():
    if request.method == 'POST':
        data = request.json
        if data:
            #removes the member in the blc_member table
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("DELETE FROM BLC_MEMBER WHERE acc_id = "+str(data['acc_id'])+"; ")
            conn.commit()
            cur.close()
            
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
                
    abort(404)


@views.route('/members/add_members/<searched_data>' , methods = ['GET', 'POST'])
@login_required
def search_members(searched_data):
    if request.method == 'GET':
        all_members = None
        all_profile = []
        
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM ACCOUNT LEFT JOIN BLC_MEMBER USING (acc_id) WHERE blc_id IS NULL AND acc_id != "+str(session.get('acc_id'))+" AND (acc_email = '"+str(searched_data)+"' OR acc_contact = '"+str(searched_data)+"'); ")
        rows = cur.fetchall()
    
        if rows:
            for user in rows:
                    if user['acc_profile']:
                        img_data = base64.b64encode(user['acc_profile']).decode('utf-8')
                        all_profile.append( f'data:image/png;base64, {img_data}')
                    
                    elif not user['acc_profile']:
                        all_profile.append(None)
            
            all_members = rows
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        return render_template('add_members.htm', members = all_members, profiles = all_profile, user = user_info, profile_pic = profile)
        
    abort(404)


@views.route('/monitor')
@login_required
def monitor():
    if request.method == 'GET':
        
        if session.get('acc_type') == 'OWNER':
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT dv_id FROM DEVICE WHERE acc_id = '"+str(session.get('acc_id'))+"';")
            devices = cur.fetchall()
            
            all_history = None
            list_of_devices = ""
            all_profile = []
            index = 0
            if devices:
                for  device in devices:
                    
                    if index == 0:
                        list_of_devices = list_of_devices +" "+str(device['dv_id'])
                    else:
                        list_of_devices = list_of_devices +" , "+str(device['dv_id'])
                    index+=1
                    
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("SELECT *, TO_CHAR(HISTORY.date_created + INTERVAL '8 hours', 'YYYY-MM-DD HH12:MI AM') AS formatted_date_created FROM HISTORY INNER JOIN ACCOUNT USING(acc_id) INNER JOIN DEVICE USING(dv_id) WHERE DEVICE.dv_id IN ( "+list_of_devices+" ) ORDER BY HISTORY.date_created DESC LIMIT 20; ")
                rows = cur.fetchall()
                if rows:
                    for user in rows:
                        if user['acc_profile']:
                            img_data = base64.b64encode(user['acc_profile']).decode('utf-8')
                            all_profile.append( f'data:image/png;base64, {img_data}')
                        
                        elif not user['acc_profile']:
                            all_profile.append(None)
                    all_history = rows
            user_info = get_account(session.get('acc_id'))
            profile = None
            if user_info['acc_profile']:
                img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
                profile =  f'data:image/png;base64, {img_data}'
            return render_template('monitor.htm', history = all_history, profiles = all_profile, user = user_info, profile_pic = profile)
        
        elif session.get('acc_type') == 'USER':
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT *, BLOC.acc_id as owner_id FROM BLC_MEMBER INNER JOIN BLOC USING(blc_id) WHERE BLC_MEMBER.acc_id = "+str(session.get('acc_id'))+" ; ")
            rows = cur.fetchone()
            
            all_history = None
            list_of_devices = ""
            all_profile = []
            index = 0
            profile = None
            user_info = get_account(session.get('acc_id'))
            if rows:
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("SELECT dv_id FROM DEVICE WHERE acc_id = '"+str(rows['owner_id'])+"';")
                devices = cur.fetchall()
                        
                if devices:
                    for  device in devices:
                        if index == 0:
                            list_of_devices = list_of_devices +" "+str(device['dv_id'])
                        else:
                            list_of_devices = list_of_devices +" , "+str(device['dv_id'])
                        index+=1
                        
                    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                    cur.execute("SELECT *, TO_CHAR(HISTORY.date_created + INTERVAL '8 hours', 'YYYY-MM-DD HH12:MI AM') AS formatted_date_created FROM HISTORY LEFT JOIN ACCOUNT USING(acc_id) LEFT JOIN DEVICE USING(dv_id) WHERE DEVICE.dv_id IN ( "+list_of_devices+" ) ORDER BY HISTORY.date_created DESC LIMIT 20; ")
                    rows = cur.fetchall()
                    if rows:
                        for user in rows:
                            if user['acc_profile']:
                                img_data = base64.b64encode(user['acc_profile']).decode('utf-8')
                                all_profile.append( f'data:image/png;base64, {img_data}')
                            
                            elif not user['acc_profile']:
                                all_profile.append(None)
                        all_history = rows
                
                if user_info['acc_profile']:
                    img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
                    profile =  f'data:image/png;base64, {img_data}'
            return render_template('monitor.htm', history = all_history, profiles = all_profile, user = user_info, profile_pic = profile)
    abort(404)
    
      
@views.route('/notification')
@login_required
def notification():
    if request.method == 'GET':
        if session.get('acc_type') == 'OWNER':
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT dv_id FROM DEVICE WHERE acc_id = '"+str(session.get('acc_id'))+"';")
            devices = cur.fetchall()
            
            all_notification = None
            list_of_devices = ""
            index = 0
            if devices:
                for  device in devices:
                    
                    if index == 0:
                        list_of_devices = list_of_devices +" "+str(device['dv_id'])
                    else:
                        list_of_devices = list_of_devices +" , "+str(device['dv_id'])
                    index+=1
                    
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("SELECT *, TO_CHAR(NOTIFICATION.date_created + INTERVAL '8 hours', 'YYYY-MM-DD HH12:MI AM') AS formatted_date_created FROM NOTIFICATION LEFT JOIN DEVICE USING(dv_id) WHERE NOTIFICATION.dv_id IN ( "+list_of_devices+" ) ORDER BY NOTIFICATION.date_created DESC LIMIT 20; ")
                rows = cur.fetchall()
                if rows:
                    all_notification = rows
            user_info = get_account(session.get('acc_id'))
            profile = None
            if user_info['acc_profile']:
                img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
                profile =  f'data:image/png;base64, {img_data}'
            return render_template('notification.htm', notifications = all_notification, user = user_info, profile_pic = profile)
        
        elif session.get('acc_type') == 'USER':
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT *, BLOC.acc_id as owner_id FROM BLC_MEMBER INNER JOIN BLOC USING(blc_id) WHERE BLC_MEMBER.acc_id = "+str(session.get('acc_id'))+" ; ")
            rows = cur.fetchone()
                            
            all_notification = None
            list_of_devices = ""
            index = 0
            profile = None
            user_info = get_account(session.get('acc_id'))
            if rows:
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("SELECT dv_id FROM DEVICE WHERE acc_id = '"+str(rows['owner_id'])+"';")
                devices = cur.fetchall()

                if devices:
                    for  device in devices:
                        
                        if index == 0:
                            list_of_devices = list_of_devices +" "+str(device['dv_id'])
                        else:
                            list_of_devices = list_of_devices +" , "+str(device['dv_id'])
                        index+=1
                        
                    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                    cur.execute("SELECT *, TO_CHAR(NOTIFICATION.date_created + INTERVAL '8 hours', 'YYYY-MM-DD HH12:MI AM') AS formatted_date_created FROM NOTIFICATION LEFT JOIN DEVICE USING(dv_id) WHERE dv_id IN ( "+list_of_devices+" ) ORDER BY NOTIFICATION.date_created DESC LIMIT 20; ")
                    rows = cur.fetchall()
                    if rows:
                        all_notification = rows
                
                
                if user_info['acc_profile']:
                    img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
                    profile =  f'data:image/png;base64, {img_data}'
            return render_template('notification.htm', notifications = all_notification, user = user_info, profile_pic = profile)
    abort(404)



'''
==============================
        User Settings
==============================
'''
@views.route('/settings')
@login_required
def settings():
    if request.method == 'GET':
        auto_lock_set_time = None
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM DEVICE WHERE acc_id ="+str(session.get('acc_id'))+"")
        rows = cur.fetchone()
        
        if rows:
            auto_lock_set_time = rows['dv_auto_lock_time']
  
        curfew_set_time = None
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM DEVICE WHERE acc_id ="+str(session.get('acc_id'))+"")
        rows = cur.fetchone()
        if rows:
            timestamp_from_postgres = rows['dv_curfew_time']
            curfew_set_time = timestamp_from_postgres.strftime("%I:%M:%S %p")
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        
        cur.close()
        return render_template('settings.htm' , auto_lock_time =  auto_lock_set_time, curfew_time = curfew_set_time , user = user_info, profile_pic = profile)

@views.route('/settings/auto_lock')
@login_required
def auto_lock():
    if request.method == 'GET':
        return redirect('/settings/auto_lock/adjust_time')

    abort(404)
        

@views.route('/settings/auto_lock/adjust_time' , methods = ['GET', 'POST'])
@login_required
def auto_lock_edit():
    if request.method == 'GET':
        set_time = None
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM DEVICE WHERE acc_id ="+str(session.get('acc_id'))+"")
        rows = cur.fetchone()
        if rows:
            set_time = rows['dv_auto_lock_time']
        cur.close()
        
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        return render_template('auto_lock_edit.htm' , time =  set_time, user = user_info, profile_pic = profile)

    elif request.method == 'POST':
        data  = request.json
        if data:
            set_time = None
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("UPDATE DEVICE SET dv_auto_lock_time = '"+data['dv_auto_lock_time']+"' WHERE acc_id ="+str(session.get('acc_id'))+"")
            conn.commit()
            cur.close()
            
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
        
    abort(404)


@views.route('/settings/curfew_mode')
@login_required
def curfew_lock():
    return redirect('/settings/curfew-mode/adjust_time')


@views.route('/settings/curfew-mode/adjust_time' , methods = ['GET', 'POST'])
@login_required
def curfew_lock_edit():
    if request.method == 'GET':
        set_time = None
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM DEVICE WHERE acc_id ="+str(session.get('acc_id'))+"")
        rows = cur.fetchone()
        if rows:
            set_time = rows['dv_curfew_time']
        cur.close()
        user_info = get_account(session.get('acc_id'))
        profile = None
        if user_info['acc_profile']:
            img_data = base64.b64encode(user_info['acc_profile']).decode('utf-8')
            profile =  f'data:image/png;base64, {img_data}'
        return render_template('curfew_lock_edit.htm', time =  set_time, user = user_info, profile_pic = profile)
    
    elif request.method == 'POST':
        data  = request.json
        if data:
            
            set_time = None
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("UPDATE DEVICE SET dv_curfew_time = '"+data['dv_curfew_time']+"' WHERE acc_id ="+str(session.get('acc_id'))+"")
            conn.commit()
            cur.close()
            
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
    
'''
==============================
        Admin Page
==============================
'''

@views.route('/dashboard_admin')
@admin_required
def dashboard_admin():
    if request.method == 'GET':
        total_users = 0
        total_active_users = 0
        all_new_users = None
        
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT COUNT(*) FROM ACCOUNT;")
        row = cur.fetchone()
        if row['count'] > 0:
            total_users = row['count']
        
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT COUNT(*) FROM ACCOUNT WHERE acc_status = 'ACTIVE';")
        row = cur.fetchone()
        if row['count'] > 0:
            total_active_users = row['count']
        
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT* FROM ACCOUNT WHERE acc_status = 'ACTIVE' ORDER BY(date_created) ASC LIMIT 20;")
        rows = cur.fetchall()
        if rows:
            all_new_users = rows
    
        return render_template('admin_dashboard.htm',users = total_users, active_users = total_active_users, new_users = all_new_users)


@views.route('/users_admin')
@admin_required
def admin_users():
    all_new_users = None
    all_users = None
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT* FROM ACCOUNT WHERE acc_status = 'ACTIVE' ORDER BY(date_created) ASC LIMIT 20;")
    rows = cur.fetchall()
    if rows:
        all_new_users = rows
    
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT * FROM ACCOUNT ORDER BY(date_created) ASC")
    rows = cur.fetchall()
    if rows:
        all_users = rows
    return render_template('admin_users.htm',users = all_users, new_users = all_new_users)


@views.route('/users_admin/<searched_data>')
@admin_required
def admin_users_search(searched_data):
    all_new_users = None
    all_users = None
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT* FROM ACCOUNT WHERE acc_status = 'ACTIVE' ORDER BY(date_created) ASC LIMIT 20;")
    rows = cur.fetchall()
    if rows:
        all_new_users = rows
    
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT * FROM ACCOUNT WHERE acc_email = '"+searched_data+"' OR acc_contact = '"+searched_data+"' ORDER BY(date_created) ASC")
    rows = cur.fetchall()
    if rows:
        all_users = rows
    return render_template('admin_users.htm',users = all_users, new_users = all_new_users)


@views.route('/users_admin/edit/<int:acc_id>', methods = ['GET', 'POST'])
@admin_required
def edit_users(acc_id):
    if request.method == 'GET':
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT acc_id, acc_fname, acc_mname, acc_lname, acc_password, acc_contact, acc_email, acc_status FROM ACCOUNT WHERE acc_id ="+str(acc_id)+"")
        user_data = cur.fetchone()
        cur.close()
        
        return render_template('edit_admin_users.htm', user = user_data)
    
    elif request.method == 'POST':
        data  = request.json
        if data:
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("UPDATE ACCOUNT SET acc_status = '"+data['acc_status']+"' WHERE acc_id = "+str(acc_id)+" ;")
            conn.commit()
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
            
@views.route('/device_admin')
@admin_required
def admin_device():
    all_devices = None
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT * FROM DEVICE LEFT JOIN ACCOUNT USING(acc_id) ORDER BY(DEVICE.date_created) ASC;")
    rows = cur.fetchall()
    if rows:
        all_devices = rows
    return render_template('admin_device.htm',devices = all_devices)


@views.route('/device_admin/<int:dv_id>')
@admin_required
def admin_search_device(dv_id):
    all_devices = None
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT* FROM DEVICE LEFT JOIN ACCOUNT USING(acc_id) WHERE dv_id = "+str(dv_id)+" ORDER BY(DEVICE.date_created) ASC;")
    rows = cur.fetchall()
    if rows:
        all_devices = rows
    return render_template('admin_device.htm',devices = all_devices)


@views.route('/device_admin/edit/<int:dv_id>', methods = ['GET', 'POST'])
@admin_required
def edit_devices(dv_id):
    if request.method == 'GET':
        devices = None
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        cur.execute("SELECT * FROM DEVICE LEFT JOIN ACCOUNT USING(acc_id) WHERE dv_id = "+str(dv_id)+" ORDER BY(DEVICE.date_created) ASC;")
        rows = cur.fetchone()
        if rows:
            devices = rows
        return render_template('edit_admin_devices.htm', device = devices)
    
    elif request.method == 'POST':
        data  = request.json
        if data:
            acc_id = 0
            
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT acc_id FROM DEVICE WHERE dv_id = "+str(dv_id)+" ")
            conn.commit()
            row = cur.fetchone()
            
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("UPDATE DEVICE SET dv_auto_lock  = 'FALSE', dv_curfew  = 'FALSE'  WHERE dv_id = "+str(dv_id)+" ;")
            conn.commit()
            
            if row['acc_id']:
                acc_id = row['acc_id']
                print(row,"hello")
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("UPDATE ACCOUNT SET is_subscribe = '"+str(data['is_subscribe'])+"' WHERE acc_id = "+str(acc_id)+" ;")
                conn.commit()
                
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
    abort(404)


@views.route('/settings_admin' , methods = ['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'GET':
        user_data= get_account(session.get('acc_id'))
        return render_template('admin_settings.htm', user = user_data)
    
    elif request.method == 'POST':
        user_data = get_account(session.get('acc_id'))
        data = request.json
        if data and compare_passwords(hash_password(data['acc_old_password']), user_data['acc_password']):
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("UPDATE ACCOUNT SET acc_password = '"+hash_password(data['acc_password'])+"' WHERE acc_id = "+str(user_data['acc_id'])+" ;")
            conn.commit()
            response_data = {"message": "Success"}
            return jsonify(response_data), 200
    abort(404)

'''
==============================
        Device Connections
==============================
'''
@views.route('nodeMCU/device/register' , methods = ['GET', 'POST'])
def nodeMCUDeviceRegistration():
    
    if request.method == 'GET':
        dv_name = request.args.get('dv_name')
        dv_key = request.args.get('dv_key')
        dv_password = request.args.get('dv_password')
        conn_auth_key = request.args.get('auth_key')
        
        if conn_auth_key == auth_key:
            
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT * FROM DEVICE WHERE dv_key = '"+dv_key+"';")
            conn.commit()
            row = cur.fetchone()
            
            if not row:
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("INSERT INTO DEVICE (dv_name,dv_key,dv_password) VALUES ('"+dv_name+"','"+dv_key+"','"+hash_password(dv_password)+"') RETURNING dv_id;")
                conn.commit()
                row = cur.fetchone()
                if row: 
                    response_data = {"message": "Registered"}
                    return jsonify(response_data), 200
                else:
                    abort(404)
                    
            return f'{row["dv_auto_lock_time"]},{row["dv_status"]},{row["dv_auto_lock"]}'
    abort(404)
      
@views.route('nodeMCU/device/update' , methods = ['GET', 'POST'])
def nodeMCUDeviceUpdate():
    
    if request.method == 'GET':
        dv_key = request.args.get('dv_key')
        is_opened = request.args.get('is_opened')
        is_auto_lock_activated = request.args.get('is_auto_lock_activated') 
        is_door_opened = request.args.get('is_door_opened')
        is_opened_too_long = request.args.get('is_opened_too_long')
        is_tampered = request.args.get('is_tampered')
        serverLockToggle = request.args.get('serverLockToggle')
        serverAutoLockToggle = request.args.get('serverAutoLockToggle')
        conn_auth_key = request.args.get('auth_key')

        if conn_auth_key == auth_key:
            
            
                
            if serverLockToggle == '1' or serverAutoLockToggle == '1':
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("UPDATE DEVICE SET is_open_toggled = false, is_auto_lock_toggled = false, is_curfew_toggled = false, dv_status = '"+str(is_opened)+"', dv_auto_lock = '"+str(is_auto_lock_activated)+"' WHERE dv_key = '"+dv_key+"';")
                conn.commit()
                serverLockToggle = 0
                serverAutoLockToggle = 0
            
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute("SELECT * FROM DEVICE WHERE dv_key = '"+dv_key+"';")
            conn.commit()
            row = cur.fetchone()
            if not row:
                abort(404)
            
            if is_door_opened == '1' and row["is_open_toggled"] == True:
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("INSERT INTO NOTIFICATION (ntf_type, ntf_message, dv_id) VALUES ('Door Is Open', 'Please close the door.', (SELECT dv_id FROM DEVICE WHERE dv_key = '"+dv_key+"'));")
                conn.commit()
            
            if is_opened_too_long == '1':
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("INSERT INTO NOTIFICATION (ntf_type, ntf_message, dv_id) VALUES ('Door Unattended', 'Please close the door.', (SELECT dv_id FROM DEVICE WHERE dv_key = '"+dv_key+"'));")
                conn.commit()
                
            if is_tampered == '1':
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("INSERT INTO NOTIFICATION (ntf_type, ntf_message, dv_id) VALUES ('Break In Alert', 'Please contact local authorithy.', (SELECT dv_id FROM DEVICE WHERE dv_key = '"+dv_key+"'));")
                conn.commit()
            
            if is_auto_lock_activated == '1':
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
                cur.execute("UPDATE DEVICE SET dv_status = '"+str(is_opened)+"' WHERE dv_key = '"+dv_key+"';")
                conn.commit()
            
            if row["is_open_toggled"]:
               serverLockToggle = 1 
            
            if row["is_auto_lock_toggled"]:
               serverAutoLockToggle = 1 
            
            cur.close()
            current_time = datetime.now().time()
            return f'{row["dv_auto_lock_time"]},{row["dv_curfew_time"]},{row["is_open_toggled"]},{row["is_auto_lock_toggled"]},{row["is_curfew_toggled"]},{serverLockToggle},{serverAutoLockToggle},{current_time}'
            
    abort(404)  
        
'''
==============================
        Error Page
==============================
'''
@views.route('/page-not-found')
def error_404():
    return render_template('404.htm')


#===============================
#     GET EMPLOYEE DETAILS
#===============================

def get_account(acc_id):
    #gets the account details from the db
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT * FROM ACCOUNT WHERE acc_id ="+str(acc_id)+"")
    rows = cur.fetchone()
    cur.close()
    
    session['acc_id'] = rows['acc_id']
    session['acc_type'] = rows['acc_type']
    
    if rows:
        return rows
    else:
        return None
    
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