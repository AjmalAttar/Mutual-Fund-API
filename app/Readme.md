### Project Details ###

Application to register user, login and save data about funds in DB and fetching hourly basis
1. Registration, usingusername and password provided by user
2. login, using registered username and password

### Please do create Virtual environment and install requirements.txt file

### Command to Run application ###

uvicorn main:app --reload --port 8000

note: navigate to 'app' directory, first activate virtual environment and then run command to run application

upon successful command run, on terminal you'll see "Uvicorn running on http://127.0.0.1:8000"
1. you can click on hyperlink and add enpoint "/docs"
2. or enter url "http://127.0.0.1:8000/docs" in browser directly