import smtplib
import random

def send_verification_code(email):
    # Generate a random 6-digit verification code
    verification_code = str(random.randint(100000, 999999))

    # Email details
    sender_email = 'aidams1534@gmail.com'
    sender_password = 'hugx uymv swod muvw'

    # SMTP server details
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587

    # Create the email message
    message = f'Subject: Verification Code\n\nYour verification code is: {verification_code}'

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_email, email, message)

        # Close the connection
        server.quit()

        return verification_code

    except Exception as e:
        print(f'An error occurred while sending the verification code: {e}')
        return None
