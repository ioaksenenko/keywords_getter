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
from rutermextract import TermExtractor
from functools import reduce
from pyphrasy.inflect import PhraseInflector


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
        words_groups, phrases_groups = get_words_from_files(cid_list, media_path)
        for i in range(len(cid_list)):
            kws = calculate_words_frequencies(words_groups[i])
            phr = calculate_phrases_frequencies(phrases_groups[i])
            name = get_course_name(sdo, cid_list[i])
            courses = models.Course.objects.all()
            course_exist = False
            for course in courses:
                if course.cid == cid_list[i] and course.sdo == sdo:
                    course.keywords = json.dumps(phr[:5] + kws[:5])
                    course.save()
                    course_exist = True
                    break
            if not course_exist:
                models.Course(
                    cid=cid_list[i],
                    name=name,
                    sdo=sdo,
                    keywords=json.dumps(phr[:5] + kws[:5])
                ).save()
    return redirect('/')


def download_files(sdo, cid_list, media_path):
    futures = []
    for cid in cid_list:
        course_path = os.path.join(media_path, str(cid))
        if os.path.exists(course_path):
            shutil.rmtree(course_path)
        os.mkdir(course_path)
        if sdo == 'online':
            response = requests.get(
                f'https://{sdo}.tusur.ru/local/filemap/?courseid={cid}&key=cea17f418fc4227b647f75fe66fe859bd24ea752'
            )
        else:
            response = requests.post(
                'https://new-online.tusur.ru/webservice/rest/server.php',
                {
                    'wstoken': 'a593d8ce00c027501c9609382ba31d28',
                    'moodlewsrestformat': 'json',
                    'wsfunction': 'local_lismo_api_filemap',
                    'courseid': cid
                }
            )
        if response.status_code == 200:
            modules = response.json()
            for module in modules:
                fragments = re.findall(r'[a-zA-Zа-яА-Я0-9_\s]+', module['name'])
                module_path = os.path.join(
                    course_path, ''.join(fragments).replace(' ', '_') + '_' + str(module['contextid'])
                )
                if os.path.exists(module_path):
                    shutil.rmtree(module_path)
                os.mkdir(module_path)
                with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
                    for file in module['files']:
                        if re.fullmatch(r'.+\.html', file['name'], re.I):
                            futures.append(executor.submit(download_file, file, sdo, module_path))
    for future in futures:
        future.result()
    return futures


def download_file(file, sdo, module_path):
    file_path = os.path.join(module_path, file['name'])
    if sdo == 'online':
        response = requests.get(file['url'])
    else:
        response = requests.post(
            'https://new-online.tusur.ru/webservice/pluginfile.php/' + file['path'],
            {
                'token': 'a593d8ce00c027501c9609382ba31d28'
            }
        )
    if response.status_code == 200:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)


def get_words_from_files(cid_list, media_path):
    term_extractor = TermExtractor()
    morph_analyzer = pymorphy2.MorphAnalyzer()
    inflector = PhraseInflector(morph_analyzer)
    futures_groups = []
    for cid in cid_list:
        course_path = os.path.join(media_path, str(cid))
        futures = []
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            for module_name in os.listdir(course_path):
                module_path = os.path.join(course_path, module_name)
                for file_name in os.listdir(module_path):
                    file_path = os.path.join(module_path, file_name)
                    futures.append(executor.submit(get_words_from_file, term_extractor, morph_analyzer, inflector, file_path))
        futures_groups.append(futures)

    words_groups = []
    phrases_groups = []
    for futures in futures_groups:
        words = []
        phrases = []
        text = ''
        for future in futures:
            w, p = future.result()
            # w, txt = future.result()
            words += w
            # text += txt
            phrases += p
        words_groups.append(words)
        phrases_groups.append(phrases)
        # phrases_groups.append(text)

    return words_groups, phrases_groups


