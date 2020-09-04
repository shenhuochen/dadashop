from dadashop.celery import app
from django.core.mail import  send_mail
from django.conf import settings
@app.task
def send_active_email_celery(email_address,verify_url):
    subject = 'dadashop激活邮件'
    html_message='''
    <p>尊敬的用户 您好</p>
    <P>您的激活链接为<a href='%s' target="_blank">点击激活</a></p>
    '''%(verify_url)
    send_mail(subject,"",settings.EMAIL_HOST_USER,[email_address],html_message=html_message)

