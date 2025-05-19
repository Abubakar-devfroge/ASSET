
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Asset, AssetRequest
from .forms import AssetForm, AssetRequestForm
from .decorators import admin_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.db.models import Count
from io import BytesIO
from datetime import datetime

# landig page
def landing_page(request):
    """Public landing page view for GridSet."""
    return render(request, 'index.html')


@login_required
def asset_list(request):
    """View to list all assets"""
    query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    assets = Asset.objects.all()
    
    # Apply search query
    if query:
        assets = assets.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query) |
            Q(department__name__icontains=query) |
            Q(status__icontains=query)
        )
    
    # Apply category filter
    if category_filter:
        assets = assets.filter(category=category_filter)
    
    # Apply status filter
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # Get unique categories and statuses for filters
    categories = Asset.CATEGORY_CHOICES
    statuses = Asset.STATUS_CHOICES
    
    return render(request, 'assets/asset_list.html', {
        'assets': assets,
        'search_query': query,
        'categories': categories,
        'statuses': statuses,
        'selected_category': category_filter,
        'selected_status': status_filter,
    })

@login_required
def asset_detail(request, pk):
    """View to show details of a specific asset"""
    asset = get_object_or_404(Asset, pk=pk)
    can_request = not AssetRequest.objects.filter(
        asset=asset,
        user=request.user,
        approved__isnull=True
    ).exists()
    return render(request, 'assets/asset_detail.html', {
        'asset': asset,
        'can_request': can_request
    })


@login_required
@admin_required
def asset_create(request):
    """View to create a new asset"""
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES)
        if form.is_valid():
            asset = form.save()
            messages.success(request, 'Asset created successfully!')
            return redirect('asset_detail', pk=asset.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AssetForm()
    return render(request, 'assets/asset_form.html', {'form': form, 'action': 'Create'})

@login_required
@admin_required
def asset_update(request, pk):
    """View to update an existing asset"""
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES, instance=asset)
        if form.is_valid():
            asset = form.save()
            messages.success(request, 'Asset updated successfully!')
            return redirect('asset_detail', pk=asset.pk)
    else:
        form = AssetForm(instance=asset)
    return render(request, 'assets/asset_form.html', {'form': form, 'action': 'Update'})

@login_required
@admin_required
def asset_delete(request, pk):
    """View to delete an asset"""
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        asset.delete()
        messages.success(request, 'Asset deleted successfully!')
        return redirect('asset_list')
    return render(request, 'assets/asset_confirm_delete.html', {'asset': asset})

@login_required
def request_asset(request, pk):
    """View to request an asset"""
    asset = get_object_or_404(Asset, pk=pk)
    
    if request.method == 'POST':
        form = AssetRequestForm(request.POST)
        if form.is_valid():
            asset_request = form.save(commit=False)
            asset_request.asset = asset
            asset_request.user = request.user
            asset_request.save()
            
            # Return JSON response for AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            # Fallback for non-AJAX requests
            messages.success(request, 'Asset request submitted successfully!')
            return redirect('asset_list')
    else:
        form = AssetRequestForm()
    
    return render(request, 'assets/request_asset.html', {
        'form': form,
        'asset': asset
    })

@login_required
@admin_required
def manage_requests(request):
    """View to manage asset requests"""
    pending_requests = AssetRequest.objects.filter(approved__isnull=True)
    approved_requests = AssetRequest.objects.filter(approved=True)
    rejected_requests = AssetRequest.objects.filter(approved=False)
    
    return render(request, 'assets/manage_requests.html', {
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests
    })

@login_required
@admin_required
def process_request(request, request_id, action):
    """View to approve or reject asset requests"""
    asset_request = get_object_or_404(AssetRequest, pk=request_id)
    
    if action == 'approve':
        asset_request.approved = True
        asset_request.asset.assigned_to = asset_request.user
        asset_request.asset.status = 'in_use'
        asset_request.asset.save()
        message = 'Request approved successfully!'
    else:
        asset_request.approved = False
        message = 'Request rejected successfully!'
    
    asset_request.approval_date = timezone.now()
    asset_request.save()
    messages.success(request, message)
    return redirect('manage_requests')

