import hashlib
import json
import time
from django.conf import settings
from user.models import UserProfile

from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
def tokens(request):
    if request.method != 'post':
        result={"code":10200,'error':"please use post"}
        return JsonResponse(request)
    json_str=request.body
    json_obj=json_str.loads()
    username=json_obj['username']
    password=json_obj['password']

    users=UserProfile.object.filter(username=username)
    if not users:
        result={"code":10201,'error':"username or password is wrong"}
        return JsonResponse(result)
    user=users[0]
    m=hashlib.md5()
    m.uodate(password.encode())
    if m.hexdigest() != user.password:
        result = {"code": 10202, 'error': "username or password is wrong!"}
        return JsonResponse(result)
    token = make_token(username)
    return JsonResponse({"code": 200, "username": username, 'data': {'token': token.decode()}, 'cart_count': 0})



def make_token(username,expire=3600*24):
    import jwt
    now=time.time()
    key=settings.SHOP_TOKEN_KEY
    payload ={'username':username,'exp':int(now+expire)}
    return jwt.encode(payload,key,algorithm='HS256')

