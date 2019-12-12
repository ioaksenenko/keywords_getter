FROM python:3
RUN mkdir /home/services
RUN mkdir /home/services/keywords_getter
WORKDIR /home/services/keywords_getter
ADD . /home/services/keywords_getter
RUN pip3 install --upgrade pip
RUN pip3 install -r /home/services/keywords_getter/requirements
RUN python3 -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
RUN python3 manage.py makemigrations keywords_getter
RUN python3 manage.py migrate