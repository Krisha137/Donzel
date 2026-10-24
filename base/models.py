from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Menu(models.Model):
    category=models.CharField(max_length=100,blank=True,null=True)
    name=models.CharField(max_length=100)
    price=models.DecimalField(max_digits=6,decimal_places=2,blank=True,null=True)
    volume=models.CharField(max_length=100)
    ingredeients=models.TextField()

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    house_no = models.CharField(max_length=100, blank=True, null=True)
    street_area = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, default='Ahmedabad')
    pincode = models.CharField(max_length=10, blank=True, null=True)
    landmark = models.CharField(max_length=150, blank=True, null=True)

    def full_address(self):
        parts = [self.house_no, self.street_area, self.landmark, self.city, self.pincode]
        valid_parts = [p for p in parts if p]
        return ", ".join(valid_parts) if valid_parts else "No address provided yet"

    def __str__(self):
        return f"Profile of {self.user.username}"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('CREDIT', 'Credit (Added Money / Refund / Bonus)'),
        ('DEBIT', 'Debit (Order Payment)'),
    )
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} ₹{self.amount} - {self.wallet.user.username} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.CharField(max_length=150, blank=True, null=True)
    order_type = models.CharField(max_length=50, default='takeaway') # takeaway or dine_in
    table_number = models.CharField(max_length=20, blank=True, null=True)
    pickup_time = models.CharField(max_length=100)
    
    # Address details for delivery
    house_no = models.CharField(max_length=100, blank=True, null=True)
    street_area = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, default='Ahmedabad')
    pincode = models.CharField(max_length=10, blank=True, null=True)
    landmark = models.CharField(max_length=150, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)

    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    STATUS_CHOICES = (
        ('Pending Approval', 'Pending Approval'),
        ('Accepted & Preparing', 'Accepted & Preparing'),
        ('Order Ready', 'Order Ready'),
        ('Out for Delivery', 'Out for Delivery / Counter Handover'),
        ('Order Delivered', 'Order Delivered & Completed'),
        ('Order Served', 'Order Served & Completed'),
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending Approval')
    payment_method = models.CharField(max_length=50, default='Donzel Wallet')
    payment_status = models.CharField(max_length=50, default='Paid')

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name} ({self.customer_email})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.item_name}"