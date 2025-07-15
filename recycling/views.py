from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.core.paginator import Paginator
from .models import Category, Package, Submission, Store
from .forms import SubmissionForm
from utils.qiniu_util import generate_qiniu_token, upload_data_to_qiniu
import json
import base64


def home(request):
    """首页"""
    return render(request, 'recycling/home.html')


def user_login(request):
    """用户登录"""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        captcha_input = request.POST.get('captcha', '').strip()
        captcha_session = request.session.get('captcha', '')
        
        # 验证验证码（数学运算结果）
        if not captcha_input or captcha_input != captcha_session:
            messages.error(request, '计算结果错误，请重新计算')
            # 清除session中的验证码
            if 'captcha' in request.session:
                del request.session['captcha']
        else:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                # 清除session中的验证码
                if 'captcha' in request.session:
                    del request.session['captcha']
                return redirect('home')
            else:
                messages.error(request, '用户名或密码错误')
                # 清除session中的验证码
                if 'captcha' in request.session:
                    del request.session['captcha']
    
    # 生成新的验证码
    from utils.captcha import generate_captcha
    captcha_text, captcha_image = generate_captcha()
    request.session['captcha'] = captcha_text
    
    return render(request, 'recycling/login.html', {'captcha_image': captcha_image})


def user_logout(request):
    """用户登出"""
    logout(request)
    return redirect('login')


def register(request):
    """用户注册"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'账号 {username} 创建成功！')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'recycling/register.html', {'form': form})


@login_required
def submit_card(request):
    """提交卡券"""
    categories = Category.objects.all()
    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            try:
                submission = form.save(commit=False)
                submission.user = request.user
                submission.save()
                messages.success(request, '卡券提交成功！')
                return redirect('my_submissions')
            except Exception as e:
                messages.error(request, f'提交失败：{str(e)}')
        else:
            # 显示表单错误
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f'{error}')
                    else:
                        field_name = form.fields.get(field, {}).label or field
                        messages.error(request, f'{field_name}: {error}')
    else:
        form = SubmissionForm()
    return render(request, 'recycling/submit_card.html', {
        'form': form,
        'categories': categories
    })


@login_required
def my_submissions(request):
    """我的提交记录"""
    submissions = Submission.objects.filter(user=request.user)
    paginator = Paginator(submissions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'recycling/my_submissions.html', {'page_obj': page_obj})


@login_required
def submission_detail(request, submission_id):
    """查看提交记录详情"""
    submission = get_object_or_404(Submission, id=submission_id, user=request.user)
    return render(request, 'recycling/submission_detail.html', {'submission': submission})


@login_required
def get_packages(request):
    """获取套餐列表"""
    category_id = request.GET.get('category_id')
    packages = Package.objects.filter(category_id=category_id)
    data = [{'id': pkg.id, 'name': pkg.name, 'commission': float(pkg.commission)} for pkg in packages]
    return JsonResponse(data, safe=False)


@login_required
def get_stores(request):
    """获取门店列表"""
    package_id = request.GET.get('package_id')
    if package_id:
        try:
            package = Package.objects.get(id=package_id)
            if package.applicable_stores.exists():
                stores = package.applicable_stores.filter(is_active=True)
            else:
                # 如果套餐没有指定门店，显示所有活跃门店
                stores = Store.objects.filter(is_active=True)
        except Package.DoesNotExist:
            stores = Store.objects.none()
    else:
        stores = Store.objects.filter(is_active=True)
    
    data = [{'id': store.id, 'name': str(store), 'store_number': store.store_number} for store in stores]
    return JsonResponse(data, safe=False)


@login_required
def get_qiniu_token(request):
    """获取七牛云上传token"""
    if request.method == 'GET':
        from utils.qiniu_util import generate_qiniu_token
        token = generate_qiniu_token()
        if token:
            return JsonResponse({'token': token})
        else:
            return JsonResponse({'error': '获取上传凭证失败'}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def refresh_captcha(request):
    """刷新验证码"""
    if request.method == 'GET':
        from utils.captcha import generate_captcha
        captcha_text, captcha_image = generate_captcha()
        request.session['captcha'] = captcha_text
        return JsonResponse({'captcha_image': captcha_image})
    return JsonResponse({'error': 'Method not allowed'}, status=405)




@staff_member_required
def admin_dashboard(request):
    """管理员仪表板"""
    total_submissions = Submission.objects.count()
    pending_submissions = Submission.objects.filter(status='pending').count()
    approved_submissions = Submission.objects.filter(status='approved').count()
    rejected_submissions = Submission.objects.filter(status='rejected').count()
    
    recent_submissions = Submission.objects.order_by('-submitted_at')[:10]
    
    context = {
        'total_submissions': total_submissions,
        'pending_submissions': pending_submissions,
        'approved_submissions': approved_submissions,
        'rejected_submissions': rejected_submissions,
        'recent_submissions': recent_submissions,
    }
    return render(request, 'recycling/admin_dashboard.html', context)


@staff_member_required
def admin_submissions(request):
    """管理员查看所有提交记录"""
    status_filter = request.GET.get('status', '')
    submissions = Submission.objects.all()
    
    if status_filter:
        submissions = submissions.filter(status=status_filter)
    
    submissions = submissions.order_by('-submitted_at')
    paginator = Paginator(submissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': Submission.STATUS_CHOICES,
    }
    return render(request, 'recycling/admin_submissions.html', context)


@staff_member_required
def admin_update_submission(request, submission_id):
    """管理员更新提交记录状态"""
    submission = get_object_or_404(Submission, id=submission_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_remark = request.POST.get('admin_remark', '')
        
        if new_status in dict(Submission.STATUS_CHOICES):
            submission.status = new_status
            submission.admin_remark = admin_remark
            submission.save()
            messages.success(request, f'记录状态已更新为：{submission.get_status_display()}')
        else:
            messages.error(request, '无效的状态值')
    
    return redirect('admin_submissions')


@staff_member_required
def admin_submission_detail(request, submission_id):
    """管理员查看提交记录详情"""
    submission = get_object_or_404(Submission, id=submission_id)
    return render(request, 'recycling/admin_submission_detail.html', {'submission': submission})