def switch_user(request):
    """Temporary view for development to switch between users"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                login(request, user)
                messages.success(request, f'Switched to user: {user.get_full_name() or user.username}')
            except User.DoesNotExist:
                messages.error(request, 'User not found')
        return redirect(request.META.get('HTTP_REFERER', 'asset_list'))
    return redirect('asset_list')

def get_context_data(request):
    """Add available users to context"""
    context = {}
    if settings.DEBUG:
        context['available_users'] = User.objects.all().order_by('-is_staff', 'username')
        context['debug'] = True
    return context

@login_required
def dashboard(request):
    context = {
        'total_assets': Asset.objects.count(),
        'available_assets': Asset.objects.filter(status='available').count(),
        'pending_requests': AssetRequest.objects.filter(approved__isnull=True).count(),
        'assigned_assets': Asset.objects.filter(status='in_use').count(),
        'recent_assets': Asset.objects.all()[:5],
        'recent_requests': AssetRequest.objects.all()[:5],
    }
    return render(request, 'assets/dashboard.html', context)

@login_required
def reports(request):
    """View for generating reports"""
    # Get summary statistics
    total_assets = Asset.objects.count()
    assets_by_category = Asset.objects.values('category').annotate(count=Count('category'))
    assets_by_status = Asset.objects.values('status').annotate(count=Count('status'))
    assets_by_department = Asset.objects.values('department__name').annotate(count=Count('department'))
    pending_requests = AssetRequest.objects.filter(approved__isnull=True).count()
    approved_requests = AssetRequest.objects.filter(approved=True).count()
    rejected_requests = AssetRequest.objects.filter(approved=False).count()

    context = {
        'total_assets': total_assets,
        'assets_by_category': assets_by_category,
        'assets_by_status': assets_by_status,
        'assets_by_department': assets_by_department,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
    }
    return render(request, 'assets/reports.html', context)

@login_required
def download_report(request):
    """Generate and download PDF report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define colors to match website theme
    primary_color = colors.HexColor('#00c853')  # Your website's green
    text_color = colors.HexColor('#2c3e50')
    text_muted = colors.HexColor('#90a4ae')
    border_color = colors.HexColor('#e0e0e0')
    light_bg = colors.HexColor('#e8f5e9')  # Light green background
    
    # Define custom styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=text_color,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=primary_color,
        spaceBefore=20,
        spaceAfter=15
    )
    
    # Normal text style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        textColor=text_color,
        fontSize=10,
        spaceBefore=10,
        spaceAfter=10
    )
    
    # Add logo and title
    elements.append(Paragraph("GridSet", title_style))
    elements.append(Paragraph("Asset Management Report", heading_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", normal_style))
    elements.append(Spacer(1, 20))
    
    # Asset Summary
    elements.append(Paragraph("Asset Distribution", heading_style))
    
    # Assets by Category
    categories = Asset.objects.values('category').annotate(count=Count('category'))
    category_data = [['Category', 'Count']]
    for cat in categories:
        category_data.append([dict(Asset.CATEGORY_CHOICES)[cat['category']], cat['count']])
    
    category_table = Table(category_data, colWidths=[300, 100])
    category_table.setStyle(TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),  # Center align the count column
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg]),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(category_table)
    elements.append(Spacer(1, 20))
    
    # Assets by Status
    elements.append(Paragraph("Status Distribution", heading_style))
    status_data = [['Status', 'Count']]
    statuses = Asset.objects.values('status').annotate(count=Count('status'))
    for status in statuses:
        status_data.append([dict(Asset.STATUS_CHOICES)[status['status']], status['count']])
    
    status_table = Table(status_data, colWidths=[300, 100])
    status_table.setStyle(TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg]),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(status_table)
    elements.append(Spacer(1, 20))
    
    # Department Distribution
    elements.append(Paragraph("Department Distribution", heading_style))
    dept_data = [['Department', 'Count']]
    departments = Asset.objects.values('department__name').annotate(count=Count('department'))
    for dept in departments:
        dept_data.append([dept['department__name'], dept['count']])
    
    dept_table = Table(dept_data, colWidths=[300, 100])
    dept_table.setStyle(TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg]),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(dept_table)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="asset_report_{datetime.now().strftime("%Y%m%d")}.pdf"'
    response.write(pdf)
    
    return response

@login_required
@admin_required
def clear_request_history(request):
    """View to clear processed request history"""
    if request.method == 'POST':
        # Only clear processed requests (approved or rejected)
        AssetRequest.objects.filter(approved__isnull=False).delete()
        messages.success(request, 'Request history cleared successfully!')
    return redirect('manage_requests')
