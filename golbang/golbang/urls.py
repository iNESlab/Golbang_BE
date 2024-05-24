# golbang/urls.py 

from django.contrib import admin
from django.urls import path, include
from allauth.socialaccount.providers import registry
from allauth.socialaccount.providers.google import provider

# GoogleProvider를 수동으로 등록
registry.register(provider.GoogleProvider)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('golbang/accounts/v1/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    #path('golbang/accounts/v2/', include('allauth.urls')),
]
