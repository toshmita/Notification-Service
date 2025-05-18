from app import app, process_notification

if __name__ == '__main__':
    with app.app_context():
        print('🚀 Starting notification consumer...')
        process_notification()