from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Asset, AssetRequest, Department, StockTake, StockTakeItem
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
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.db.models import Count, Sum, Avg, F
from django.db.models.functions import TruncMonth
from io import BytesIO
from datetime import datetime
from django.db import transaction
from django.db.utils import IntegrityError
import os

# landing page
def landing_page(request):
    """Redirect to login page as the first page."""
    return redirect('login')


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
    
    # Calculate summary statistics
    total_assets = assets.count()
    total_value = assets.aggregate(total=Sum('purchase_cost'))['total'] or 0
    utilization_rate = (assets.filter(status='in_use').count() / total_assets * 100) if total_assets > 0 else 0
    
    # Prepare the data for export
    export_data = {
        'title': 'Asset Management Report',
        'summary': {
            'total_assets': total_assets,
            'total_value': total_value,
            'utilization_rate': round(utilization_rate, 1)
        },
        'assets': assets,
        'filters': {
            'department': department,
            'category': category,
            'status': status,
            'start_date': start_date,
            'end_date': end_date
        }
    }
    
    if format_type == 'csv':
        return generate_csv_report(request, export_data)
    elif format_type == 'excel':
        return generate_excel_report(request, export_data)
    else:
        return generate_pdf_report(request, export_data)

def generate_csv_report(request, data):
    """Generate CSV report"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="asset_report_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Write title and generation date
    writer.writerow([data['title']])
    writer.writerow(['Generated on: ' + datetime.now().strftime('%B %d, %Y')])
    writer.writerow([])
    
    # Write summary statistics
    writer.writerow(['Summary Statistics'])
    writer.writerow(['Total Assets', data['summary']['total_assets']])
    writer.writerow(['Total Value', f"${data['summary']['total_value']:.2f}"])
    writer.writerow(['Utilization Rate', f"{data['summary']['utilization_rate']}%"])
    writer.writerow([])
    
    # Write active filters
    writer.writerow(['Active Filters'])
    filters = data['filters']
    if any(filters.values()):
        for key, value in filters.items():
            if value:
                writer.writerow([key.replace('_', ' ').title(), value])
    else:
        writer.writerow(['No filters applied'])
    writer.writerow([])
    
    # Write asset details
    writer.writerow(['Asset Details'])
    writer.writerow(['Asset No', 'Serial No', 'Category', 'Department', 'Status', 'Purchase Date', 'Purchase Cost', 'Assigned To'])
    
    for asset in data['assets']:
        writer.writerow([
            asset.asset_no,
            asset.serial_no,
            asset.get_category_display(),
            asset.department.name,
            asset.get_status_display(),
            asset.purchase_date.strftime('%B %d, %Y') if asset.purchase_date else 'Not Set',
            f"${asset.purchase_cost:.2f}" if asset.purchase_cost else 'Not Set',
            asset.assigned_to.get_full_name() if asset.assigned_to else 'Not Assigned'
        ])
    
    return response

def generate_excel_report(request, data):
    """Generate Excel report"""
    import xlsxwriter
    from io import BytesIO
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Add formatting
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'align': 'center'
    })
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#005B4F',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })
    summary_format = workbook.add_format({
        'bold': True,
        'bg_color': '#e8f5e9',
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True
    })
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_size': 9
    })
    currency_format = workbook.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '$#,##0.00',
        'font_size': 9
    })
    
    # Set row height for better spacing
    worksheet.set_default_row(20)
    
    # Write title
    worksheet.merge_range('A1:H1', data['title'], title_format)
    worksheet.write('A2', 'Generated on: ' + datetime.now().strftime('%B %d, %Y'))
    worksheet.write('A4', '')
    
    # Write summary statistics
    worksheet.write('A5', 'Summary Statistics', summary_format)
    worksheet.write('A6', 'Total Assets', cell_format)
    worksheet.write('B6', data['summary']['total_assets'], cell_format)
    worksheet.write('A7', 'Total Value', cell_format)
    worksheet.write('B7', data['summary']['total_value'], currency_format)
    worksheet.write('A8', 'Utilization Rate', cell_format)
    worksheet.write('B8', f"{data['summary']['utilization_rate']}%", cell_format)
    worksheet.write('A10', '')
    
    # Write active filters
    worksheet.write('A11', 'Active Filters', summary_format)
    row = 12
    filters = data['filters']
    if any(filters.values()):
        for key, value in filters.items():
            if value:
                worksheet.write(f'A{row}', key.replace('_', ' ').title(), cell_format)
                worksheet.write(f'B{row}', value, cell_format)
                row += 1
    else:
        worksheet.write(f'A{row}', 'No filters applied', cell_format)
    row += 2
    
    # Write asset details
    worksheet.write(f'A{row}', 'Asset Details', summary_format)
    row += 1
    
    # Write headers
    headers = ['Asset No', 'Serial No', 'Category', 'Department', 'Status', 'Purchase Date', 'Purchase Cost', 'Assigned To']
    for col, header in enumerate(headers):
        worksheet.write(row, col, header, header_format)
    row += 1
    
    # Write asset data
    for asset in data['assets']:
        worksheet.write(row, 0, asset.asset_no, cell_format)
        worksheet.write(row, 1, asset.serial_no, cell_format)
        worksheet.write(row, 2, asset.get_category_display(), cell_format)
        worksheet.write(row, 3, asset.department.name, cell_format)
        worksheet.write(row, 4, asset.get_status_display(), cell_format)
        worksheet.write(row, 5, asset.purchase_date.strftime('%B %d, %Y') if asset.purchase_date else 'Not Set', cell_format)
        worksheet.write(row, 6, asset.purchase_cost if asset.purchase_cost else 'Not Set', currency_format if asset.purchase_cost else cell_format)
        worksheet.write(row, 7, asset.assigned_to.get_full_name() if asset.assigned_to else 'Not Assigned', cell_format)
        row += 1
    
    # Adjust column widths
    worksheet.set_column('A:A', 15)  # Asset No
    worksheet.set_column('B:B', 20)  # Serial No
    worksheet.set_column('C:C', 20)  # Category
    worksheet.set_column('D:D', 20)  # Department
    worksheet.set_column('E:E', 15)  # Status
    worksheet.set_column('F:F', 15)  # Purchase Date
    worksheet.set_column('G:G', 15)  # Purchase Cost
    worksheet.set_column('H:H', 25)  # Assigned To
    
    # Add filters
    worksheet.autofilter(f'A{row-len(data["assets"])-1}:H{row-1}')
    
    # Freeze the header row
    worksheet.freeze_panes(row - len(data['assets']), 0)
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="asset_report_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    
    return response

def generate_pdf_report(request, data):
    """Generate PDF report"""
    buffer = BytesIO()
    # Use landscape orientation for better data display
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define colors to match website theme
    primary_color = colors.HexColor('#005B4F')  # Your website's green
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
        fontSize=18,
        textColor=text_color,
        spaceAfter=15,
        alignment=1  # Center alignment
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=8
    )
    
    # Normal text style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        textColor=text_color,
        fontSize=8,
        spaceBefore=6,
        spaceAfter=6
    )

    # Add logo
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'konza.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=60, height=30)
        elements.append(img)
        elements.append(Spacer(1, 10))
    
    # Add title and generation date
    elements.append(Paragraph(data['title'], title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", normal_style))
    elements.append(Spacer(1, 10))
    
    # Add summary statistics
    elements.append(Paragraph("Summary Statistics", heading_style))
    summary_data = [
        ['Total Assets', str(data['summary']['total_assets'])],
        ['Total Value', f"${data['summary']['total_value']:.2f}"],
        ['Utilization Rate', f"{data['summary']['utilization_rate']}%"]
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 100])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))
    
    # Add active filters
    elements.append(Paragraph("Active Filters", heading_style))
    filters = data['filters']
    if any(filters.values()):
        filter_data = [[key.replace('_', ' ').title(), value] for key, value in filters.items() if value]
    else:
        filter_data = [['No filters applied', '']]
    
    filter_table = Table(filter_data, colWidths=[150, 100])
    filter_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(filter_table)
    elements.append(Spacer(1, 10))
    
    # Add asset details
    elements.append(Paragraph("Asset Details", heading_style))
    
    # Prepare table data
    table_data = [['Asset No', 'Serial No', 'Category', 'Department', 'Status', 'Purchase Date', 'Purchase Cost', 'Assigned To']]
    for asset in data['assets']:
        table_data.append([
            asset.asset_no,
            asset.serial_no,
            asset.get_category_display(),
            asset.department.name,
            asset.get_status_display(),
            asset.purchase_date.strftime('%B %d, %Y') if asset.purchase_date else 'Not Set',
            f"${asset.purchase_cost:.2f}" if asset.purchase_cost else 'Not Set',
            asset.assigned_to.get_full_name() if asset.assigned_to else 'Not Assigned'
        ])
    
    # Calculate column widths based on page width (landscape)
    page_width = letter[1] - 40  # Subtract margins (using height since we're in landscape)
    col_widths = [
        page_width * 0.10,  # Asset No
        page_width * 0.12,  # Serial No
        page_width * 0.15,  # Category
        page_width * 0.15,  # Department
        page_width * 0.10,  # Status
        page_width * 0.12,  # Purchase Date
        page_width * 0.10,  # Purchase Cost
        page_width * 0.16   # Assigned To
    ]
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style the table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), text_color),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg]),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    
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

@login_required
@admin_required
def stock_take_list(request):
    """View to list all stock take records"""
    stock_takes = StockTake.objects.all()
    return render(request, 'assets/stock_take_list.html', {
        'stock_takes': stock_takes
    })

@login_required
@admin_required
def stock_take_create(request):
    """View to create a new stock take record"""
    if request.method == 'POST':
        department_id = request.POST.get('department')
        notes = request.POST.get('notes', '')
        
        try:
            with transaction.atomic():
                # Create stock take record
                stock_take = StockTake.objects.create(
                    department_id=department_id,
                    notes=notes,
                    created_by=request.user
                )
                
                # Get all assets for the department
                assets = Asset.objects.filter(department_id=department_id)
                
                # Create stock take items for each asset
                for asset in assets:
                    StockTakeItem.objects.create(
                        stock_take=stock_take,
                        asset=asset,
                        expected_quantity=1
                    )
                
                messages.success(request, 'Stock take record created successfully!')
                return redirect('stock_take_detail', pk=stock_take.pk)
        except Exception as e:
            messages.error(request, f'Error creating stock take record: {str(e)}')
    
    departments = Department.objects.all()
    return render(request, 'assets/stock_take_form.html', {
        'departments': departments,
        'action': 'Create'
    })

@login_required
@admin_required
def stock_take_detail(request, pk):
    """View to show details of a stock take record"""
    stock_take = get_object_or_404(StockTake, pk=pk)
    items = stock_take.items.all()
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for item in items:
                    actual_quantity = int(request.POST.get(f'quantity_{item.id}', 0))
                    notes = request.POST.get(f'notes_{item.id}', '')
                    
                    item.actual_quantity = actual_quantity
                    item.notes = notes
                    item.save()
                
                # Update stock take status
                has_discrepancy = False
                all_completed = True
                
                for item in items:
                    if item.actual_quantity != item.expected_quantity:
                        has_discrepancy = True
                        all_completed = False
                        break
                    elif item.actual_quantity == 0:  # If any item hasn't been counted
                        all_completed = False
                
                if has_discrepancy:
                    stock_take.status = 'discrepancy'
                elif all_completed:
                    stock_take.status = 'completed'
                else:
                    stock_take.status = 'in_progress'
                
                stock_take.save()
                
                messages.success(request, 'Stock take updated successfully!')
                return redirect('stock_take_list')
        except Exception as e:
            messages.error(request, f'Error updating stock take: {str(e)}')
    
    return render(request, 'assets/stock_take_detail.html', {
        'stock_take': stock_take,
        'items': items
    })

@login_required
@admin_required
def stock_take_update(request, pk):
    """View to update a stock take record"""
    stock_take = get_object_or_404(StockTake, pk=pk)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        status = request.POST.get('status')
        
        try:
            stock_take.notes = notes
            stock_take.status = status
            stock_take.save()
            messages.success(request, 'Stock take record updated successfully!')
            return redirect('stock_take_detail', pk=stock_take.pk)
        except Exception as e:
            messages.error(request, f'Error updating stock take record: {str(e)}')
    
    return render(request, 'assets/stock_take_form.html', {
        'stock_take': stock_take,
        'action': 'Update'
    })
