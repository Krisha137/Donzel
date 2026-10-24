from django.contrib import admin
from django.urls import path
from base import views as homeviews

urlpatterns = [
    path('', homeviews.home, name='home'),
    path('about/', homeviews.about, name='about'),
    path('menu/', homeviews.menu, name='menu'),
    path('customizer/', homeviews.customizer, name='customizer'),
    path('cart/', homeviews.cart, name='cart'),
    path('add-to-cart/', homeviews.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_index>/', homeviews.remove_from_cart, name='remove_from_cart'),
    path('checkout/', homeviews.checkout, name='checkout'),
    path('payment/', homeviews.payment, name='payment'),
    path('order-success/<int:order_id>/', homeviews.order_success, name='order_success'),
    path('signup/', homeviews.signup, name='signup'),
    path('login/', homeviews.loginac, name='login'),
    path('logout/', homeviews.logoutac, name='logout'),
    path('admin-login/', homeviews.admin_login, name='admin_login'),
    path('admin-logout/', homeviews.admin_logout, name='admin_logout'),
    path('update-profile/', homeviews.update_profile_address, name='update_profile'),
    path('add-wallet-money/', homeviews.add_wallet_money, name='add_wallet_money'),
    path('admin-dashboard/', homeviews.admin_dashboard, name='admin_dashboard'),
    path('update-order-status/<int:order_id>/', homeviews.update_order_status, name='update_order_status'),
    path('api/order-status/<int:order_id>/', homeviews.api_order_status, name='api_order_status'),
]