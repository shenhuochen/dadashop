from django.conf.urls import url
from django.urls import path
from . import views
urlpatterns =[
    path("",views.users),
    path("/activation",views.user_active),
    path(r'/<str:username>/address',views.AddressView.as_view()),
    path(r'/<str:username>/address/<int:id>',views.AddressView.as_view()),
    path(r'/weibo/authorization',views.oauth_url),
    path(r'/weibo/users',views.oauth_token),

]