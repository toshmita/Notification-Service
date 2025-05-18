from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import pika
import smtplib
import ssl  # Add this line
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/KIIT/OneDrive/Desktop/NotificationSystem/notifications.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.route('/favicon.ico')
def favicon():
    return '', 204

db = SQLAlchemy(app)

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'running',
        'endpoints': {
            'send_notification': '/notifications [POST]',
            'get_user_notifications': '/users/<user_id>/notifications [GET]'
        }
    })

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    # Removed email_password and email_provider fields

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    email = data.get('email')
    phone = data.get('phone')

    user = User(email=email, phone=phone)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'id': user.id,
        'email': user.email,
        'phone': user.phone
    }), 201

# Add after app configuration
# Replace the SMTP configuration with
app.config['SMTP_SERVER'] = 'smtp-mail.outlook.com'
app.config['SMTP_PORT'] = 587
app.config['SMTP_USERNAME'] = os.getenv('SMTP_USERNAME')
app.config['SMTP_PASSWORD'] = os.getenv('SMTP_PASSWORD')

# Replace the existing send_email function
# Update the SMTP configuration
# First, remove the duplicate SMTP configurations and keep only one set
app.config['SMTP_SERVER'] = 'smtp.gmail.com'
app.config['SMTP_PORT'] = 587
app.config['SMTP_USERNAME'] = os.getenv('SMTP_USERNAME')
app.config['SMTP_PASSWORD'] = os.getenv('SMTP_PASSWORD')

def send_email(notification):
    try:
        user = User.query.get(notification.user_id)
        if not user:
            raise Exception("User not found")

        msg = MIMEMultipart()
        msg['Subject'] = 'Notification System'
        msg['From'] = app.config['SMTP_USERNAME']
        msg['To'] = user.email
        
        body = MIMEText(notification.content, 'plain')
        msg.attach(body)

        with smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT']) as server:
            # First establish secure connection
            server.ehlo()
            server.starttls()
            server.ehlo()
            # Then login and send
            server.login(app.config['SMTP_USERNAME'], app.config['SMTP_PASSWORD'])
            server.send_message(msg)

        print(f"📧 Email sent successfully to {user.email}")
        notification.status = 'Delivered'
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        raise

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    retry_count = db.Column(db.Integer, default=0)

@app.route('/notifications', methods=['POST'])
def send_notification():
    data = request.get_json()
    user_id = data.get('user_id')
    notif_type = data.get('type')
    content = data.get('content')

    notification = Notification(user_id=user_id, type=notif_type, content=content)
    db.session.add(notification)
    db.session.commit()

    send_to_queue(notification.id)
    return jsonify({'message': 'Notification queued successfully'}), 201

@app.route('/users/<int:user_id>/notifications', methods=['GET'])
def get_user_notifications(user_id):
    notifications = Notification.query.filter_by(user_id=user_id).all()
    return jsonify([
        {
            'id': n.id,
            'type': n.type,
            'content': n.content,
            'status': n.status
        } for n in notifications
    ]), 200

def send_sms(notification):
    try:
        user = User.query.get(notification.user_id)
        if not user:
            raise Exception("User not found")
        print(f"📱 Simulated SMS to {user.phone}: {notification.content}")
        notification.status = 'Delivered'
    except Exception as e:
        print(f"❌ SMS failed: {str(e)}")
        raise

def send_to_queue(notification_id):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='notifications')
    channel.basic_publish(exchange='', routing_key='notifications', body=str(notification_id))
    connection.close()

def process_notification():
    # Add this line to create application context
    with app.app_context():
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='notifications')

        def callback(ch, method, properties, body):
            notification_id = int(body.decode())
            notification = Notification.query.get(notification_id)
            max_retries = 3

            if notification:
                try:
                    if notification.type == 'Email':
                        send_email(notification)
                    elif notification.type == 'SMS':
                        send_sms(notification)
                    elif notification.type == 'In-App':
                        notification.status = 'Delivered'
                    notification.status = 'Delivered'
                    db.session.commit()
                except Exception as e:
                    notification.retry_count += 1
                    if notification.retry_count < max_retries:
                        notification.status = 'Pending'
                        delay = 5 * (2 ** (notification.retry_count - 1))
                        print(f"⚠️ Retry attempt {notification.retry_count} for notification {notification_id} in {delay} seconds")
                        db.session.commit()
                        retry_queue = f"retry_queue_{delay}"
                        channel.queue_declare(queue=retry_queue)
                        channel.basic_publish(
                            exchange='',
                            routing_key=retry_queue,
                            body=str(notification_id),
                            properties=pika.BasicProperties(expiration=str(delay * 1000))
                        )
                    else:
                        notification.status = 'Failed'
                        print(f"❌ Notification {notification_id} failed after {max_retries} attempts")
                        db.session.commit()

        channel.basic_consume(queue='notifications', on_message_callback=callback, auto_ack=True)
        
        for delay in [5, 10, 20]:
            retry_queue = f"retry_queue_{delay}"
            channel.queue_declare(queue=retry_queue)
            channel.basic_consume(queue=retry_queue, on_message_callback=callback, auto_ack=True)
        
        print('📬 Waiting for notifications...')
        channel.start_consuming()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database created successfully: notifications.db")
    app.run(debug=True)
