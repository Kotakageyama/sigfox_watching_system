from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, loads, dumps
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, resolve_url, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import generic, View
from .forms import (
    LoginForm, UserCreateForm, UserUpdateForm, MyPasswordChangeForm,
    MyPasswordResetForm, MySetPasswordForm, EmailChangeForm
)
import json
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SigfoxData
from django.utils import timezone
import datetime

User = get_user_model()


class Top(generic.TemplateView):
    template_name = 'dashboard/top.html'
    model = SigfoxData

    def get(self, request, *args, **kwargs):
        DIFF_JST_FROM_UTC = 9
        start_date = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
        #start_date = timezone.now().date()
        end_date = start_date - timezone.timedelta(days=1)
        end_week = start_date - timezone.timedelta(weeks=1)
        datas_list = SigfoxData.objects.filter(date__range=(end_date,start_date)).order_by('date')
        datas_week_list = SigfoxData.objects.filter(date__range=(end_week,start_date)).order_by('date')
        # temp_list = SigfoxData.objects.filter(date__range=(start_date, end_date)).order_by('date')
        # humid_list = SigfoxData.objects.filter(date__range=(start_date, end_date)).order_by('date')

        context = {
            #'labels_list': [i.date.strftime('%Y/%M/%d') for i in datas_list],
            #'labels_list': [i.date.strftime("%Y/%m/%d %H:%M:%S") for i in datas_list],
            #'labels_list': [timezone.localtime(i.date).isoformat(timespec='seconds') for i in datas_list],
            'labels_list': [timezone.localtime(i.date).strftime("%Y-%m-%d %H:%M:%S") for i in datas_list],
            #'labels_list': datas_list[0].date,
            #'labels_list': datas_list[0].date,
            'temp_list': [i.temp for i in datas_list],
            'humid_list': [i.humid for i in datas_list],
            'labels_week_list': [timezone.localtime(i.date).strftime("%Y-%m-%d %H:%M:%S") for i in datas_week_list],
            'temp_week_list': [i.temp for i in datas_week_list],
            'humid_week_list': [i.humid for i in datas_week_list],
        }
        #print(start_date,end_date)
        print(context)
        return render(request, 'dashboard/top.html', context)


class Login(LoginView):
    """ログインページ"""
    form_class = LoginForm
    template_name = 'dashboard/login.html'

    # def get_success_url(self):
    #     url = self.get_redirect_url()
    #     return url or resolve_url('dashboard:user_detail', pk=self.request.user.pk)


class Logout(LogoutView):
    """ログアウトページ"""
    template_name = 'dashboard/top.html'


class UserCreate(generic.CreateView):
    """ユーザー仮登録"""
    template_name = 'dashboard/user_create.html'
    form_class = UserCreateForm

    def form_valid(self, form):
        """仮登録と本登録用メールの発行."""
        # 仮登録と本登録の切り替えは、is_active属性を使うと簡単です。
        # 退会処理も、is_activeをFalseにするだけにしておくと捗ります。
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # アクティベーションURLの送付
        current_site = get_current_site(self.request)
        domain = current_site.domain
        context = {
            'protocol': 'https' if self.request.is_secure() else 'http',
            'domain': domain,
            'token': dumps(user.pk),
            'user': user,
        }

        subject = render_to_string('dashboard/mail_template/create/subject.txt', context)
        message = render_to_string('dashboard/mail_template/create/message.txt', context)

        user.email_user(subject, message)
        return redirect('dashboard:user_create_done')


class UserCreateDone(generic.TemplateView):
    """ユーザー仮登録したよ"""
    template_name = 'dashboard/user_create_done.html'


class UserCreateComplete(generic.TemplateView):
    """メール内URLアクセス後のユーザー本登録"""
    template_name = 'dashboard/user_create_complete.html'
    timeout_seconds = getattr(settings, 'ACTIVATION_TIMEOUT_SECONDS', 60*60*24)  # デフォルトでは1日以内

    def get(self, request, **kwargs):
        """tokenが正しければ本登録."""
        token = kwargs.get('token')
        try:
            user_pk = loads(token, max_age=self.timeout_seconds)

        # 期限切れ
        except SignatureExpired:
            return HttpResponseBadRequest()

        # tokenが間違っている
        except BadSignature:
            return HttpResponseBadRequest()

        # tokenは問題なし
        else:
            try:
                user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                return HttpResponseBadRequest()
            else:
                if not user.is_active:
                    # まだ仮登録で、他に問題なければ本登録とする
                    user.is_active = True
                    user.save()
                    return super().get(request, **kwargs)

        return HttpResponseBadRequest()


class OnlyYouMixin(UserPassesTestMixin):
    """本人か、スーパーユーザーだけユーザーページアクセスを許可する"""
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.pk == self.kwargs['pk'] or user.is_superuser


