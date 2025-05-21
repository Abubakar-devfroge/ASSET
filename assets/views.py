from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Asset, AssetRequest, Department
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
from django.db.models import Count, Sum, Avg, F
from django.db.models.functions import TruncMonth
from io import BytesIO
from datetime import datetime
from django.db import transaction
from django.db.utils import IntegrityError

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
            try:
                with transaction.atomic():
                    asset = form.save(commit=False)
                    # Ensure department and category are set before generating asset number
                    if not asset.department or not asset.category:
                        messages.error(request, 'Department and Category are required to generate asset number.')
                        return render(request, 'assets/asset_form.html', {'form': form, 'action': 'Create'})
                    
                    # Get the last asset number for this department and category
                    last_asset = Asset.objects.filter(
                        department=asset.department,
                        category=asset.category
                    ).order_by('-asset_no').first()

                    if last_asset and last_asset.asset_no:
                        try:
                            # Extract the number from the last asset number
                            last_number = int(last_asset.asset_no.split('-')[-1])
                            new_number = last_number + 1
                        except (ValueError, IndexError):
                            new_number = 1
                    else:
                        new_number = 1

                    # Format: [department]-[category]-KOTDA-[number]
                    dept_prefix = asset.department.name[:3].upper()
                    cat_prefix = asset.category[:3].upper()
                    asset.asset_no = f"{dept_prefix}-{cat_prefix}-KOTDA-{new_number:04d}"
                    
                    # Verify this number doesn't exist
                    while Asset.objects.filter(asset_no=asset.asset_no).exists():
                        new_number += 1
                        asset.asset_no = f"{dept_prefix}-{cat_prefix}-KOTDA-{new_number:04d}"
                    
                    asset.save()
                messages.success(request, 'Asset created successfully!')
                return redirect('asset_detail', pk=asset.pk)
            except IntegrityError as e:
                messages.error(request, f'Error creating asset: {str(e)}')
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Unexpected error: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
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
    # Get filter parameters
    department = request.GET.get('department')
    category = request.GET.get('category')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Base queryset
    assets = Asset.objects.all()
    requests = AssetRequest.objects.all()

    # Apply filters
    if department:
        assets = assets.filter(department__name=department)
        requests = requests.filter(asset__department__name=department)
    
    if category:
        assets = assets.filter(category=category)
        requests = requests.filter(asset__category=category)
    
    if status:
        assets = assets.filter(status=status)
        requests = requests.filter(asset__status=status)
    
    if start_date:
        assets = assets.filter(purchase_date__gte=start_date)
        requests = requests.filter(request_date__gte=start_date)
    
    if end_date:
        assets = assets.filter(purchase_date__lte=end_date)
        requests = requests.filter(request_date__lte=end_date)

    # Calculate summary statistics
    total_assets = assets.count()
    total_value = assets.aggregate(total=Sum('purchase_cost'))['total'] or 0
    utilization_rate = (assets.filter(status='in_use').count() / total_assets * 100) if total_assets > 0 else 0
    avg_response_time = requests.filter(approved__isnull=False).aggregate(
        avg_time=Avg(F('approval_date') - F('request_date'))
    )['avg_time'] or 0

    # Get filter options
    departments = Department.objects.all()
    categories = Asset.CATEGORY_CHOICES
    statuses = Asset.STATUS_CHOICES

    # Current filters for template
    current_filters = {
        'department': department,
        'category': category,
        'status': status,
        'start_date': start_date,
        'end_date': end_date
    }

    context = {
        'assets': assets,
        'total_assets': total_assets,
        'total_value': total_value,
        'utilization_rate': round(utilization_rate, 1),
        'avg_response_time': round(avg_response_time.days if avg_response_time else 0, 1),
        'departments': departments,
        'categories': categories,
        'statuses': statuses,
        'current_filters': current_filters
    }

    return render(request, 'assets/reports.html', context)

@login_required
def download_report(request):
    """Generate and download report in various formats"""
    format_type = request.GET.get('format', 'pdf')
    report_type = request.GET.get('type', 'all')
    
    # Get all filter parameters
    department = request.GET.get('department')
    category = request.GET.get('category')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    assets = Asset.objects.all()
    
    # Apply all filters
    if department:
        assets = assets.filter(department__name=department)
    if category:
        assets = assets.filter(category=category)
    if status:
        assets = assets.filter(status=status)
    if start_date:
        assets = assets.filter(purchase_date__gte=start_date)
    if end_date:
        assets = assets.filter(purchase_date__lte=end_date)
    
    # Filter by report type
    if report_type == 'category':
        data = assets.values('category').annotate(count=Count('category'))
        title = 'Asset Distribution by Category'
    elif report_type == 'status':
        data = assets.values('status').annotate(count=Count('status'))
        title = 'Asset Distribution by Status'
    elif report_type == 'department':
        data = assets.values('department__name').annotate(count=Count('department'))
        title = 'Asset Distribution by Department'
    else:
        data = None
        title = 'Complete Asset Report'
    
    if format_type == 'csv':
        return generate_csv_report(request, data, title)
    elif format_type == 'excel':
        return generate_excel_report(request, data, title)
    else:
        return generate_pdf_report(request, data, title)

