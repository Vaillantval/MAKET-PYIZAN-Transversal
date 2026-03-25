from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('a-propos/', views.apropos, name='apropos'),
    path('faq/',      views.faq,     name='faq'),
    path('contact/',  views.contact, name='contact'),
]
