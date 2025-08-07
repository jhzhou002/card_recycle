from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import Category, Package, Submission, Store, BottleCapSubmission, Notification, Tutorial
from .forms import SubmissionForm, BottleCapSubmissionForm
from utils.qiniu_util import generate_qiniu_token, upload_data_to_qiniu
import json
import base64


def home(request):
    """首页"""
    # 获取首页通知
    notifications = Notification.objects.filter(
        is_active=True,
        target_page__in=['home', 'all_pages']
    ).order_by('-updated_at')
    
    context = {
        'notifications': notifications
    }
    return render(request, 'recycling/home.html', context)


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
                
                # 管理员登录后直接跳转到管理后台
                if user.is_staff:
                    return redirect('admin_dashboard')
                else:
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
    
    # 获取针对卡券提交页面的通知
    notifications = Notification.objects.filter(
        is_active=True,
        target_page__in=['card_submit', 'all_pages']
    ).order_by('-updated_at')
    
    return render(request, 'recycling/submit_card.html', {
        'form': form,
        'categories': categories,
        'notifications': notifications
    })


@login_required
def my_submissions(request):
    """我的提交记录（包括卡券和瓶盖）"""
    # 获取提交类型筛选
    submission_type = request.GET.get('type', 'all')
    
    # 根据类型筛选记录
    if submission_type == 'card':
        submissions = Submission.objects.filter(user=request.user).order_by('-submitted_at')
        bottle_caps = BottleCapSubmission.objects.none()
    elif submission_type == 'bottle_cap':
        submissions = Submission.objects.none()
        bottle_caps = BottleCapSubmission.objects.filter(user=request.user).order_by('-submitted_at')
    else:
        submissions = Submission.objects.filter(user=request.user).order_by('-submitted_at')
        bottle_caps = BottleCapSubmission.objects.filter(user=request.user).order_by('-submitted_at')
    
    # 分页处理卡券记录
    submissions_paginator = Paginator(submissions, 10)
    submissions_page_number = request.GET.get('submissions_page')
    submissions_page_obj = submissions_paginator.get_page(submissions_page_number)
    
    # 分页处理瓶盖记录
    bottle_caps_paginator = Paginator(bottle_caps, 10)
    bottle_caps_page_number = request.GET.get('bottle_caps_page')
    bottle_caps_page_obj = bottle_caps_paginator.get_page(bottle_caps_page_number)
    
    context = {
        'submissions_page_obj': submissions_page_obj,
        'bottle_caps_page_obj': bottle_caps_page_obj,
        'submission_type': submission_type,
    }
    
    return render(request, 'recycling/my_submissions.html', context)


@login_required
def submission_detail(request, submission_id):
    """查看提交记录详情"""
    submission = get_object_or_404(Submission, id=submission_id, user=request.user)
    return render(request, 'recycling/submission_detail.html', {'submission': submission})


@login_required
def bottle_cap_detail(request, bottle_cap_id):
    """查看瓶盖记录详情"""
    bottle_cap = get_object_or_404(BottleCapSubmission, id=bottle_cap_id, user=request.user)
    return render(request, 'recycling/bottle_cap_detail.html', {'bottle_cap': bottle_cap})


@login_required
def get_packages(request):
    """获取套餐列表"""
    category_id = request.GET.get('category_id')
    packages = Package.objects.filter(category_id=category_id)
    data = [{'id': pkg.id, 'name': pkg.name, 'commission': float(pkg.commission)} for pkg in packages]
    return JsonResponse(data, safe=False)


def get_categories(request):
    """获取类别信息"""
    category_id = request.GET.get('category_id')
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            return JsonResponse({
                'id': category.id,
                'name': category.name,
                'show_store_field': category.show_store_field
            })
        except Category.DoesNotExist:
            return JsonResponse({'error': '类别不存在'}, status=404)
    return JsonResponse({'error': '缺少类别ID'}, status=400)


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


@login_required
def submit_bottle_cap(request):
    """瓶盖二维码提交"""
    # 初始化existing_payment_code变量，确保在所有代码路径中都可用
    existing_payment_code = None
    last_submission = BottleCapSubmission.objects.filter(user=request.user).order_by('-submitted_at').first()
    if last_submission and last_submission.payment_code:
        existing_payment_code = last_submission.payment_code
    
    if request.method == 'POST':
        # 检查是否是AJAX请求（前端上传）
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'qr_codes' in request.POST:
            try:
                print("开始处理瓶盖提交请求")
                
                # 获取前端上传的URL
                qr_codes_json = request.POST.get('qr_codes')
                payment_code_url = request.POST.get('payment_code')
                
                print(f"接收到的数据: qr_codes={qr_codes_json}, payment_code={payment_code_url}")
                
                if not qr_codes_json:
                    return JsonResponse({'error': '请选择至少一张瓶盖二维码图片'}, status=400)
                
                # 检查用户是否已有收款码记录
                print(f"找到用户已有收款码: {existing_payment_code}")
                
                # 如果没有传入收款码且用户没有历史收款码，则要求上传
                if not payment_code_url and not existing_payment_code:
                    return JsonResponse({'error': '请上传收款码图片（首次提交必需）'}, status=400)
                
                # 使用传入的收款码或复用已有的收款码
                final_payment_code = payment_code_url if payment_code_url else existing_payment_code
                
                # 解析QR码URL列表
                import json
                qr_code_urls = json.loads(qr_codes_json)
                print(f"解析后的QR码URLs: {qr_code_urls}")
                
                if not qr_code_urls:
                    return JsonResponse({'error': '瓶盖二维码上传失败'}, status=400)
                
                print(f"准备创建瓶盖记录，用户: {request.user.id}")
                
                # 创建瓶盖提交记录
                bottle_cap_submission = BottleCapSubmission.objects.create(
                    user=request.user,
                    qr_codes=qr_code_urls,
                    payment_code=final_payment_code
                )
                
                print(f"瓶盖记录创建成功，ID: {bottle_cap_submission.id}")
                
                # 构建提示消息
                message = f'瓶盖信息提交成功！已上传 {len(qr_code_urls)} 张瓶盖二维码'
                if not payment_code_url and existing_payment_code:
                    message += '（已复用历史收款码）'
                
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'redirect': '/my-bottle-caps/',
                    'reused_payment_code': not payment_code_url and existing_payment_code is not None
                })
                
            except Exception as e:
                print(f"瓶盖提交出错: {str(e)}")
                import traceback
                traceback.print_exc()
                return JsonResponse({'error': f'提交失败：{str(e)}'}, status=500)
        
        # 如果是传统表单提交（备用）
        form = BottleCapSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            messages.error(request, '请使用新的上传方式')
    # GET请求或POST请求处理完成后，继续处理模板渲染
    
    # 创建表单对象供模板使用
    form = BottleCapSubmissionForm()
    
    # 获取瓶盖提交页面的通知
    notification = Notification.objects.filter(
        is_active=True,
        target_page__in=['bottle_cap', 'all_pages']
    ).first()
    
    context = {
        'form': form,
        'has_existing_payment_code': existing_payment_code is not None,
        'existing_payment_code_url': existing_payment_code,
        'notification': notification
    }
    
    return render(request, 'recycling/submit_bottle_cap.html', context)


