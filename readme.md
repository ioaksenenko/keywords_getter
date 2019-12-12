KEYWORDS GETTER
===============
This is a service for searching keywords for training courses in distance learning systems [online](https://online.tusur.ru/) and [new-online](https://new-online.tusur.ru/).

LOCAL INSTALLATION
------------------
1. Download and install [docker toolbox](https://github.com/docker/toolbox/releases).
2. Run docker toolbox and type the command "sh runme.sh".
3. Open the service:
    > <div>For linux: open browser and type "127.0.0.1:8000"</div>
    > <div>For windows: type `docker-machine ip default` into docker toolbox and copy returned IP into your browser with port 8000.</div>

DEPLOYMENT TO SERVER
--------------------
1. Upgrade apt: `sudo apt update`
2. Install git: `sudo apt install git`
3. Download files from repository: `sudo git clone https://github.com/ioaksenenko/keywords_getter`
4. Install python: `sudo apt install python3.6`
    > If you have the message:
        <div>"E: Unable to locate package python3.6"</div>
        <div>"E: Couldn't find any package by glob 'python3.6'"</div>
        <div>"E: Couldn't find any package by regex 'python3.6'"</div>        
        Run the commands:
        <div>4.1. Install software properties common: `sudo apt install software-properties-common`</div>
        <div>4.2. Add python repository: `sudo add-apt-repository ppa:jonathonf/python-3.6`</div>
        <div>4.3. Upgrade apt: `sudo apt update`</div>
5. Install pip: `sudo apt install python3-pip`
6. Install virtual environment: `sudo pip3 install virtualenv`
7. Create virtual environment: `sudo virtualenv venv`
8. Activate virtual environment: `sudo source {path_to_venv}/bin/activate`
9. Upgrade pip: `python3.6 -m pip install --upgrade pip`
10. Install project requirements: `python3.6 -m pip install -r requirements`
11. Install the necessary dictionaries: `python3.6 -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"`
12. Prepare django migrations: `python3.6 manage.py makemigrations`
13. Make django migrations: `python3.6 manage.py migrate`
14. Prepare django migrations for keywords_getter application: `python3.6 manage.py makemigrations keywords_getter`
15. Make django migrations for keywords_getter application: `python3.6 manage.py migrate keywords_getter`
16. Run the project: `python3.6 manage.py runserver 0.0.0.0:8000`

USAGE
-----

1. Choose distance learning systems [online](https://online.tusur.ru/) or [new-online](https://new-online.tusur.ru/).
2. Enter course IDs, separated by commas.
3. Press the "Get" button and in the table below new lines with data and keywords of the entered courses will appear.  