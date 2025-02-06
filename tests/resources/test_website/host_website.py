from flask import Flask, render_template

app = Flask(__name__)

@app.route('/form')
def form():
   return render_template('form.html')

@app.route('/success')
def success():
   return render_template('success.html')

def create_app():
    return app

if __name__ == '__main__':
    app = create_app()
    app.run()