KEYWORDS GETTER
===============
This is a service for searching keywords for training courses in distance learning systems [online](https://online.tusur.ru/) and [new-online](https://new-online.tusur.ru/).

LOCAL INSTALLATION
------------------
1. Download and install [docker toolbox](https://github.com/docker/toolbox/releases).
2. Download files from repository: `sudo git clone http://git.2i.tusur.ru/aio/keywords_getter`.
3. Run docker toolbox, go to the directory with the project and type the command: `sh runme.sh`.
4. Open the service:
    > <div>For linux: open browser and type "127.0.0.1:8000"</div>
    > <div>For windows: type `docker-machine ip default` into docker toolbox and copy returned IP into your browser with port 8000.</div>

DEPLOYMENT TO SERVER
--------------------
1. Login as superuser: `sudo su`
2. Upgrade apt: `apt update`
3. Install the necessary packages: `apt install git python3.6 python3-pip libmysqlclient-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev`
4. Download files from repository: `git clone http://git.2i.tusur.ru/aio/keywords_getter`
5. Install virtual environment: `pip3 install virtualenv`
6. Create virtual environment: `virtualenv venv`
7. Activate virtual environment: `source {path_to_venv}/bin/activate`
8. Install project requirements: `pip3 install -r requirements`
9. Install the necessary dictionaries: `python3.6 -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"`
10. Prepare django migrations: `python3.6 manage.py makemigrations`
11. Make django migrations: `python3.6 manage.py migrate`
12. Run the project: `python3.6 manage.py runserver 0.0.0.0:8000`

USAGE
-----

1. Choose distance learning systems [online](https://online.tusur.ru/) or [new-online](https://new-online.tusur.ru/).
2. Enter course IDs, separated by commas.
3. Press the "Get" button and in the table below new lines with data and keywords of the entered courses will appear.  