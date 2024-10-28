from app import create_app

# Initialize Flask application
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=app.config['PORT'])
