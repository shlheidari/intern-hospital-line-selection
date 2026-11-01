from django.urls import path

from . import views

urlpatterns = [
    # public pages
    path('', views.index, name='index'),
    path('member/', views.member, name='member'),
    path('capacity/', views.capacity, name='capacity'),
    path('capacity/selector/', views.selector, name='selector'),

    # a student's turn
    path('select/', views.select, name='select'),
    path('select/selected/', views.selected, name='selected'),
    path('select/loggedout_manual/', views.loggedout_manual, name='loggedout_manual'),
    path('select/concurrentlogincheck/', views.concurrentlogincheck, name='concurrentlogincheck'),
    path('validate_selections/', views.validate_selections, name='validate_selections'),
    path('get_selected_options/', views.get_selected_options, name='get_selected_options'),

    # password change
    path('pas/', views.pas, name='pas'),
    path('pas/change_password/',
         views.PasswordsChangeView.as_view(template_name='line/change_password.html')),

    # admin utilities
    path('userdata/', views.userdata, name='userdata'),
    path('realtime_data_page/', views.realtime_data_page, name='realtime_data_page'),
    path('get_real_time_data/', views.get_real_time_data, name='get_real_time_data'),
    path('get_selection_data/', views.get_selection_data, name='get_selection_data'),
    path('update_real_time_data/', views.update_real_time_data, name='update_real_time_data'),
    path('admin/download-template/', views.download_template, name='admin_download_template'),
]
