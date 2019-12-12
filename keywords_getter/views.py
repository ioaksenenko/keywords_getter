import re
import os
import requests
import shutil
import django
import bs4
import pymorphy2
import MySQLdb as sql
import pandas as pd
import json

django.setup()

from django.shortcuts import render, redirect
from . import models, settings
from concurrent.futures import ProcessPoolExecutor
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords


def index(request):
    context = {
        'courses': models.Course.objects.all()
    }
    request.session.create()
    if not os.path.exists(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    media_path = os.path.join(settings.MEDIA_ROOT, request.session.session_key)
    if os.path.exists(media_path):
        shutil.rmtree(media_path)
    os.mkdir(media_path)
    return render(request, 'index.html', context)


def get_keywords(request):
    if request.method == 'POST':
        sdo = request.POST.get('sdo')
        cid_list = list(map(int, re.split(r',\s*', request.POST.get('cid-list'))))
        media_path = os.path.join(settings.MEDIA_ROOT, request.session.session_key)
        download_files(sdo, cid_list, media_path)
        words_groups = get_words_from_files(cid_list, media_path)
        for i in range(len(cid_list)):
            kws = calculate_frequencies(words_groups[i])
            name = get_course_name(sdo, cid_list[i])
            models.Course(
                cid=cid_list[i],
                name=name,
                sdo=sdo,
                keywords=json.dumps(kws[:5])
            ).save()
    return redirect('/')


def download_files(sdo, cid_list, media_path):
    futures = []
    for cid in cid_list:
        course_path = os.path.join(media_path, str(cid))
        if os.path.exists(course_path):
            shutil.rmtree(course_path)
        os.mkdir(course_path)
        response = requests.get(
            f'https://{sdo}.tusur.ru/local/filemap/?courseid={cid}&key=cea17f418fc4227b647f75fe66fe859bd24ea752'
        )
        if response.status_code == 200:
            modules = response.json()
            for module in modules:
                fragments = re.findall(r'[a-zA-Zа-яА-Я0-9_\s]+', module['name'])
                module_path = os.path.join(
                    course_path, ''.join(fragments).replace(' ', '_') + '_' + module['contextid']
                )
                if os.path.exists(module_path):
                    shutil.rmtree(module_path)
                os.mkdir(module_path)
                with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
                    for file in module['files']:
                        if re.fullmatch(r'.+\.html', file['name'], re.I):
                            futures.append(executor.submit(download_file, file, module_path))
    for future in futures:
        future.result()
    return futures


def download_file(file, module_path):
    file_path = os.path.join(module_path, file['name'])
    response = requests.get(file['url'])
    if response.status_code == 200:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)


def get_words_from_files(cid_list, media_path):
    futures_groups = []
    for cid in cid_list:
        course_path = os.path.join(media_path, str(cid))
        futures = []
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            for module_name in os.listdir(course_path):
                module_path = os.path.join(course_path, module_name)
                for file_name in os.listdir(module_path):
                    file_path = os.path.join(module_path, file_name)
                    futures.append(executor.submit(get_words_from_file, file_path))
        futures_groups.append(futures)

    words_groups = []
    for futures in futures_groups:
        words = []
        for future in futures:
            words += future.result()
        words_groups.append(words)

    return words_groups


def get_words_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        bs = bs4.BeautifulSoup(f.read(), 'html.parser')
        txt = bs.text
        tokens = get_tokens(txt)
        words = get_words_objects(tokens)
        words = remove_nonexistent_words(words)
        words = get_norm_words(words)
        words = remove_stopwords(words)
    return words


def get_tokens(txt):
    tokenizer = RegexpTokenizer(r'[a-zA-Zа-яА-Я-]+')
    res = list(map(lambda x: x.lower(), tokenizer.tokenize(txt)))
    return res


def get_words_objects(tokens):
    morph = pymorphy2.MorphAnalyzer()
    res = [morph.parse(tocken)[0] for tocken in tokens]
    return res


def remove_nonexistent_words(words):
    res = list(filter(lambda x: x.tag.POS is not None, words))
    return res


def get_norm_words(words):
    res = [word.normal_form for word in words]
    return res


def remove_stopwords(words):
    sws = set(stopwords.words('russian') + stopwords.words('english'))
    res = [word for word in words if word not in sws]
    return res


def calculate_frequencies(words):
    res = []
    uniq_words = list(set(words))
    for word in uniq_words:
        res.append({
            'word': word,
            'frequency': words.count(word) * 100 / len(words)
        })
    res = sorted(res, key=lambda k: k['frequency'], reverse=True)
    return res


def get_course_name(sdo, cid):
    if sdo == 'online':
        connection = sql.connect(
            host='172.16.8.31',
            port=3306,
            user='aio',
            passwd='acw-6l8q',
            db='online',
            charset='utf8',
            init_command='SET NAMES UTF8'
        )
    elif sdo == 'new-online':
        connection = sql.connect(
            host='172.16.9.53',
            port=3306,
            user='aio',
            passwd='acw-6l8q',
            db='moodle_online',
            charset='utf8',
            init_command='SET NAMES UTF8'
        )
    else:
        connection = None

    if connection is not None:
        df = pd.read_sql(
            """
                SELECT
                    c.fullname
                FROM
                    mdl_course AS c
                WHERE
                    c.id = %s
            """,
            connection,
            params=[cid]
        )
        res = df['fullname'].item()
    else:
        res = 'Неизвестный курс'
    return res
