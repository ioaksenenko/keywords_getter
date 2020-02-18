"""keywords_getter URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views
from . import settings
from django.contrib.staticfiles.urls import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('get-keywords/', views.get_keywords, name='get-keywords'),
    path('word-courses/', views.word_courses, name='word-courses'),
    path('auto-processing/', views.auto_processing, name='auto-processing'),
    path('visualisation/', views.visualisation, name='visualisation'),
    path('get-json/', views.get_json, name='get-json'),
    path('get-config/', views.get_config, name='get-config'),
    path('admin-settings/', views.admin_settings, name='admin-settings'),
    path('exclude-words/', views.exclude_words, name='exclude-words'),
    path('courses/', views.courses, name='courses'),
    path('general-settings/', views.general_settings, name='general-settings'),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)