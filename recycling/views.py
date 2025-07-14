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
from .models import Category, Package, Submission
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
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, '用户名或密码错误')
    return render(request, 'recycling/login.html')


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
            submission = form.save(commit=False)
            submission.user = request.user
            submission.save()
            messages.success(request, '卡券提交成功！')
            return redirect('my_submissions')
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
def get_packages(request):
    """获取套餐列表"""
    category_id = request.GET.get('category_id')
    packages = Package.objects.filter(category_id=category_id)
    data = [{'id': pkg.id, 'name': pkg.name, 'commission': float(pkg.commission)} for pkg in packages]
    return JsonResponse(data, safe=False)


@csrf_exempt
def get_qiniu_token(request):
    """获取七牛云上传token"""
    if request.method == 'POST':
        token = generate_qiniu_token()
        return JsonResponse({'token': token})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def upload_image(request):
    """上传图片到七牛云"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            if image_data:
                # 去掉base64前缀
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                
                # 解码base64
                image_bytes = base64.b64decode(image_data)
                
                # 上传到七牛云
                url = upload_data_to_qiniu(image_bytes)
                if url:
                    return JsonResponse({'url': url})
                else:
                    return JsonResponse({'error': '上传失败'}, status=500)
            else:
                return JsonResponse({'error': '没有图片数据'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
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