# Notification System

A Flask-based notification system with RabbitMQ for handling Email, SMS, and In-App notifications.

## Features
- Multiple notification types (Email, SMS, In-App)
- Queue-based processing with RabbitMQ
- Automatic retry mechanism
- RESTful API endpoints
- Email notifications via Gmail SMTP

## Prerequisites
- Python 3.7+
- RabbitMQ Server
- Gmail Account with App Password
- Postman

## Setup Instructions

1. Clone the repository:
```bash
git clone [https://github.com/toshmita/Notification-Service.git]
```
2. Install dependencies:
```bash
pip install flask flask-sqlalchemy pika python-dotenv
 ```
3. Create .env file with your Gmail credentials:
```env
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your-app-password
 ```
4. Start RabbitMQ server
5. Run the application:
```bash
python app.py
 ```
6. In a new terminal, start the consumer:
```bash
python -c "from app import process_notification; process_notification()"
 ```
## API Documentation
### Create User
POST /users

```json
{
    "email": "user@example.com",
    "phone": "1234567890"
}
 ```
### Send Notification
POST /notifications

```json
{
    "user_id": 1,
    "type": "Email",
    "content": "Test notification"
}
 ```
### Get User Notifications
GET /users/<user_id>/notifications

## Architecture
- Flask web framework
- SQLite database
- RabbitMQ message queue
- Gmail SMTP for email delivery
##  Example Usage

```bash
# Create a user
curl -X POST -H "Content-Type: application/json" -d '{"email": "test@example.com", "phone": "+1234567890"}' http://localhost:5000/users

# Send a notification
curl -X POST -H "Content-Type: application/json" -d '{"user_id": 1, "type": "Email", "content": "Hello User!"}' http://localhost:5000/notifications
```
* Run the application again
* Create a user in Postman with simplified JSON
```json
{
"email" : "user@example.com" ,
"phone" : "1234567890"
}
```
* Send a notification 
```json
{
    "user_id": 1,
    "type": "Email",
    "content": "Test notification"
}

 ```

## Assumptions

* RabbitMQ is running locally.

## Optional - Deployment

* You can deploy this app using any cloud provider (like AWS, Heroku, or Vercel).
* Make sure to configure environment variables for RabbitMQ and database connections.
