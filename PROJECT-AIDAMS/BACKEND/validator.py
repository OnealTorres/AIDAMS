from datetime import datetime
import os


# Add Device
def add_device(dv_password):
    if len(dv_password) > 50 or len(dv_password) <=0:
        return False
    return True

# User Account Settings
def user_settings(acc_fname, acc_mname, acc_lname, acc_password, acc_contact, acc_email):
    if len(acc_fname) > 50 :
        return False
    elif len(acc_mname) > 50 :
        return False
    elif len(acc_lname) > 50 :
        return False
    elif len(acc_password) > 50:
        return False
    elif len(acc_contact) > 11:
        return False
    elif not acc_email.find('@') and not acc_email.find('.'):
        return False
    return True

def user_Filetype(acc_profile):
    valid_types = {'.jpeg', '.jpg', '.png'}
    is_valid_type = False
    max_size = 5 * 1024  # 5 MB in KB
    min_size = 0.5 * 1024  # 0.5 MB in KB
   
    if not os.path.exists(acc_profile):
        return False
    
    extension = os.path.splitext(acc_profile)[1].lower()
    filesize = os.stat(acc_profile).st_size/1024
   
    for file_type in valid_types:
        if extension == file_type:
            is_valid_type = True
            break

    return is_valid_type and min_size < filesize < max_size


# SUPPPPPPPPER SULIT ADMIN 
# Edit Admin Users
def admin_user_edit(acc_fname, acc_mname, acc_lname, acc_password, acc_contact, acc_email):
    if len(acc_fname) > 50 :
        return False
    elif len(acc_mname) > 50 :
        return False
    elif len(acc_lname) > 50 :
        return False
    elif len(acc_password) > 50:
        return False
    elif len(acc_contact) > 11:
        return False
    elif not acc_email.find('@') and not acc_email.find('.'):
        return False
    return True

def user_Filetype(acc_profile):
    valid_types = {'.jpeg', '.jpg', '.png'}
    is_valid_type = False
    max_size = 5 * 1024  # 5 MB in KB
    min_size = 0.5 * 1024  # 0.5 MB in KB
   
    if not os.path.exists(acc_profile):
        return False
    
    extension = os.path.splitext(acc_profile)[1].lower()
    filesize = os.stat(acc_profile).st_size/1024
   
    for file_type in valid_types:
        if extension == file_type:
            is_valid_type = True
            break

    return is_valid_type and min_size < filesize < max_size

