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
import matplotlib.pyplot as plt
import markdown as mkd
import random

django.setup()

from django.shortcuts import render, redirect
from django.http import JsonResponse
from . import models, settings
from concurrent.futures import ProcessPoolExecutor
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
from rutermextract import TermExtractor
from functools import reduce
from pyphrasy.inflect import PhraseInflector
from matplotlib.patches import BoxStyle
from matplotlib import cm
from natsort import natsorted


def index(request):
    # morph_analyzer = pymorphy2.MorphAnalyzer()
    # res = morph_analyzer.parse('приёмника')
    # print(res)

    context = {
        'courses': models.Course.objects.filter(sdo='new-online')
    }
    request.session.create()
    if not os.path.exists(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    media_path = os.path.join(settings.MEDIA_ROOT, request.session.session_key)
    if os.path.exists(media_path):
        shutil.rmtree(media_path)
    os.mkdir(media_path)

    courses = models.Course.objects.all()
    for course in courses:
        for keyword in json.loads(course.keywords):
            if not models.Keyword.objects.filter(word=keyword['word']).exists():
                models.Keyword(word=keyword['word']).save()

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

            keywords = phr[:5] + kws[:5]
            for keyword in keywords:
                if not models.Keyword.objects.filter(word=keyword['word']).exists():
                    models.Keyword(word=keyword['word']).save()

            for course in courses:
                if course.cid == cid_list[i] and course.sdo == sdo:
                    course.keywords = json.dumps(keywords)
                    course.save()
                    course_exist = True
                    break
            if not course_exist:
                models.Course(
                    cid=cid_list[i],
                    name=name,
                    sdo=sdo,
                    keywords=json.dumps(keywords)
                ).save()
        # shutil.rmtree(media_path)
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
                module_path = os.path.join(course_path, str(module['contextid']))
                if os.path.exists(module_path):
                    shutil.rmtree(module_path)
                try:
                    os.mkdir(module_path)
                except OSError as e:
                    if e.errno == 36:
                        print('File name too long.')
                    else:
                        raise
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
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        c = f.read()
        bs = bs4.BeautifulSoup(c, 'html.parser')
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
    # tokenizer = RegexpTokenizer(r'[a-zA-Zа-яА-Я-]+')
    # res = list(map(lambda x: x.lower(), tokenizer.tokenize(txt)))
    res = re.split(r'\s+', txt)
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
    try:
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
    except Exception:
        return 'Неизвестный курс'
    return res


def word_courses(request):
    words = get_words_courses({'sdo': 'new-online'})
    if len(words) == 0:
        words = get_words_courses()
    context = {
        'words': words
    }
    return render(request, 'word-courses.html', context)


def get_words_courses(filter_cond=None):
    res = []
    courses = models.Course.objects.all() if filter_cond is None else models.Course.objects.filter(**filter_cond)
    for course in courses:
        words = json.loads(course.keywords)
        for word in words:
            exist = False
            for element in res:
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
                res.append({
                    'word': word['word'],
                    'courses': [{
                        'name': course.name,
                        'id': course.cid,
                        'sdo': course.sdo,
                        'frequency': word['frequency']
                    }]
                })
    res = [word for word in res if len(word['courses']) != 1 and
           not models.Keyword.objects.filter(word=word['word'])[0].exclude]
    return res


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

            keywords = phr[:5] + kws[:5]
            for keyword in keywords:
                if not models.Keyword.objects.filter(word=keyword['word']).exists():
                    models.Keyword(word=keyword['word']).save()

            name = df_course['fullname'].item()
            courses = models.Course.objects.all()
            course_exist = False
            for course in courses:
                if course.cid == cid_list[i] and course.sdo == sdo:
                    course.keywords = json.dumps(keywords)
                    course.save()
                    course_exist = True
                    break
            if not course_exist:
                models.Course(
                    cid=cid_list[i],
                    name=name,
                    sdo=sdo,
                    keywords=json.dumps(keywords)
                ).save()
        shutil.rmtree(os.path.join(media_path, str(df_course['id'].item())))
    shutil.rmtree(media_path)
    return redirect('/')


"""
def visualisation(request):
    plt.rcParams['figure.figsize'] = [20, 20]
    plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    plt.margins(0.07, 0.02)
    plt.axis('off')

    words = get_words_courses()
    courses = []
    coordinates = []
    j = 0

    for i in range(len(words)):
        plt.text(
            0,
            i / 10,
            words[i]['word'],
            fontsize=14,
            ha="center",
            va="center",
            bbox=dict(
                boxstyle=BoxStyle.Round(rounding_size=1.5, pad=1),
                fc=(0.18, 0.70, 0.49),
                linewidth=0
            )
        )
        for course in words[i]['courses']:
            if course['id'] not in courses:
                plt.text(
                    1,
                    j / 10,
                    course['name'],
                    fontsize=14,
                    ha="center",
                    va="center",
                    bbox=dict(
                        boxstyle=BoxStyle.Square(pad=1),
                        fc=(0.56, 0.84, 0.27),
                        linewidth=0
                    )
                )
                courses.append(course['id'])
                coordinates.append((1, j / 10))
                j += 1

        viridis = cm.get_cmap('viridis', len(courses))
        for course in words[i]['courses']:
            index = courses.index(course['id'])
            plt.plot(
                [0, 1],
                [i / 10, coordinates[index][1]],
                color=viridis.colors[index],
                linestyle='-',
                linewidth=1
            )

    if not os.path.exists(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    img_path = os.path.join(settings.MEDIA_ROOT, 'img')
    if not os.path.exists(img_path):
        os.mkdir(img_path)
    img_path = os.path.join(img_path, 'visualisation.png')

    context = {
        'src': '\\' + img_path[img_path.index('media'):]
    }

    plt.savefig(img_path)

    return render(request, 'visualisation.html', context)
"""


def visualisation(request):
    content = []
    courses = []

    words = get_words_courses({'sdo': 'new-online'})
    if len(words) == 0:
        words = get_words_courses()
    courses_number = 0
    keywords_number = 0
    for word in words:
        depends = []
        for course in word['courses']:
            course_name = course['name'] + ' (' + course['sdo'] + ', ' + str(course['id']) + ')'
            depends.append(course_name)
            if course['sdo'] + str(course['id']) not in courses:
                courses.append(course['sdo'] + str(course['id']))
                content.append({
                    'type': 'discipline',
                    'name': course_name,
                    'depends': []
                })
                courses_number += 1
            content.append({
                'type': 'keyword',
                'name': word['word'],
                'depends': depends
            })
        keywords_number += 1
    file_path = os.path.join(settings.BASE_DIR, 'static', 'json', 'objects.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(content, ensure_ascii=False))

    context = {
        'courses_number': courses_number,
        'keywords_number': keywords_number
    }

    return render(request, 'visualisation.html', context)


def get_depends_markdown(header, arr):
    markdown = f'### {header}'
    if len(arr) > 0:
        markdown += '\n\n'
        for name in arr:
            markdown += '* {{' + name + '}}\n'
        markdown += '\n'
    else:
        markdown += ' *(none)*\n\n'
    return markdown


def get_id_string(name):
    return 'obj-' + re.sub(r'@[^a-z0-9]+@i', '-', name)


def get_html_docs(data, errors, obj):
    file_path = os.path.join(settings.BASE_DIR, 'static', 'json', 'config.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        config = json.loads(f.read())

        name = obj['name'].replace('/', '_')
        filename = os.path.join(settings.BASE_DIR, 'static', 'json', f'{name}.mkdn')

        name = obj['name'].replace('_', '\_')
        type = obj['type']
        if type in config['types']:
            type = config['types'][type]['long']

        markdown = f'## {name} *{type}*\n\n'

        if os.path.exists(filename):
            markdown += '### Documentation\n\n'
            with open(filename, 'r', encoding='utf-8') as f:
                markdown += f.read()
        else:
            markdown += '<div class="alert alert-warning">No documentation for this object</div>'

        if obj:
            markdown += '\n\n'
            markdown += get_depends_markdown('Depends on', obj['depends'])
            markdown += get_depends_markdown('Depended on by', obj['dependedOnBy'])

        arr = markdown.split('{{')
        markdown = arr[0]
        for i in range(1, len(arr)):
            pieces = arr[i].split('}}', 2)
            name = pieces[0]
            id_string = get_id_string(name)
            name_esc = name.replace('_', '\_')
            _class = 'select-object'
            if name not in data:
                _class = ' missing'
                errors.append('Object "{0}" links to unrecognized object "{1}"'.format(obj['name'], name))
            markdown += f'<a href="#{id_string}" class="{_class}" data-name="{name}">{name_esc}</a>'
            markdown += pieces[1]

    html = mkd.markdown(markdown)
    html = html.replace('<pre><code>', '<pre>')
    html = html.replace('</code></pre>', '</pre>')
    return html


def create_json():
    file_path = os.path.join(settings.BASE_DIR, 'static', 'json', 'objects.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        objects = json.loads(f.read())
        data = {}
        errors = []

        for obj in objects:
            data[obj['name']] = obj

        for k, v in data.items():
            v['dependedOnBy'] = []

        for k, v in data.items():
            for depend in v['depends']:
                if depend in data:
                    data[depend]['dependedOnBy'].append(v['name'])
                else:
                    errors.append('Unrecognized dependency: "{0}" depends on "{1}"'.format(v['name'], depend))

        for k, v in data.items():
            v['docs'] = get_html_docs(data, errors, v)

        res = {
            'data': data,
            'errors': errors
        }
        return res


def get_json(request):
    return JsonResponse(create_json())


def get_config(request):
    file_path = os.path.join(settings.BASE_DIR, 'static', 'json', 'config.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        config = json.loads(f.read())
        config['jsonUrl'] = create_json()
    return JsonResponse(config)


def admin_settings(request):
    context = {
        'keywords': natsorted(models.Keyword.objects.all(), key=lambda x: x.word)
    }
    return render(request, 'admin-settings.html', context)


def exclude_words(request):
    if request.method == 'POST':
        keywords = request.POST.getlist('keywords')
        for keyword in models.Keyword.objects.all():
            keyword.exclude = keyword.word not in keywords
            keyword.save()
    return redirect('/admin-settings/')