def generate_csv_report(request, data=None, title=None):
    """Generate CSV report"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{title.lower().replace(" ", "_")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([title, 'Generated on: ' + datetime.now().strftime('%B %d, %Y')])
    writer.writerow([])
    
    if data:
        # Write filtered data
        writer.writerow(['Item', 'Count'])
        for item in data:
            if 'category' in item:
                writer.writerow([dict(Asset.CATEGORY_CHOICES)[item['category']], item['count']])
            elif 'status' in item:
                writer.writerow([dict(Asset.STATUS_CHOICES)[item['status']], item['count']])
            else:
                writer.writerow([item['department__name'], item['count']])
    else:
        # Write complete report
        writer.writerow(['Asset Summary'])
        writer.writerow(['Total Assets', Asset.objects.count()])
        writer.writerow(['Total Value', Asset.objects.aggregate(total=Sum('purchase_cost'))['total'] or 0])
        writer.writerow([])
        
        # Category Distribution
        writer.writerow(['Category Distribution'])
        writer.writerow(['Category', 'Count'])
        for item in Asset.objects.values('category').annotate(count=Count('category')):
            writer.writerow([dict(Asset.CATEGORY_CHOICES)[item['category']], item['count']])
        writer.writerow([])
        
        # Status Distribution
        writer.writerow(['Status Distribution'])
        writer.writerow(['Status', 'Count'])
        for item in Asset.objects.values('status').annotate(count=Count('status')):
            writer.writerow([dict(Asset.STATUS_CHOICES)[item['status']], item['count']])
        writer.writerow([])
        
        # Department Distribution
        writer.writerow(['Department Distribution'])
        writer.writerow(['Department', 'Count'])
        for item in Asset.objects.values('department__name').annotate(count=Count('department')):
            writer.writerow([item['department__name'], item['count']])
    
    return response

def generate_excel_report(request, data=None, title=None):
    """Generate Excel report"""
    import xlsxwriter
    from io import BytesIO
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Add formatting
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center'
    })
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4CAF50',
        'font_color': 'white'
    })
    
    # Write title
    worksheet.write('A1', title, title_format)
    worksheet.write('A2', 'Generated on: ' + datetime.now().strftime('%B %d, %Y'))
    worksheet.write('A4', '')
    
    if data:
        # Write filtered data
        worksheet.write('A5', 'Item', header_format)
        worksheet.write('B5', 'Count', header_format)
        row = 6
        for item in data:
            if 'category' in item:
                worksheet.write(f'A{row}', dict(Asset.CATEGORY_CHOICES)[item['category']])
            elif 'status' in item:
                worksheet.write(f'A{row}', dict(Asset.STATUS_CHOICES)[item['status']])
            else:
                worksheet.write(f'A{row}', item['department__name'])
            worksheet.write(f'B{row}', item['count'])
            row += 1
    else:
        # Write complete report
        worksheet.write('A5', 'Asset Summary', title_format)
        worksheet.write('A6', 'Total Assets')
        worksheet.write('B6', Asset.objects.count())
        worksheet.write('A7', 'Total Value')
        worksheet.write('B7', Asset.objects.aggregate(total=Sum('purchase_cost'))['total'] or 0)
        worksheet.write('A9', '')
        
        # Category Distribution
        worksheet.write('A10', 'Category Distribution', title_format)
        worksheet.write('A11', 'Category', header_format)
        worksheet.write('B11', 'Count', header_format)
        row = 12
        for item in Asset.objects.values('category').annotate(count=Count('category')):
            worksheet.write(f'A{row}', dict(Asset.CATEGORY_CHOICES)[item['category']])
            worksheet.write(f'B{row}', item['count'])
            row += 1
        
        # Add more sections as needed...
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{title.lower().replace(" ", "_")}.xlsx"'
    
    return response

def generate_pdf_report(request, data=None, title=None):
    """Generate PDF report"""
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
    elements.append(Paragraph(title, heading_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", normal_style))
    elements.append(Spacer(1, 20))
    
    if data:
        # Write filtered data
        table_data = [['Item', 'Count']]
        for item in data:
            if 'category' in item:
                table_data.append([dict(Asset.CATEGORY_CHOICES)[item['category']], item['count']])
            elif 'status' in item:
                table_data.append([dict(Asset.STATUS_CHOICES)[item['status']], item['count']])
            else:
                table_data.append([item['department__name'], item['count']])
        
        table = Table(table_data, colWidths=[400, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
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
        elements.append(table)
    else:
        # Write complete report
        # Asset Summary
        elements.append(Paragraph("Asset Summary", heading_style))
        summary_data = [
            ['Total Assets', str(Asset.objects.count())],
            ['Total Value', f"${Asset.objects.aggregate(total=Sum('purchase_cost'))['total'] or 0}"],
            ['Utilization Rate', f"{round((Asset.objects.filter(status='in_use').count() / Asset.objects.count() * 100) if Asset.objects.count() > 0 else 0, 1)}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[300, 100])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, border_color),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Category Distribution
        elements.append(Paragraph("Category Distribution", heading_style))
        category_data = [['Category', 'Count']]
        categories = Asset.objects.values('category').annotate(count=Count('category'))
        for cat in categories:
            category_data.append([dict(Asset.CATEGORY_CHOICES)[cat['category']], cat['count']])
        
        category_table = Table(category_data, colWidths=[300, 100])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
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
        elements.append(category_table)
        elements.append(Spacer(1, 20))
        
        # Status Distribution
        elements.append(Paragraph("Status Distribution", heading_style))
        status_data = [['Status', 'Count']]
        statuses = Asset.objects.values('status').annotate(count=Count('status'))
        for status in statuses:
            status_data.append([dict(Asset.STATUS_CHOICES)[status['status']], status['count']])
        
        status_table = Table(status_data, colWidths=[300, 100])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
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
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
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
    response['Content-Disposition'] = f'attachment; filename="{title.lower().replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf"'
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
