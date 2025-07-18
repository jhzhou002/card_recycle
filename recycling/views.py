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
from .models import Category, Package, Submission, Store, BottleCapSubmission
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
                # 获取前端上传的URL
                qr_codes_json = request.POST.get('qr_codes')
                payment_code_url = request.POST.get('payment_code')
                
                if not qr_codes_json:
                    return JsonResponse({'error': '请选择至少一张瓶盖二维码图片'}, status=400)
                
                if not payment_code_url:
                    return JsonResponse({'error': '请选择收款码图片'}, status=400)
                
                # 解析QR码URL列表
                import json
                qr_code_urls = json.loads(qr_codes_json)
                
                if not qr_code_urls:
                    return JsonResponse({'error': '瓶盖二维码上传失败'}, status=400)
                
                # 创建瓶盖提交记录
                bottle_cap_submission = BottleCapSubmission.objects.create(
                    user=request.user,
                    qr_codes=qr_code_urls,
                    payment_code=payment_code_url
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'瓶盖信息提交成功！已上传 {len(qr_code_urls)} 张瓶盖二维码',
                    'redirect': '/my-bottle-caps/'
                })
                
            except Exception as e:
                return JsonResponse({'error': f'提交失败：{str(e)}'}, status=500)
        
        # 如果是传统表单提交（备用）
        form = BottleCapSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            messages.error(request, '请使用新的上传方式')
    else:
        form = BottleCapSubmissionForm()
    
    return render(request, 'recycling/submit_bottle_cap.html', {'form': form})


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
    from django.db.models import Q
    from datetime import datetime, date
    
    # 获取筛选参数
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_settled = request.GET.get('is_settled')
    user_id = request.GET.get('user_id')
    
    # 基础查询
    bottle_caps = BottleCapSubmission.objects.all()
    
    # 日期筛选
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
    
    return render(request, 'recycling/admin_bottle_caps.html', context)


@staff_member_required
def admin_update_bottle_cap(request, bottle_cap_id):
    """管理员更新瓶盖提交状态"""
    bottle_cap = get_object_or_404(BottleCapSubmission, id=bottle_cap_id)
    
    if request.method == 'POST':
        is_settled = request.POST.get('is_settled') == 'on'
        admin_remark = request.POST.get('admin_remark', '')
        
        bottle_cap.is_settled = is_settled
        bottle_cap.admin_remark = admin_remark
        bottle_cap.save()
        
        status_text = '已结算' if is_settled else '未结算'
        messages.success(request, f'瓶盖记录状态已更新为：{status_text}')
    
    return redirect('admin_bottle_caps')


@staff_member_required
def admin_bottle_cap_detail(request, bottle_cap_id):
    """管理员查看瓶盖提交详情"""
    bottle_cap = get_object_or_404(BottleCapSubmission, id=bottle_cap_id)
    return render(request, 'recycling/admin_bottle_cap_detail.html', {'bottle_cap': bottle_cap})


@staff_member_required
def export_bottle_caps_pdf(request):
    """导出瓶盖二维码PDF"""
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from datetime import datetime
    import requests
    import io
    
    # 获取筛选参数
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_settled = request.GET.get('is_settled')
    user_id = request.GET.get('user_id')
    
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
    
    # 创建PDF响应
    response = HttpResponse(content_type='application/pdf')
    filename = f'bottle_caps_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # 创建PDF文档
    doc = SimpleDocTemplate(response, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # 标题
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # 居中
    )
    story.append(Paragraph('瓶盖二维码导出报告', title_style))
    story.append(Spacer(1, 12))
    
    # 导出信息
    info_data = [
        ['导出时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['记录总数', str(bottle_caps.count())],
        ['筛选条件', ''],
    ]
    
    if date_from or date_to:
        date_range = f"{date_from or '开始'} 至 {date_to or '结束'}"
        info_data.append(['日期范围', date_range])
    
    if is_settled:
        settlement_status = '已结算' if is_settled == 'true' else '未结算'
        info_data.append(['结算状态', settlement_status])
    
    if user_id:
        info_data.append(['用户ID', user_id])
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # 遍历每个瓶盖提交记录
    for bottle_cap in bottle_caps:
        # 用户信息标题
        user_title = f"用户ID: {bottle_cap.user.id} | 用户名: {bottle_cap.user.username}"
        story.append(Paragraph(user_title, styles['Heading2']))
        story.append(Spacer(1, 6))
        
        # 提交信息
        submit_info = f"提交时间: {bottle_cap.submitted_at.strftime('%Y-%m-%d %H:%M:%S')} | 结算状态: {'已结算' if bottle_cap.is_settled else '未结算'}"
        story.append(Paragraph(submit_info, styles['Normal']))
        story.append(Spacer(1, 12))
        
        # 添加瓶盖二维码图片
        qr_codes = bottle_cap.qr_codes
        if qr_codes:
            story.append(Paragraph('瓶盖二维码:', styles['Heading3']))
            story.append(Spacer(1, 6))
            
            # 每行显示3张图片
            images_per_row = 3
            image_width = 1.5 * inch
            image_height = 1.5 * inch
            
            for i in range(0, len(qr_codes), images_per_row):
                row_images = qr_codes[i:i + images_per_row]
                image_data = []
                
                for j, qr_url in enumerate(row_images):
                    try:
                        # 下载图片
                        response_img = requests.get(qr_url, timeout=10)
                        if response_img.status_code == 200:
                            img_data = io.BytesIO(response_img.content)
                            img = Image(img_data, width=image_width, height=image_height)
                            image_data.append(img)
                        else:
                            # 如果下载失败，添加占位符
                            image_data.append(Paragraph(f'图片{i+j+1}加载失败', styles['Normal']))
                    except Exception as e:
                        # 添加错误占位符
                        image_data.append(Paragraph(f'图片{i+j+1}错误', styles['Normal']))
                
                # 填充空位
                while len(image_data) < images_per_row:
                    image_data.append('')
                
                # 创建表格显示图片
                img_table = Table([image_data], colWidths=[2*inch]*images_per_row)
                img_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                story.append(img_table)
                story.append(Spacer(1, 12))
        
        # 添加分隔线
        story.append(Spacer(1, 12))
        story.append(Paragraph('_' * 80, styles['Normal']))
        story.append(Spacer(1, 12))
    
    # 生成PDF
    doc.build(story)
    return response