# GridSet - Asset Management System

GridSet is a modern, web-based asset management system built with Django that helps organizations track and manage their assets efficiently.

## Features

### Asset Management
- Create, view, update, and delete assets
- Categorize assets (Hardware, Software, etc.)
- Track asset status (Available, In Use, Under Maintenance)
- Asset image upload support
- Department-wise asset distribution

### Request System
- Users can request assets
- Admin approval workflow
- Request history tracking
- Status tracking (Pending, Approved, Rejected)
- Email notifications for request updates

### User Management
- Role-based access control (Admin/Regular Users)
- User authentication and authorization
- User profile management
- Department assignment

### Reporting
- Comprehensive asset distribution reports
- PDF report generation
- Distribution by category, status, and department
- Request summary statistics
- Visual data representation
![report](https://github.com/user-attachments/assets/bd36a3da-c2af-4268-a9fd-4dcaf0b8b026)



### Dashboard
- Overview statistics
- Recent assets listing
- Recent requests tracking
- Quick access to key functions
- Status indicators

![dashboard](https://github.com/user-attachments/assets/8e8edef0-f359-4d8f-b5e3-fa0a8610c929)

### Modern UI/UX
- Clean, responsive design
- Intuitive navigation
- Status badges and indicators
- Modal confirmations
- Success notifications
- Mobile-friendly interface

  ![asset](https://github.com/user-attachments/assets/a6cb840a-7406-4b62-99b7-950e15ce3e34)


## Technology Stack

- **Backend**: Django 4.x
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite (default) / PostgreSQL
- **UI Framework**: Bootstrap 5
- **Icons**: Font Awesome
- **PDF Generation**: ReportLab
- **API**: Django REST Framework

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/gridset.git
cd gridset          
```
2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Run migrations:
```bash
python manage.py migrate
```
5. Create test users:
```bash
python manage.py createsuperuser
```
6. Run the development server:
```bash
python manage.py runserver
```

## Default Users

After running `create_test_users`, the following accounts are available:

- Admin User:
  - Username: admin
  - Password: admin

- Regular Users:
  - Username: user1, user2, user3
  - Password: same as username

## Project Structure

asset_management_system
assets
migrations
management
commands
templates
assets
registration
models.py
views.py
urls.py
static
styles.css
manage.py



## Key Features Explained

### Asset Categories
- Furniture
- Technology
- Vehicles
- Office Supplies
- Machinery/Equipment

### Asset Status Types
- Available
- In Use
- Under Maintenance
- Retired

### Department Management
- Asset assignment by department
- Department-wise reporting
- Access control based on departments

### Request Workflow
1. User submits asset request
2. Admin reviews request
3. Request approved/rejected
4. Asset status updated automatically
5. User notified of decision

## Security Features

- User authentication required
- Role-based access control
- Admin-only sections
- CSRF protection
- Secure password handling

## API Endpoints

- `/assets/` - List all assets
- `/assets/<id>/` - Asset details
- `/requests/` - Manage requests
- `/reports/` - Generate reports
- `/reports/download/` - Download PDF reports

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Requirements

- Python 3.8+
- Django 4.x
- Other dependencies in requirements.txt

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors

- Prince Gabriel - Initial work and maintenance

## Support

For support:
- Create an issue in the repository
- Email: princeafrim1@gmail.com

## Acknowledgments

- Bootstrap for the UI framework
- Font Awesome for icons
- ReportLab for PDF generation
- Django community for the amazing framework

## Screenshots

(Add screenshots of key features here)

## Future Enhancements

- Email notifications
- Asset maintenance scheduling
- QR code generation for assets
- Mobile app development
- Advanced reporting features
- Asset lifecycle tracking

## Version History

- 1.0.0
  - Initial Release
  - Basic asset management
  - User authentication
  - Request system

## Notes

- Ensure proper database backups
- Regular security updates
- Check logs for errors
- Monitor system performance
