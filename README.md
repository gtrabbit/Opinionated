# Opinionated

Opinionated is a simple web application built in Python with Flask. The application allows users to catalog their opinions, share them with other users, and vote on each other's opinions. The application also offers an API. For information on this, please visit the "developers" section of the application.

Depending on your system, you may need to run this application within a virtual machine. Please see the "Getting Started" section of [this guide](https://docs.google.com/document/d/1jFjlq_f-hJoAZP8dYuo5H3xY62kGyziQmiv9EPIA7tM/pub?embedded=true) for directions on installing a virtual machine. Once you have the virtual machine installed, proceed to the next step.

The easiest way to preview this application is to use the `'load_start_data.py'` script to generate dummy data within the database. In order to use this script, you will need to install the Random Words library via `pip install random_words`. Next, open a python shell and enter  `py load_start_data.py` (the command my vary depending on your system settings). If an 'Opinionated' database is already present, the script will prompt you to delete this database and replace it with the starter data. 

When you have loaded the starter data, you may start the server with `py server.py`. Now you can visit localhost:5000/ (or localhost:8000 if hosting from within a virtual machine)to view and use the application. 