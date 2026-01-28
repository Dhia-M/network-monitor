"""
Flask Web Application
Main web server for the monitoring dashboard
"""

from flask import Flask

app = Flask(__name__, 
    template_folder='../../templates',
    static_folder='../../static'
)

# Disable template caching to always load fresh templates
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Import routes after app creation to avoid circular imports
from src.api import routes

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