def get_words_from_file(term_extractor, morph_analyzer, inflector, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        bs = bs4.BeautifulSoup(f.read(), 'html.parser')
        txt = bs.text
        tokens = get_tokens(txt)
        words = get_words_objects(morph_analyzer, tokens)
        words = remove_nonexistent_words(words)
        words = filter_by_part_of_speech(words)
        words = get_norm_words(words)
        words = remove_stopwords(words)
        phrases = extract_phrases(term_extractor, morph_analyzer, inflector, txt)
    return words, phrases


def get_tokens(txt):
    tokenizer = RegexpTokenizer(r'[a-zA-Zа-яА-Я-]+')
    res = list(map(lambda x: x.lower(), tokenizer.tokenize(txt)))
    return res


def get_words_objects(morph_analyzer, tokens):
    res = [morph_analyzer.parse(token)[0] for token in tokens]
    return res


def remove_nonexistent_words(words):
    res = list(filter(lambda x: x.tag.POS is not None, words))
    return res


def filter_by_part_of_speech(words):
    parts_of_speech = [
        'NOUN',  # имя существительное
        'ADJF',  # имя прилагательное (полное)
        'ADJS',  # имя прилагательное (краткое)
        'COMP',  # компаратив
        'VERB',  # глагол (личная форма)
        'INFN',  # глагол (инфинитив)
        'PRTF',  # причастие (полное)
        'PRTS',  # причастие (краткое)
        'GRND',  # деепричастие
        # 'NUMR',  # числительное
        # 'ADVB',  # наречие
        # 'NPRO',  # местоимение-существительное
        'PRED',  # предикатив
        # 'PREP',  # предлог
        # 'CONJ',  # союз
        # 'PRCL',  # частица
        'INTJ',  # междометие
    ]
    res = list(filter(lambda x: x.tag.POS in parts_of_speech, words))
    return res


def get_norm_words(words):
    res = [word.normal_form for word in words]
    return res


def remove_stopwords(words):
    sws = set(stopwords.words('russian') + stopwords.words('english'))
    res = [word for word in words if word not in sws]
    return res


def calculate_words_frequencies(words):
    res = []
    uniq_words = list(set(words))
    for word in uniq_words:
        res.append({
            'word': word,
            'frequency': round(words.count(word) * 100 / len(words), 2)
        })
    res = sorted(res, key=lambda k: k['frequency'], reverse=True)
    return res


def calculate_phrases_frequencies(phrases):
    res = []
    #"""
    n = 0
    terms = set([phrase[0] for phrase in phrases])
    uniq_phrases = []
    for term in terms:
        count = 0
        for phrase in phrases:
            if phrase[0] == term:
                count += phrase[1]
        uniq_phrases.append((term, count))
        n += count
    for phrase in uniq_phrases:
        res.append({
            'word': phrase[0],
            'frequency': round(phrase[1] * 100 / n, 2)
        })
    res = sorted(res, key=lambda k: k['frequency'], reverse=True)
    #"""
    """
    rake = Rake()
    terms = rake.apply(phrases)
    for term in terms:
        res.append({
            'word': term[0],
            'frequency': term[1]
        })
    """
    return res


def get_course_name(sdo, cid):
    # return 'Неизвестный курс'
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


def word_courses(request):
    courses = models.Course.objects.all()
    context = {'words': []}
    for course in courses:
        words = json.loads(course.keywords)
        for word in words:
            exist = False
            for element in context['words']:
                if element['word'] == word['word']:
                    element['courses'].append({
                        'name': course.name,
                        'id': course.cid,
                        'sdo': course.sdo,
                        'frequency': word['frequency']
                    })
                    exist = True
                    break
            if not exist:
                context['words'].append({
                    'word': word['word'],
                    'courses': [{
                        'name': course.name,
                        'id': course.cid,
                        'sdo': course.sdo,
                        'frequency': word['frequency']
                    }]
                })
    context['words'] = list(filter(lambda word: len(word['courses']) != 1, context['words']))
    return render(request, 'word-courses.html', context)


def extract_phrases(term_extractor, morph_analyzer, inflector, text):
    res = []
    terms = term_extractor(text)
    for term in terms:
        words = term.normalized.split()
        words_objects = [morph_analyzer.parse(word)[0] for word in words]
        exist_words = []
        for words_object in words_objects:
            if words_object.tag.POS is not None and len(words_object.methods_stack) == 1:
                exist_words.append(words_object)
            else:
                if words_object.word in words:
                    words.remove(words_object.word)
        if 1 < len(exist_words) < 4:
            words = [words_object.word for words_object in exist_words]
            phrase = ' '.join(words)
            phrase = inflector.inflect(phrase, 'nomn')
            res.append((phrase, term.count))
    return res


def get_courses(sdo):
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
                    c.id,
                    c.fullname
                FROM
                    mdl_course AS c
                WHERE
                    c.category = 1
            """,
            connection
        )
        return df
    else:
        return None


def auto_processing(request):
    sdo = 'new-online'
    df_courses = get_courses(sdo)
    media_path = os.path.join(settings.MEDIA_ROOT, request.session.session_key)
    for idx in df_courses.index:
        df_course = df_courses[df_courses.index == idx]
        cid_list = list(df_course['id'])
        download_files(sdo, cid_list, media_path)
        words_groups, phrases_groups = get_words_from_files(cid_list, media_path)
        for i in range(len(cid_list)):
            kws = calculate_words_frequencies(words_groups[i])
            phr = calculate_phrases_frequencies(phrases_groups[i])
            name = df_course['fullname'].item()
            courses = models.Course.objects.all()
            course_exist = False
            for course in courses:
                if course.cid == cid_list[i] and course.sdo == sdo:
                    course.keywords = json.dumps(phr[:5] + kws[:5])
                    course.save()
                    course_exist = True
                    break
            if not course_exist:
                models.Course(
                    cid=cid_list[i],
                    name=name,
                    sdo=sdo,
                    keywords=json.dumps(phr[:5] + kws[:5])
                ).save()
        shutil.rmtree(os.path.join(media_path, str(df_course['id'].item())))
    return redirect('/')
