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
from .models import Category, Package, Submission, Store, BottleCapSubmission, Notification
from .forms import SubmissionForm, BottleCapSubmissionForm
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


@login_required
def submit_bottle_cap(request):
    """瓶盖二维码提交"""
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
                existing_payment_code = None
                last_submission = BottleCapSubmission.objects.filter(user=request.user).order_by('-submitted_at').first()
                if last_submission and last_submission.payment_code:
                    existing_payment_code = last_submission.payment_code
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
    else:
        # GET请求，检查用户是否已有收款码
        existing_payment_code = None
        last_submission = BottleCapSubmission.objects.filter(user=request.user).order_by('-submitted_at').first()
        if last_submission and last_submission.payment_code:
            existing_payment_code = last_submission.payment_code
    
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
        
        print(f"筛选参数: date_from={date_from}, date_to={date_to}, is_settled={is_settled}, user_id={user_id}")
        
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
    
    # 构建查询
    queryset = BottleCapSubmission.objects.all()
    
    if date_from:
        queryset = queryset.filter(submitted_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(submitted_at__date__lte=date_to)
    if is_settled:
        if is_settled == 'true':
            queryset = queryset.filter(is_settled=True)
        elif is_settled == 'false':
            queryset = queryset.filter(is_settled=False)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
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
    
    # 构建查询
    queryset = BottleCapSubmission.objects.all()
    
    if date_from:
        queryset = queryset.filter(submitted_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(submitted_at__date__lte=date_to)
    if is_settled:
        if is_settled == 'true':
            queryset = queryset.filter(is_settled=True)
        elif is_settled == 'false':
            queryset = queryset.filter(is_settled=False)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
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