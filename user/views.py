import base64
import hashlib
import random
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import JsonResponse
from django.core.cache import cache
from django.core.mail import send_mail
import json
from django.views import View
from .tasks import send_active_email_celery
from dtoken.views import make_token
from .models import UserProfile, Address
from tools.logging_dec import logging_check


# Create your views here.
def users(request):
    if request.method == 'POST':
        data = request.body
        json_obj = json.loads(data)
        username = json_obj['uname']
        password = json_obj['password']
        phone = json_obj['phone']
        email = json_obj['email']
        if len(password) < 6:
            result = {'code': 10100, "error": 'password is wrong'}
            return JsonResponse(result)
        # 用户名是否可用;已注册的话给个错误返回
        old_user = UserProfile.objects.filter(username=username)
        if old_user:
            result = {'code': 10100, "error": 'The username is already existed'}
            return JsonResponse(result)
        # 创建用户 密码用md5
        m = hashlib.md5()
        m.update(password.encode())

        try:
            user = UserProfile.objects.create(username=username, password=m.hexdigest(), phone=phone, email=email)
        except Exception as e:
            return JsonResponse({'code': 10100, "error": 'The username is already existed'})
        token = make_token(username)

        code = "%s" % (random.randint(1000, 9999))
        code_str = code + "_" + username
        code_bs = base64.urlsafe_b64encode(code_str.encode())
        cache.set('email_active_%s' % (username), code, 3600 * 24 * 3)
        verify_url = 'http://127.0.0.1:7000/dadashop/templates/active.html?code=%s' % (code_bs.decode())
        send_active_email_celery.delay(email, verify_url)
        return JsonResponse({"code": 200, "username": username, 'data': {'token': token.decode()}, 'cart_count': 0})


def send_active_email(email_address, verify_url):
    subject = 'dadashop激活邮件'
    html_message = '''
    <p>尊敬的用户 您好</p>
    <P>您的激活链接为<a href='%s' target="_blank">点击激活</a></p>
    ''' % (verify_url)
    send_mail(subject, "", settings.EMAIL_HOST_USER, [email_address], html_message=html_message)


def user_active(request):
    # 激活用户
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'code': 10103, 'error': 'please give me code!'})
    code_str = base64.urlsafe_b64decode(code.encode()).decode()
    random_code, username = code_str.split('_')
    old_code = cache.get('email_active_%s' % (username))
    if not old_code:
        return JsonResponse({'code': 10104, 'error': 'link is wrong'})
    if random_code != old_code:
        return JsonResponse({'code': 10105, 'error': 'link is wrong!!'})
    try:
        user = UserProfile.objects.get(username=username)
    except Exception as e:
        return JsonResponse({'code': 10106, 'error': ' get user is error!!'})
    user.is_active = True
    user.save()
    cache.delete('email_active_%s' % (username))
    return JsonResponse({'code': 200, 'data': "ok"})


# FBV-函数 视图
def address_view(request):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        pass


# CBV -类 视图
class AddressView(View):
    @logging_check
    def dispatch(self, request, *args, **kwargs):
        json_str = request.body
        request.json_obj = {}
        if json_str:
            json_obj = json.loads(json_str)
            request.json_obj = json_obj
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, username):
        user = request.myuser
        all_addr = user.address_set.filter(is_active=True)
        res = []
        for addr in all_addr:
            addr_data = {}
            addr_data["id"] = addr.id
            addr_data["address"] = addr.address
            addr_data["receiver"] = addr.receiver
            addr_data["tag"] = addr.tag
            addr_data["receiver_mobile"] = addr.receiver_mobile
            addr_data["postcode"] = addr.postcode
            addr_data["is_default"] = addr.is_default
            res.append(addr_data)
        return JsonResponse({"code": 200, "addresslist": res})

    def post(self, request, username):
        print(request.myuser)
        data = request.json_obj
        receiver = data['receiver']
        address = data['address']
        receiver_phone = data['receiver_phone']
        postcode = data['postcode']
        tag = data['tag']
        user = request.myuser
        old_addr = Address.objects.filter(user_profile=user)
        default_status = False
        if not old_addr:
            default_status = True
        Address.objects.create(user_prifile=user, receiver=receiver, address=address, receiver_phone=receiver_phone,
                               postcode=postcode, tag=tag, is_default=default_status)
        return JsonResponse({'code': 200, 'data': "ok"})

    def put(self, request, username, id):
        if not id:
            result = {'code': 10107, 'error': 'id is not given'}
            return JsonResponse(result)
        data = request.json_obj
        receive = data['receiver']
        receive_phone = data['receiver_phone']
        address = data['address']
        tag = data['tag']
        data_id = data['id']
        if int(id) != data_id:
            result = {'code': 10108, 'error': 'id is wrong'}
            return JsonResponse(result)

        filter_address = Address.objects.filter(id=id)
        filter_address=filter_address[0]
        try:
            filter_address.receive = receive
            filter_address.receive_phone = receive_phone
            filter_address.address = address
            filter_address.tag = tag
            filter_address.save()

        except Exception as e:
            print('error is %s' % (e))
            return JsonResponse({'code':10109, 'error': 'change address failed'})
        return  JsonResponse({'code':200, "data":"地址修改成功！"})


    def delete(self,request,username,id):
        if not id:
            result = {'code': 10107, 'error': 'id is not given'}
            return JsonResponse(result)
        filter_address = Address.objects.filter(id=id)
        filter_address = filter_address[0]
        if filter_address.is_default:
            result = {'code': 10108, 'error': 'default address can not be deleted'}
            return JsonResponse(result)
        try:
            filter_address.is_active=False
            filter_address.save()
        except Exception as e:
            result = {'code': 10109, 'error': 'deleting address  failed'}
            return JsonResponse(result)
        return JsonResponse({'code': 200, "data": "删除地址成功！"})

def oauth_url(request):
    params={
        'response_type':'code',
        'client_id':settings.WEIBO_CLIENT_ID,
        'redirect_uri':settings.WEIBO_REDIRECT_URL
    }
    weibo_url='https://api.weibo.com/oauth2/authorize?'
    url =weibo_url+urlencode(params)
    print(url)
    return JsonResponse({'code':200,'oauth_url':url})
def oauth_token(request):
    code= request.GET.get('code')
    token_url='https://api.weibo.com/oauth2/access_token'
    req_data ={
        'client_id':settings.WEIBO_CLIENT_ID,
        'client_secret':settings.WEIBO_CLIENT_SECRET,
        'grant_type':'authorization_code',
        'redirect_uri': settings.WEIBO_REDIRECT_URL,
        "code":code
    }
    response=requests.post(token_url,data=req_data)
    if response.status_code ==200:
        res_data=json.loads(response.text)
    else:
        print('change code error %s'%(response.status_code))
        return JsonResponse({'code':10108,'error':'weibo error'})
    if res_data.get('error'):
        print(res_data.get('error'))
        return JsonResponse({'code': 10108, 'error': 'weibo error'})
    print(res_data)

    return JsonResponse({'code':200})

















