from django.contrib import admin
from .models import Menu, Order, OrderItem

# Admin Panel models (Only essential Shop Menu & Orders)
admin.site.register(Menu)
admin.site.register(Order)