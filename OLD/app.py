from app import create_app

# Initialize Flask application
app = create_app()

if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['PORT'])