@login_required
def my_bottle_caps(request):
    """我的瓶盖提交记录"""
    bottle_caps = BottleCapSubmission.objects.filter(user=request.user).order_by('-submitted_at')
    paginator = Paginator(bottle_caps, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'recycling/my_bottle_caps.html', {'page_obj': page_obj})




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


@staff_member_required
def admin_bottle_caps(request):
    """管理员瓶盖管理页面"""
    print("admin_bottle_caps view called")
    try:
        from django.db.models import Q
        from datetime import datetime, date
        
        # 获取筛选参数
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        is_settled = request.GET.get('is_settled')
        user_id = request.GET.get('user_id')
        sort_by = request.GET.get('sort_by')
        
        print(f"筛选参数: date_from={date_from}, date_to={date_to}, is_settled={is_settled}, user_id={user_id}, sort_by={sort_by}")
        
        # 基础查询
        bottle_caps = BottleCapSubmission.objects.all()
        print(f"总瓶盖记录数: {bottle_caps.count()}")
        
        # 日期时间筛选（精确到秒）
        if date_from:
            try:
                # 支持datetime-local格式 (YYYY-MM-DDTHH:MM:SS)
                if 'T' in date_from:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%dT%H:%M')
                else:
                    # 兼容旧的日期格式
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                bottle_caps = bottle_caps.filter(submitted_at__gte=date_from_obj)
                print(f"开始时间筛选: {date_from_obj}")
            except ValueError as e:
                print(f"开始时间格式错误: {e}")
                pass
        
        if date_to:
            try:
                # 支持datetime-local格式 (YYYY-MM-DDTHH:MM:SS)
                if 'T' in date_to:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%dT%H:%M')
                else:
                    # 兼容旧的日期格式，设置为当天23:59:59
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                    date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
                bottle_caps = bottle_caps.filter(submitted_at__lte=date_to_obj)
                print(f"结束时间筛选: {date_to_obj}")
            except ValueError as e:
                print(f"结束时间格式错误: {e}")
                pass
        
        # 结算状态筛选
        if is_settled == 'true':
            bottle_caps = bottle_caps.filter(is_settled=True)
        elif is_settled == 'false':
            bottle_caps = bottle_caps.filter(is_settled=False)
        
        # 用户ID筛选
        if user_id:
            try:
                user_id_int = int(user_id)
                bottle_caps = bottle_caps.filter(user_id=user_id_int)
            except ValueError:
                pass
        
        # 排序
        if sort_by == 'user_id_asc':
            bottle_caps = bottle_caps.order_by('user_id', '-submitted_at')
        elif sort_by == 'user_id_desc':
            bottle_caps = bottle_caps.order_by('-user_id', '-submitted_at')
        else:
            bottle_caps = bottle_caps.order_by('-submitted_at')
        
        # 分页
        paginator = Paginator(bottle_caps, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # 统计信息
        total_count = bottle_caps.count()
        settled_count = bottle_caps.filter(is_settled=True).count()
        unsettled_count = bottle_caps.filter(is_settled=False).count()
        
        print(f"统计: 总数={total_count}, 已结算={settled_count}, 未结算={unsettled_count}")
        
        context = {
            'page_obj': page_obj,
            'total_count': total_count,
            'settled_count': settled_count,
            'unsettled_count': unsettled_count,
            'date_from': date_from,
            'date_to': date_to,
            'is_settled': is_settled,
            'user_id': user_id,
            'sort_by': sort_by,
        }
        
        print("准备渲染模板")
        return render(request, 'recycling/admin_bottle_caps.html', context)
        
    except Exception as e:
        print(f"admin_bottle_caps view error: {e}")
        import traceback
        traceback.print_exc()
        raise


@staff_member_required
def admin_update_bottle_cap(request, bottle_cap_id):
    """管理员更新瓶盖提交状态"""
    bottle_cap = get_object_or_404(BottleCapSubmission, id=bottle_cap_id)
    
    if request.method == 'POST':
        is_settled = request.POST.get('is_settled') == 'on'
        admin_remark = request.POST.get('admin_remark', '')
        
        bottle_cap.is_settled = is_settled
        bottle_cap.admin_remark = admin_remark
        
        # 如果标记为已结算，记录结算时间
        if is_settled:
            from django.utils import timezone
            bottle_cap.settled_at = timezone.now()
        else:
            bottle_cap.settled_at = None
            
        bottle_cap.save()
        
        status_text = '已结算' if is_settled else '未结算'
        messages.success(request, f'瓶盖记录状态已更新为：{status_text}')
    
    # 检查是否有返回参数，用于维持页码和筛选条件
    if request.GET:
        # 构建带参数的重定向URL
        from django.http import QueryDict
        params = request.GET.copy()
        redirect_url = f"/admin-bottle-caps/?{params.urlencode()}"
        return redirect(redirect_url)
    
    return redirect('admin_bottle_caps')


@staff_member_required
def admin_bottle_cap_detail(request, bottle_cap_id):
    """管理员查看瓶盖提交详情"""
    bottle_cap = get_object_or_404(BottleCapSubmission, id=bottle_cap_id)
    
    # 获取页码参数，用于返回列表时维持页码
    page = request.GET.get('page', '1')
    
    # 构建返回URL，保持所有筛选参数
    return_params = request.GET.copy()
    if 'page' not in return_params:
        return_params['page'] = page
    
    context = {
        'bottle_cap': bottle_cap,
        'return_params': return_params.urlencode()
    }
    
    return render(request, 'recycling/admin_bottle_cap_detail.html', context)


@staff_member_required
def export_bottle_caps_pdf(request):
    """导出瓶盖二维码PDF - 简化版本"""
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from datetime import datetime
    import requests
    import io
    from PIL import Image as PILImage
    import os
    
    # 获取筛选参数
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_settled = request.GET.get('is_settled')
    user_id = request.GET.get('user_id')
    
    print("开始生成PDF")
    
    # 应用相同的筛选逻辑
    bottle_caps = BottleCapSubmission.objects.all()
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            bottle_caps = bottle_caps.filter(submitted_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            bottle_caps = bottle_caps.filter(submitted_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    if is_settled == 'true':
        bottle_caps = bottle_caps.filter(is_settled=True)
    elif is_settled == 'false':
        bottle_caps = bottle_caps.filter(is_settled=False)
    
    if user_id:
        try:
            user_id_int = int(user_id)
            bottle_caps = bottle_caps.filter(user_id=user_id_int)
        except ValueError:
            pass
    
    bottle_caps = bottle_caps.order_by('-submitted_at')
    print(f"找到 {bottle_caps.count()} 条记录")
    
    # 创建PDF响应
    response = HttpResponse(content_type='application/pdf')
    filename = f'bottle_caps_qr_codes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # 创建PDF canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # 页面设置
    margin = 50
    y_position = height - margin
    images_per_row = 3
    image_size = 150  # 每张图片的大小
    row_spacing = 180  # 行间距
    
    # PDF标题
    p.setFont("Helvetica-Bold", 16)
    title = f"Bottle Cap QR Codes Export - {datetime.now().strftime('%Y-%m-%d')}"
    p.drawString(margin, y_position, title)
    y_position -= 40
    
    # 统计信息
    p.setFont("Helvetica", 10)
    p.drawString(margin, y_position, f"Total Records: {bottle_caps.count()}")
    if date_from or date_to:
        y_position -= 15
        p.drawString(margin, y_position, f"Date Range: {date_from or 'Start'} to {date_to or 'End'}")
    if is_settled:
        y_position -= 15
        status_text = "Settled" if is_settled == 'true' else "Unsettled"
        p.drawString(margin, y_position, f"Status: {status_text}")
    
    y_position -= 30
    
    # 处理每个瓶盖记录
    for bottle_cap in bottle_caps:
        # 检查是否需要新页面
        if y_position < 200:
            p.showPage()
            y_position = height - margin
        
        # 用户信息
        p.setFont("Helvetica-Bold", 12)
        user_info = f"User ID: {bottle_cap.user.id} | Username: {bottle_cap.user.username}"
        p.drawString(margin, y_position, user_info)
        y_position -= 20
        
        p.setFont("Helvetica", 10)
        submit_info = f"Submit Time: {bottle_cap.submitted_at.strftime('%Y-%m-%d %H:%M')} | Status: {'Settled' if bottle_cap.is_settled else 'Pending'}"
        p.drawString(margin, y_position, submit_info)
        y_position -= 25
        
        # 处理瓶盖二维码图片
        qr_codes = bottle_cap.qr_codes
        if qr_codes:
            p.setFont("Helvetica-Bold", 10)
            p.drawString(margin, y_position, f"QR Codes ({len(qr_codes)} images):")
            y_position -= 20
            
            # 按行排列图片
            current_row = 0
            images_in_current_row = 0
            
            for i, qr_url in enumerate(qr_codes):
                try:
                    print(f"处理图片 {i+1}: {qr_url}")
                    
                    # 计算位置
                    x_pos = margin + (images_in_current_row * (image_size + 20))
                    
                    # 检查是否需要换行
                    if images_in_current_row >= images_per_row:
                        y_position -= row_spacing
                        images_in_current_row = 0
                        x_pos = margin
                        
                        # 检查是否需要新页面
                        if y_position < 200:
                            p.showPage()
                            y_position = height - margin
                    
                    try:
                        # 尝试多种方式获取图片
                        img_buffer = None
                        
                        # 方法1: 尝试requests下载（如果网络可用）
                        if qr_url.startswith('http'):
                            full_url = qr_url
                        else:
                            full_url = f"https://guangpan.lingjing235.cn/{qr_url}"
                        
                        try:
                            print(f"尝试下载: {full_url}")
                            headers = {'User-Agent': 'Mozilla/5.0 (compatible; PDF-Export)'}
                            # 设置代理为None，避免代理问题
                            response_img = requests.get(full_url, timeout=10, headers=headers, 
                                                      proxies={'http': None, 'https': None})
                            print(f"下载状态: {response_img.status_code}")
                            
                            if response_img.status_code == 200:
                                img_data = io.BytesIO(response_img.content)
                                pil_img = PILImage.open(img_data)
                                print(f"图片模式: {pil_img.mode}, 尺寸: {pil_img.size}")
                                
                                # 转换为RGB模式
                                if pil_img.mode in ('RGBA', 'P'):
                                    pil_img = pil_img.convert('RGB')
                                
                                # 重新保存为JPEG
                                img_buffer = io.BytesIO()
                                pil_img.save(img_buffer, format='JPEG', quality=90)
                                img_buffer.seek(0)
                                print(f"图片处理完成，大小: {len(img_buffer.getvalue())} bytes")
                        except Exception as download_error:
                            print(f"下载失败: {download_error}")
                            img_buffer = None
                        
                        # 如果成功获取图片，绘制它
                        if img_buffer:
                            print(f"绘制位置: x={x_pos}, y={y_position - image_size}")
                            img_buffer.seek(0)
                            
                            # 使用ImageReader包装BytesIO对象
                            img_reader = ImageReader(img_buffer)
                            p.drawImage(img_reader, x_pos, y_position - image_size, 
                                      width=image_size, height=image_size)
                            
                            # 添加图片编号
                            p.setFont("Helvetica", 8)
                            p.drawString(x_pos, y_position - image_size - 15, f"QR {i+1}")
                            print(f"图片 {i+1} 绘制成功")
                        else:
                            # 绘制URL文本作为备用
                            print(f"绘制URL文本: {qr_url}")
                            p.rect(x_pos, y_position - image_size, image_size, image_size)
                            p.setFont("Helvetica", 8)
                            
                            # 将URL分行显示
                            url_display = qr_url.replace('https://guangpan.lingjing235.cn/', '')
                            if len(url_display) > 20:
                                line1 = url_display[:20]
                                line2 = url_display[20:40] if len(url_display) > 20 else ""
                                line3 = "..." if len(url_display) > 40 else ""
                            else:
                                line1 = url_display
                                line2 = ""
                                line3 = ""
                            
                            p.drawString(x_pos + 5, y_position - image_size/2 + 20, f"QR {i+1}")
                            p.drawString(x_pos + 5, y_position - image_size/2, line1)
                            if line2:
                                p.drawString(x_pos + 5, y_position - image_size/2 - 12, line2)
                            if line3:
                                p.drawString(x_pos + 5, y_position - image_size/2 - 24, line3)
                        
                        images_in_current_row += 1
                        
                    except Exception as inner_error:
                        print(f"内部处理失败: {inner_error}")
                        # 绘制错误占位符
                        p.rect(x_pos, y_position - image_size, image_size, image_size)
                        p.setFont("Helvetica", 8)
                        p.drawString(x_pos + 10, y_position - image_size/2, "Error")
                        images_in_current_row += 1
                        
                except Exception as e:
                    print(f"外部处理失败: {e}")
                    continue
            
            # 移动到下一个记录的位置
            y_position -= row_spacing + 30
        else:
            y_position -= 20
        
        # 添加分隔线
        p.line(margin, y_position, width - margin, y_position)
        y_position -= 20
    
    # 保存PDF
    p.save()
    print("PDF生成完成")
    return response


@staff_member_required
def export_bottle_caps_web(request):
    """网页版瓶盖导出 - 紧急方案"""
    from datetime import datetime
    
    # 获取筛选参数
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_settled = request.GET.get('is_settled')
    user_id = request.GET.get('user_id')
    sort_by = request.GET.get('sort_by')
    
    # 构建查询
    queryset = BottleCapSubmission.objects.all()
    
    if date_from:
        try:
            # 支持datetime-local格式 (YYYY-MM-DDTHH:MM:SS)
            if 'T' in date_from:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%dT%H:%M')
            else:
                # 兼容旧的日期格式
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            queryset = queryset.filter(submitted_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            # 支持datetime-local格式 (YYYY-MM-DDTHH:MM:SS)
            if 'T' in date_to:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%dT%H:%M')
            else:
                # 兼容旧的日期格式，设置为当天23:59:59
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            queryset = queryset.filter(submitted_at__lte=date_to_obj)
        except ValueError:
            pass
    
    if is_settled:
        if is_settled == 'true':
            queryset = queryset.filter(is_settled=True)
        elif is_settled == 'false':
            queryset = queryset.filter(is_settled=False)
    if user_id:
        try:
            user_id_int = int(user_id)
            queryset = queryset.filter(user_id=user_id_int)
        except ValueError:
            pass
    
    # 排序
    if sort_by == 'user_id_asc':
        submissions = queryset.order_by('user_id', '-submitted_at')
    elif sort_by == 'user_id_desc':
        submissions = queryset.order_by('-user_id', '-submitted_at')
    else:
        submissions = queryset.order_by('-submitted_at')
    
    # 计算总图片数量
    total_images = 0
    for submission in submissions:
        if submission.qr_codes:
            total_images += len(submission.qr_codes)
    
    context = {
        'submissions': submissions,
        'total_count': queryset.count(),
        'total_images': total_images,
        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'filter_info': {
            'date_from': date_from,
            'date_to': date_to,
            'is_settled': is_settled,
            'user_id': user_id,
        }
    }
    
    return render(request, 'recycling/export_bottle_caps_web.html', context)


@staff_member_required
def export_bottle_caps_with_payment(request):
    """网页版瓶盖导出（包含收款码）"""
    from datetime import datetime
    
    # 获取筛选参数
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_settled = request.GET.get('is_settled')
    user_id = request.GET.get('user_id')
    sort_by = request.GET.get('sort_by')
    
    # 构建查询
    queryset = BottleCapSubmission.objects.all()
    
    if date_from:
        try:
            # 支持datetime-local格式 (YYYY-MM-DDTHH:MM:SS)
            if 'T' in date_from:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%dT%H:%M')
            else:
                # 兼容旧的日期格式
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            queryset = queryset.filter(submitted_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            # 支持datetime-local格式 (YYYY-MM-DDTHH:MM:SS)
            if 'T' in date_to:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%dT%H:%M')
            else:
                # 兼容旧的日期格式，设置为当天23:59:59
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            queryset = queryset.filter(submitted_at__lte=date_to_obj)
        except ValueError:
            pass
    
    if is_settled:
        if is_settled == 'true':
            queryset = queryset.filter(is_settled=True)
        elif is_settled == 'false':
            queryset = queryset.filter(is_settled=False)
    if user_id:
        try:
            user_id_int = int(user_id)
            queryset = queryset.filter(user_id=user_id_int)
        except ValueError:
            pass
    
    # 排序
    if sort_by == 'user_id_asc':
        submissions = queryset.order_by('user_id', '-submitted_at')
    elif sort_by == 'user_id_desc':
        submissions = queryset.order_by('-user_id', '-submitted_at')
    else:
        submissions = queryset.order_by('-submitted_at')
    
    # 计算总图片数量
    total_images = 0
    for submission in submissions:
        if submission.qr_codes:
            total_images += len(submission.qr_codes)
    
    context = {
        'submissions': submissions,
        'total_count': queryset.count(),
        'total_images': total_images,
        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'filter_info': {
            'date_from': date_from,
            'date_to': date_to,
            'is_settled': is_settled,
            'user_id': user_id,
        }
    }
    
    return render(request, 'recycling/export_bottle_caps_with_payment.html', context)


@staff_member_required
def export_bottle_caps_images(request):
    """单个图片导出 - ZIP打包下载"""
    import zipfile
    import tempfile
    import os
    import csv
    import requests
    from datetime import datetime
    from django.http import HttpResponse
    from urllib.parse import urlparse
    
    # 获取筛选参数
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_settled = request.GET.get('is_settled')
    user_id = request.GET.get('user_id')
    sort_by = request.GET.get('sort_by')
    
    # 构建查询
    queryset = BottleCapSubmission.objects.all()
    
    if date_from:
        try:
            if 'T' in date_from:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%dT%H:%M')
            else:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            queryset = queryset.filter(submitted_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            if 'T' in date_to:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%dT%H:%M')
            else:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            queryset = queryset.filter(submitted_at__lte=date_to_obj)
        except ValueError:
            pass
    
    if is_settled:
        if is_settled == 'true':
            queryset = queryset.filter(is_settled=True)
        elif is_settled == 'false':
            queryset = queryset.filter(is_settled=False)
    
    if user_id:
        try:
            user_id_int = int(user_id)
            queryset = queryset.filter(user_id=user_id_int)
        except ValueError:
            pass
    
    # 排序
    if sort_by == 'user_id_asc':
        submissions = queryset.order_by('user_id', '-submitted_at')
    elif sort_by == 'user_id_desc':
        submissions = queryset.order_by('-user_id', '-submitted_at')
    else:
        submissions = queryset.order_by('-submitted_at')
    
    if not submissions.exists():
        return HttpResponse('没有找到符合条件的记录', status=404)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建CSV映射文件
        csv_file_path = os.path.join(temp_dir, 'image_mapping.csv')
        with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                '文件名', '用户ID', '用户名', '提交记录ID', '图片序号', 
                '提交时间', '结算状态', '原始URL', '管理员备注'
            ])
            
            total_images = 0
            successful_downloads = 0
            
            for submission in submissions:
                if not submission.qr_codes:
                    continue
                    
                for idx, qr_url in enumerate(submission.qr_codes, 1):
                    total_images += 1
                    
                    # 生成文件名
                    timestamp = submission.submitted_at.strftime('%Y%m%d_%H%M%S')
                    file_extension = '.jpg'  # 默认扩展名
                    
                    # 尝试从URL获取扩展名
                    try:
                        parsed_url = urlparse(qr_url)
                        if parsed_url.path:
                            original_ext = os.path.splitext(parsed_url.path)[1]
                            if original_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                                file_extension = original_ext
                    except:
                        pass
                    
                    filename = f"user{submission.user.id}_submission{submission.id}_qr{idx:03d}_{timestamp}{file_extension}"
                    file_path = os.path.join(temp_dir, filename)
                    
                    # 写入CSV记录
                    writer.writerow([
                        filename,
                        submission.user.id,
                        submission.user.username,
                        submission.id,
                        idx,
                        submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
                        '已结算' if submission.is_settled else '未结算',
                        qr_url,
                        submission.admin_remark or ''
                    ])
                    
                    # 下载图片并添加水印
                    try:
                        # 处理URL
                        if qr_url.startswith('http'):
                            download_url = qr_url
                        else:
                            download_url = f"https://guangpan.lingjing235.cn/{qr_url}"
                        
                        print(f"下载图片: {download_url}")
                        
                        # 下载图片
                        response = requests.get(download_url, timeout=30, stream=True)
                        if response.status_code == 200:
                            # 先保存原图到临时位置
                            temp_image_path = file_path + '.temp'
                            with open(temp_image_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            
                            # 添加水印
                            try:
                                from PIL import Image, ImageDraw, ImageFont
                                import io
                                
                                # 打开图片
                                with Image.open(temp_image_path) as img:
                                    # 转换为RGB模式（如果需要）
                                    if img.mode in ('RGBA', 'P'):
                                        img = img.convert('RGB')
                                    
                                    # 创建绘图对象
                                    draw = ImageDraw.Draw(img)
                                    
                                    # 水印文本
                                    watermark_text = f"USER-ID: {submission.user.id} | RECORD: {submission.id} | IMAGE: {idx}"
                                    
                                    # 图片尺寸
                                    img_width, img_height = img.size
                                    
                                    # 尝试使用系统字体，如果失败则使用默认字体
                                    try:
                                        # 根据图片大小动态调整字体大小
                                        font_size = max(20, min(img_width, img_height) // 25)
                                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                                    except:
                                        try:
                                            font_size = max(20, min(img_width, img_height) // 25)
                                            font = ImageFont.truetype("arial.ttf", font_size)
                                        except:
                                            font = ImageFont.load_default()
                                            font_size = 20
                                    
                                    # 获取文本尺寸
                                    try:
                                        bbox = draw.textbbox((0, 0), watermark_text, font=font)
                                        text_width = bbox[2] - bbox[0]
                                        text_height = bbox[3] - bbox[1]
                                    except:
                                        # 兼容旧版本PIL
                                        text_width, text_height = draw.textsize(watermark_text, font=font)
                                    
                                    # 水印位置（右下角）
                                    margin = 10
                                    x = img_width - text_width - margin
                                    y = img_height - text_height - margin
                                    
                                    # 绘制背景矩形（半透明黑色）
                                    padding = 5
                                    bg_bbox = [
                                        x - padding,
                                        y - padding,
                                        x + text_width + padding,
                                        y + text_height + padding
                                    ]
                                    
                                    # 创建半透明背景
                                    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                                    overlay_draw = ImageDraw.Draw(overlay)
                                    overlay_draw.rectangle(bg_bbox, fill=(0, 0, 0, 128))  # 半透明黑色
                                    
                                    # 将背景合并到原图
                                    img = img.convert('RGBA')
                                    img = Image.alpha_composite(img, overlay)
                                    img = img.convert('RGB')
                                    
                                    # 重新创建绘图对象
                                    draw = ImageDraw.Draw(img)
                                    
                                    # 绘制白色文字
                                    draw.text((x, y), watermark_text, fill=(255, 255, 255), font=font)
                                    
                                    # 保存添加水印后的图片
                                    img.save(file_path, 'JPEG', quality=95)
                                    
                                # 删除临时文件
                                os.remove(temp_image_path)
                                
                                successful_downloads += 1
                                print(f"成功下载并添加水印: {filename}")
                                
                            except Exception as watermark_error:
                                print(f"添加水印失败: {watermark_error}")
                                # 如果水印失败，使用原图
                                try:
                                    os.rename(temp_image_path, file_path)
                                    successful_downloads += 1
                                    print(f"水印失败，使用原图: {filename}")
                                except:
                                    print(f"保存原图也失败: {filename}")
                        else:
                            print(f"下载失败: {download_url}, 状态码: {response.status_code}")
                            
                    except Exception as e:
                        print(f"下载图片失败: {qr_url}, 错误: {str(e)}")
                        continue
        
        # 创建统计文件
        stats_file_path = os.path.join(temp_dir, 'export_summary.txt')
        with open(stats_file_path, 'w', encoding='utf-8') as f:
            f.write(f"瓶盖图片导出统计报告（含水印版）\n")
            f.write(f"=" * 50 + "\n")
            f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总记录数: {submissions.count()}\n")
            f.write(f"总图片数: {total_images}\n")
            f.write(f"成功下载: {successful_downloads}\n")
            f.write(f"失败数量: {total_images - successful_downloads}\n")
            f.write(f"成功率: {(successful_downloads / total_images * 100):.1f}%\n\n")
            
            f.write(f"水印功能说明：\n")
            f.write(f"- 每张图片右下角自动添加水印\n")
            f.write(f"- 水印内容：用户ID | 记录ID | 图片序号\n")
            f.write(f"- 适用场景：微信聊天发送时可直接看到用户信息\n")
            f.write(f"- 水印样式：白色文字 + 半透明黑色背景\n\n")
            
            if date_from:
                f.write(f"开始时间: {date_from}\n")
            if date_to:
                f.write(f"结束时间: {date_to}\n")
            if is_settled:
                status_text = "已结算" if is_settled == 'true' else "未结算"
                f.write(f"状态筛选: {status_text}\n")
            if user_id:
                f.write(f"用户ID筛选: {user_id}\n")
        
        # 创建ZIP文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'bottle_caps_images_{timestamp}.zip'
        
        response = HttpResponse(content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        with zipfile.ZipFile(response, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加所有文件到ZIP
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname=arcname)
        
        print(f"ZIP文件创建完成，包含 {successful_downloads} 个图片文件")
        return response
        
    finally:
        # 清理临时文件
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


@staff_member_required
def admin_notifications(request):
    """管理员通知管理"""
    notifications = Notification.objects.all().order_by('-updated_at')
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'recycling/admin_notifications.html', context)


@staff_member_required
def admin_notification_edit(request, notification_id=None):
    """编辑通知"""
    if notification_id:
        notification = get_object_or_404(Notification, id=notification_id)
    else:
        notification = None
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        is_active = request.POST.get('is_active') == 'on'
        target_page = request.POST.get('target_page')
        
        if notification:
            notification.title = title
            notification.content = content
            notification.is_active = is_active
            notification.target_page = target_page
            notification.save()
            messages.success(request, '通知更新成功')
        else:
            Notification.objects.create(
                title=title,
                content=content,
                is_active=is_active,
                target_page=target_page
            )
            messages.success(request, '通知创建成功')
        
        return redirect('admin_notifications')
    
    context = {
        'notification': notification,
        'target_page_choices': Notification._meta.get_field('target_page').choices,
    }
    
    return render(request, 'recycling/admin_notification_edit.html', context)


@staff_member_required
def admin_notification_delete(request, notification_id):
    """删除通知"""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id)
        notification.delete()
        messages.success(request, '通知已删除')
    
    return redirect('admin_notifications')


@staff_member_required
def admin_bottle_caps_batch_update(request):
    """批量更新瓶盖状态"""
    if request.method == 'POST':
        batch_ids = request.POST.get('batch_ids', '')
        is_settled = request.POST.get('is_settled') == 'on'
        admin_remark = request.POST.get('admin_remark', '')
        
        if batch_ids:
            try:
                # 解析ID列表
                id_list = [int(id.strip()) for id in batch_ids.split(',') if id.strip().isdigit()]
                
                if id_list:
                    # 批量更新
                    updated_count = 0
                    for bottle_cap_id in id_list:
                        try:
                            bottle_cap = BottleCapSubmission.objects.get(id=bottle_cap_id)
                            bottle_cap.is_settled = is_settled
                            if admin_remark:
                                bottle_cap.admin_remark = admin_remark
                            if is_settled:
                                from django.utils import timezone
                                bottle_cap.settled_at = timezone.now()
                            else:
                                bottle_cap.settled_at = None
                            bottle_cap.save()
                            updated_count += 1
                        except BottleCapSubmission.DoesNotExist:
                            continue
                    
                    messages.success(request, f'成功批量更新 {updated_count} 条记录')
                else:
                    messages.error(request, '无效的记录ID')
            except ValueError:
                messages.error(request, '记录ID格式错误')
        else:
            messages.error(request, '请选择要更新的记录')
    
    return redirect('admin_bottle_caps')


# ==================== 卡券类别管理 ====================

@staff_member_required
def admin_categories(request):
    """卡券类别管理"""
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'edit':
            # 编辑类别
            category_id = request.POST.get('category_id')
            name = request.POST.get('name', '').strip()
            show_store_field = request.POST.get('show_store_field') == 'true'
            
            if not name:
                return JsonResponse({'success': False, 'message': '类别名称不能为空'})
            
            try:
                category = get_object_or_404(Category, id=category_id)
                category.name = name
                category.show_store_field = show_store_field
                category.save()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        elif action == 'delete':
            # 删除类别
            category_id = request.POST.get('category_id')
            
            try:
                category = get_object_or_404(Category, id=category_id)
                category.delete()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        else:
            # 添加类别
            name = request.POST.get('name', '').strip()
            show_store_field = request.POST.get('show_store_field') == 'true'
            
            if not name:
                return JsonResponse({'success': False, 'message': '类别名称不能为空'})
            
            try:
                Category.objects.create(name=name, show_store_field=show_store_field)
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
    
    # GET请求，显示类别列表
    categories = Category.objects.all().order_by('id')
    context = {
        'categories': categories,
        'total_count': categories.count(),
    }
    return render(request, 'recycling/admin_categories.html', context)


# ==================== 套餐管理 ====================

@staff_member_required
def admin_packages(request):
    """套餐管理"""
    if request.method == 'GET' and request.GET.get('action') == 'get_package':
        # 获取套餐详细信息
        package_id = request.GET.get('package_id')
        try:
            package = get_object_or_404(Package, id=package_id)
            return JsonResponse({
                'success': True,
                'package': {
                    'id': package.id,
                    'name': package.name,
                    'category': package.category.id,
                    'commission': str(package.commission),
                    'stores': list(package.applicable_stores.values_list('id', flat=True))
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    elif request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'edit':
            # 编辑套餐
            package_id = request.POST.get('package_id')
            name = request.POST.get('name', '').strip()
            category_id = request.POST.get('category')
            commission = request.POST.get('commission')
            store_ids = request.POST.getlist('stores')
            
            if not name or not category_id or not commission:
                return JsonResponse({'success': False, 'message': '请填写完整信息'})
            
            try:
                package = get_object_or_404(Package, id=package_id)
                category = get_object_or_404(Category, id=category_id)
                
                package.name = name
                package.category = category
                package.commission = float(commission)
                package.save()
                
                # 更新适用门店
                if store_ids:
                    stores = Store.objects.filter(id__in=store_ids)
                    package.applicable_stores.set(stores)
                else:
                    package.applicable_stores.clear()
                
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        elif action == 'delete':
            # 删除套餐
            package_id = request.POST.get('package_id')
            
            try:
                package = get_object_or_404(Package, id=package_id)
                package.delete()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        else:
            # 添加套餐
            name = request.POST.get('name', '').strip()
            category_id = request.POST.get('category')
            commission = request.POST.get('commission')
            store_ids = request.POST.getlist('stores')
            
            if not name or not category_id or not commission:
                return JsonResponse({'success': False, 'message': '请填写完整信息'})
            
            try:
                category = get_object_or_404(Category, id=category_id)
                package = Package.objects.create(
                    name=name,
                    category=category,
                    commission=float(commission)
                )
                
                # 设置适用门店
                if store_ids:
                    stores = Store.objects.filter(id__in=store_ids)
                    package.applicable_stores.set(stores)
                
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
    
    # GET请求，显示套餐列表
    packages = Package.objects.select_related('category').prefetch_related('applicable_stores').order_by('id')
    categories = Category.objects.all().order_by('id')
    stores = Store.objects.filter(is_active=True).order_by('store_number')
    
    context = {
        'packages': packages,
        'categories': categories,
        'stores': stores,
        'total_count': packages.count(),
    }
    return render(request, 'recycling/admin_packages.html', context)


# ==================== 门店管理 ====================

@staff_member_required
def admin_stores(request):
    """门店管理"""
    if request.method == 'GET' and request.GET.get('action') == 'get_store':
        # 获取门店详细信息
        store_id = request.GET.get('store_id')
        try:
            store = get_object_or_404(Store, id=store_id)
            return JsonResponse({
                'success': True,
                'store': {
                    'id': store.id,
                    'store_number': store.store_number,
                    'name': store.name,
                    'is_active': store.is_active
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    elif request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'edit':
            # 编辑门店
            store_id = request.POST.get('store_id')
            store_number = request.POST.get('store_number', '').strip()
            name = request.POST.get('name', '').strip()
            is_active = request.POST.get('is_active') == 'true'
            
            if not store_number or not name:
                return JsonResponse({'success': False, 'message': '请填写完整信息'})
            
            try:
                store = get_object_or_404(Store, id=store_id)
                
                # 检查门店编号是否重复
                if Store.objects.exclude(id=store.id).filter(store_number=store_number).exists():
                    return JsonResponse({'success': False, 'message': '门店编号已存在'})
                
                store.store_number = store_number
                store.name = name
                store.is_active = is_active
                store.save()
                
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        elif action == 'delete':
            # 删除门店
            store_id = request.POST.get('store_id')
            
            try:
                store = get_object_or_404(Store, id=store_id)
                store.delete()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        elif action == 'toggle_status':
            # 切换门店状态
            store_id = request.POST.get('store_id')
            is_active = request.POST.get('is_active') == 'true'
            
            try:
                store = get_object_or_404(Store, id=store_id)
                store.is_active = is_active
                store.save()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        else:
            # 添加门店
            store_number = request.POST.get('store_number', '').strip()
            name = request.POST.get('name', '').strip()
            is_active = request.POST.get('is_active') == 'true'
            
            if not store_number or not name:
                return JsonResponse({'success': False, 'message': '请填写完整信息'})
            
            try:
                # 检查门店编号是否重复
                if Store.objects.filter(store_number=store_number).exists():
                    return JsonResponse({'success': False, 'message': '门店编号已存在'})
                
                Store.objects.create(
                    store_number=store_number,
                    name=name,
                    is_active=is_active
                )
                
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
    
    # GET请求，显示门店列表
    stores = Store.objects.all().order_by('store_number')
    active_stores = stores.filter(is_active=True)
    
    context = {
        'stores': stores,
        'total_count': stores.count(),
        'active_count': active_stores.count(),
    }
    return render(request, 'recycling/admin_stores.html', context)


# ==================== 个人中心 ====================

@login_required
def profile(request):
    """个人中心"""
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'edit_profile':
            # 编辑个人资料
            first_name = request.POST.get('first_name', '').strip()
            email = request.POST.get('email', '').strip()
            
            try:
                # 检查邮箱是否已被其他用户使用
                if email and email != request.user.email:
                    from django.contrib.auth.models import User
                    if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                        return JsonResponse({'success': False, 'message': '该邮箱已被其他用户使用'})
                
                # 更新用户信息
                request.user.first_name = first_name
                if email:
                    request.user.email = email
                request.user.save()
                
                return JsonResponse({'success': True, 'message': '资料更新成功'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
        
        elif action == 'change_password':
            # 修改密码
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            # 验证当前密码
            if not request.user.check_password(current_password):
                return JsonResponse({'success': False, 'message': '当前密码错误'})
            
            # 验证新密码
            if len(new_password) < 8:
                return JsonResponse({'success': False, 'message': '新密码至少需要8位字符'})
            
            if new_password != confirm_password:
                return JsonResponse({'success': False, 'message': '两次输入的密码不一致'})
            
            try:
                # 更新密码
                request.user.set_password(new_password)
                request.user.save()
                
                # 更新session，避免用户被自动登出
                update_session_auth_hash(request, request.user)
                
                return JsonResponse({'success': True, 'message': '密码修改成功'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})
    
    # GET请求，显示个人中心页面
    # 获取用户统计信息
    user_submissions = Submission.objects.filter(user=request.user)
    user_bottle_caps = BottleCapSubmission.objects.filter(user=request.user)
    
    stats = {
        'total_submissions': user_submissions.count() + user_bottle_caps.count(),
        'approved_submissions': user_submissions.filter(status='approved').count(),
        'card_submissions': user_submissions.count(),
        'bottle_cap_submissions': user_bottle_caps.count(),
    }
    
    context = {
        'stats': stats,
    }
    return render(request, 'recycling/profile.html', context)


# ==================== 教程功能 ====================

def tutorials(request):
    """教程列表页面"""
    # 获取所有已发布的教程
    tutorials_queryset = Tutorial.objects.filter(status='published').order_by('-published_at')
    
    # 获取推荐教程
    featured_tutorials = tutorials_queryset.filter(is_featured=True)[:3]
    
    # 分页处理
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(tutorials_queryset, 10)  # 每页显示10条
    page_number = request.GET.get('page')
    
    try:
        tutorials_page = paginator.page(page_number)
    except PageNotAnInteger:
        # 如果页数不是整数，显示第一页
        tutorials_page = paginator.page(1)
    except EmptyPage:
        # 如果页数超出范围，显示最后一页
        tutorials_page = paginator.page(paginator.num_pages)
    
    # 获取所有类别
    categories = Category.objects.all().order_by('name')
    
    context = {
        'tutorials': tutorials_page,
        'featured_tutorials': featured_tutorials,
        'categories': categories,
        'tutorials_count': tutorials_queryset.count(),
        'paginator': paginator,
        'page_obj': tutorials_page,
    }
    
    return render(request, 'recycling/tutorials.html', context)


def tutorial_detail(request, tutorial_id):
    """教程详情页面"""
    tutorial = get_object_or_404(Tutorial, id=tutorial_id, status='published')
    
    # 增加浏览次数
    tutorial.increment_views()
    
    # 获取相关教程（同类别的其他教程）
    related_tutorials = Tutorial.objects.filter(
        category=tutorial.category,
        status='published'
    ).exclude(id=tutorial.id)[:5]
    
    # 获取教程统计
    total_tutorials = Tutorial.objects.filter(status='published').count()
    category_tutorials = Tutorial.objects.filter(
        category=tutorial.category,
        status='published'
    ).count()
    
    # 处理Markdown内容
    import markdown
    from django.utils.safestring import mark_safe
    
    try:
        # 尝试渲染Markdown，如果失败则使用原始内容
        md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc'])
        html_content = md.convert(tutorial.content)
        tutorial.content = mark_safe(html_content)
    except:
        # 如果markdown处理失败，使用原始内容
        pass
    
    context = {
        'tutorial': tutorial,
        'related_tutorials': related_tutorials,
        'total_tutorials': total_tutorials,
        'category_tutorials': category_tutorials,
    }
    
    return render(request, 'recycling/tutorial_detail.html', context)


# ==================== 管理员教程管理 ====================

@staff_member_required
def admin_tutorials(request):
    """管理员教程管理列表"""
    tutorials = Tutorial.objects.all().select_related('category', 'author').order_by('-updated_at')
    categories = Category.objects.all().order_by('name')
    
    context = {
        'tutorials': tutorials,
        'categories': categories,
    }
    
    return render(request, 'recycling/admin_tutorials.html', context)


@staff_member_required
def admin_tutorial_edit(request, tutorial_id=None):
    """编辑/新增教程"""
    if tutorial_id:
        tutorial = get_object_or_404(Tutorial, id=tutorial_id)
    else:
        tutorial = None
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category_id = request.POST.get('category')
        content = request.POST.get('content', '').strip()
        summary = request.POST.get('summary', '').strip()
        cover_image = request.POST.get('cover_image', '').strip()
        status = request.POST.get('status', 'draft')
        is_featured = request.POST.get('is_featured') == 'on'
        
        # 表单验证
        if not title or not category_id or not content or not summary:
            messages.error(request, '请填写所有必填字段')
            return redirect(request.path)
        
        try:
            category = get_object_or_404(Category, id=category_id)
            
            if tutorial:
                # 更新教程
                tutorial.title = title
                tutorial.category = category
                tutorial.content = content
                tutorial.summary = summary
                tutorial.cover_image = cover_image
                tutorial.status = status
                tutorial.is_featured = is_featured
                
                # 如果状态改为已发布且之前未发布过，设置发布时间
                if status == 'published' and not tutorial.published_at:
                    from django.utils import timezone
                    tutorial.published_at = timezone.now()
                
                tutorial.save()
                messages.success(request, '教程更新成功')
                
            else:
                # 创建教程
                tutorial = Tutorial.objects.create(
                    title=title,
                    category=category,
                    content=content,
                    summary=summary,
                    cover_image=cover_image,
                    status=status,
                    is_featured=is_featured,
                    author=request.user
                )
                
                # 如果直接发布，设置发布时间
                if status == 'published':
                    from django.utils import timezone
                    tutorial.published_at = timezone.now()
                    tutorial.save()
                
                messages.success(request, '教程创建成功')
            
            return redirect('admin_tutorials')
            
        except Exception as e:
            messages.error(request, f'操作失败：{str(e)}')
    
    # GET请求，显示编辑表单
    categories = Category.objects.all().order_by('name')
    
    context = {
        'tutorial': tutorial,
        'categories': categories,
    }
    
    return render(request, 'recycling/admin_tutorial_edit.html', context)


@staff_member_required
def admin_tutorial_delete(request, tutorial_id):
    """删除教程"""
    if request.method == 'POST':
        tutorial = get_object_or_404(Tutorial, id=tutorial_id)
        title = tutorial.title
        tutorial.delete()
        messages.success(request, f'教程 "{title}" 已删除')
    
    return redirect('admin_tutorials')
