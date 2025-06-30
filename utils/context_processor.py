# from django.urls import include


# from setup.models import Setup


def check_active_sidebar_links(request):
    current_url = f"{request.resolver_match.namespace}:{request.resolver_match.url_name}"

    leave_status = False
    roster_status = False
    employee_status = False
    attendance_status = False
    setting_status = False
    payout_status = False


    # checking leave urls active status
    leave_urls =[ 'leave:leave_list', 'leave:leave_type_list', 'leave:employee_leave_report']
    if current_url in leave_urls:
        leave_status = True

    # checking roster urls active status
    roster_urls =[ 'roster:shift_list']
    if current_url in roster_urls:
        roster_status = True

    employee_urls =[ 'user:employee_list']
    if current_url in employee_urls:
        employee_status = True
    
    attendance_urls =[ 'attendance:request_list']
    if current_url in attendance_urls:
        attendance_status = True
    
    setting_urls =[ 'fiscal_year:list', 'department:department_list']
    if current_url in setting_urls:
        setting_status = True

    # checking payout urls active status
    payout_urls = ['payout:salary_type_list', 'payout:salary_release_list']
    if current_url in payout_urls:
        payout_status = True

    context = {     
        'current_url': current_url,
        'leave_status': leave_status,
        'roster_status': roster_status,
        'employee_status': employee_status,
        'attendance_status': attendance_status,
        'setting_status': setting_status,
        'payout_status': payout_status,
    }
    return context