class UserDetail(OnlyYouMixin, generic.DetailView):
    """ユーザーの詳細ページ"""
    model = User
    template_name = 'dashboard/user_detail.html'  # デフォルトユーザーを使う場合に備え、きちんとtemplate名を書く


class UserUpdate(OnlyYouMixin, generic.UpdateView):
    """ユーザー情報更新ページ"""
    model = User
    form_class = UserUpdateForm
    template_name = 'dashboard/user_form.html'  # デフォルトユーザーを使う場合に備え、きちんとtemplate名を書く

    def get_success_url(self):
        return resolve_url('dashboard:user_detail', pk=self.kwargs['pk'])


class PasswordChange(PasswordChangeView):
    """パスワード変更ビュー"""
    form_class = MyPasswordChangeForm
    success_url = reverse_lazy('dashboard:password_change_done')
    template_name = 'dashboard/password_change.html'


class PasswordChangeDone(PasswordChangeDoneView):
    """パスワード変更しました"""
    template_name = 'dashboard/password_change_done.html'


class PasswordReset(PasswordResetView):
    """パスワード変更用URLの送付ページ"""
    subject_template_name = 'dashboard/mail_template/password_reset/subject.txt'
    email_template_name = 'dashboard/mail_template/password_reset/message.txt'
    template_name = 'dashboard/password_reset_form.html'
    form_class = MyPasswordResetForm
    success_url = reverse_lazy('dashboard:password_reset_done')


class PasswordResetDone(PasswordResetDoneView):
    """パスワード変更用URLを送りましたページ"""
    template_name = 'dashboard/password_reset_done.html'


class PasswordResetConfirm(PasswordResetConfirmView):
    """新パスワード入力ページ"""
    form_class = MySetPasswordForm
    success_url = reverse_lazy('dashboard:password_reset_complete')
    template_name = 'dashboard/password_reset_confirm.html'


class PasswordResetComplete(PasswordResetCompleteView):
    """新パスワード設定しましたページ"""
    template_name = 'dashboard/password_reset_complete.html'


class EmailChange(LoginRequiredMixin, generic.FormView):
    """メールアドレスの変更"""
    template_name = 'dashboard/email_change_form.html'
    form_class = EmailChangeForm

    def form_valid(self, form):
        user = self.request.user
        new_email = form.cleaned_data['email']

        # URLの送付
        current_site = get_current_site(self.request)
        domain = current_site.domain
        context = {
            'protocol': 'https' if self.request.is_secure() else 'http',
            'domain': domain,
            'token': dumps(new_email),
            'user': user,
        }

        subject = render_to_string('dashboard/mail_template/email_change/subject.txt', context)
        message = render_to_string('dashboard/mail_template/email_change/message.txt', context)
        send_mail(subject, message, None, [new_email])

        return redirect('dashboard:email_change_done')


class EmailChangeDone(LoginRequiredMixin, generic.TemplateView):
    """メールアドレスの変更メールを送ったよ"""
    template_name = 'dashboard/email_change_done.html'


class EmailChangeComplete(LoginRequiredMixin, generic.TemplateView):
    """リンクを踏んだ後に呼ばれるメアド変更ビュー"""
    template_name = 'dashboard/email_change_complete.html'
    timeout_seconds = getattr(settings, 'ACTIVATION_TIMEOUT_SECONDS', 60*60*24)  # デフォルトでは1日以内

    def get(self, request, **kwargs):
        token = kwargs.get('token')
        try:
            new_email = loads(token, max_age=self.timeout_seconds)

        # 期限切れ
        except SignatureExpired:
            return HttpResponseBadRequest()

        # tokenが間違っている
        except BadSignature:
            return HttpResponseBadRequest()

        # tokenは問題なし
        else:
            User.objects.filter(email=new_email, is_active=False).delete()
            request.user.email = new_email
            request.user.save()
            return super().get(request, **kwargs)

@csrf_exempt
def jsonReceive(request):
    if request.method == 'GET':
        return JsonResponse({})

        # JSON文字列
    datas = json.loads(request.body)
    device = datas.get('device', None)
    data = datas.get('data', None)
    temp = float(int(data[:4],16))/100
    humid = float(int(data[4:8],16))/100
    light = int(data[8:12],16)
    sound = float(int(data[12:16],16))/100
    butt = float(int(data[16:20],16))/100
    # requestには、param1,param2の変数がpostされたものとする
    ret = {"device": str(device), "data": "temp:" + str(temp) + ", humid:" + str(humid), "alldata": str(temp) + str(humid) + str(light) + str(sound) +str(butt)}

    sgfx = SigfoxData()
    sgfx.device = device
    sgfx.temp = temp
    sgfx.humid = humid
    sgfx.light = light
    sgfx.sound = sound
    sgfx.butt = butt
    sgfx.save()
    # JSONに変換して戻す
    return JsonResponse(ret)

