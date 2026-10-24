import time
from decimal import Decimal
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from .models import Menu, Order, OrderItem, UserProfile, Wallet, WalletTransaction
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

# Helper to get cart count & total & user profile + wallet history
def get_cart_data(request):
    cart = request.session.get('cart', [])
    count = sum(item.get('quantity', 1) for item in cart)
    subtotal = sum(Decimal(str(item.get('price', 0))) * item.get('quantity', 1) for item in cart)
    
    user_orders = []
    user_profile = None
    user_wallet = None
    wallet_transactions = []

    if request.user.is_authenticated:
        user_orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')[:15]
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet_transactions = user_wallet.transactions.all().order_by('-created_at')[:10]

    return {
        'cart': cart, 
        'cart_count': count, 
        'cart_subtotal': subtotal,
        'user_orders': user_orders,
        'user_profile': user_profile,
        'user_wallet': user_wallet,
        'wallet_transactions': wallet_transactions
    }

def home(request):
    cart_data = get_cart_data(request)
    return render(request, 'home.html', cart_data)

def about(request):
    cart_data = get_cart_data(request)
    return render(request, 'about.html', cart_data)

def menu(request):
    cart_data = get_cart_data(request)
    categories = list(Menu.objects.values_list('category', flat=True).distinct())
    categorized_menu = {}
    for cat in categories:
        if cat:
            categorized_menu[cat] = Menu.objects.filter(category=cat)
    context = {**cart_data, 'menu_items': categorized_menu}
    return render(request, 'menu.html', context)

def customizer(request):
    cart_data = get_cart_data(request)
    return render(request, 'customizer.html', cart_data)

def add_to_cart(request):
    if not request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'login_required', 'redirect_url': '/login/'})
        return render(request, 'login.html', {
            'form': AuthenticationForm(),
            'error': 'Please log in to add desserts to your cart!'
        })

    if request.method == 'POST':
        item_name = request.POST.get('item_name')
        price = request.POST.get('price')
        quantity = int(request.POST.get('quantity', 1))

        if item_name and price:
            cart = request.session.get('cart', [])
            found = False
            for item in cart:
                if item['name'] == item_name:
                    item['quantity'] += quantity
                    found = True
                    break
            if not found:
                cart.append({
                    'name': item_name,
                    'price': float(price),
                    'quantity': quantity
                })
            request.session['cart'] = cart
            request.session.modified = True

            count = sum(i['quantity'] for i in cart)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok', 'cart_count': count, 'item_name': item_name})

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('menu')

def remove_from_cart(request, item_index):
    cart = request.session.get('cart', [])
    if 0 <= item_index < len(cart):
        cart.pop(item_index)
        request.session['cart'] = cart
        request.session.modified = True
    return redirect('cart')

def cart(request):
    cart_data = get_cart_data(request)
    return render(request, 'cart.html', cart_data)

def update_profile_address(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Login required'}, status=401)
    
    if request.method == 'POST':
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.phone = request.POST.get('phone', profile.phone)
        profile.house_no = request.POST.get('house_no', profile.house_no)
        profile.street_area = request.POST.get('street_area', profile.street_area)
        profile.city = request.POST.get('city', profile.city or 'Ahmedabad')
        profile.pincode = request.POST.get('pincode', profile.pincode)
        profile.landmark = request.POST.get('landmark', profile.landmark)
        profile.save()

        email = request.POST.get('email')
        if email:
            request.user.email = email
            request.user.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_json'):
            return JsonResponse({
                'status': 'ok',
                'full_address': profile.full_address(),
                'phone': profile.phone
            })

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'home')

def add_wallet_money(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Login required'}, status=401)

    if request.method == 'POST':
        raw_amount = request.POST.get('amount', '0')
        try:
            amount = Decimal(str(raw_amount))
        except Exception:
            amount = Decimal('0')

        if amount > 0:
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='CREDIT',
                amount=amount,
                description='⚡ Top-Up Added via Online Payment'
            )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_json'):
                return JsonResponse({
                    'status': 'ok',
                    'new_balance': float(wallet.balance),
                    'message': f'Successfully added ₹{amount} to your Donzel Wallet!'
                })

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'home')

def checkout(request):
    cart_data = get_cart_data(request)
    cart = cart_data['cart']
    if not cart:
        return redirect('menu')

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        order_type = request.POST.get('order_type', 'takeaway')
        table_number = request.POST.get('table_number', '')
        pickup_time = request.POST.get('pickup_time', '15 mins')

        city = request.POST.get('city', 'Ahmedabad')
        house_no = request.POST.get('house_no', '')
        street_area = request.POST.get('street_area', '')
        pincode = request.POST.get('pincode', '')
        landmark = request.POST.get('landmark', '')

        if order_type == 'dine_in':
            if not table_number.strip():
                return render(request, 'checkout.html', {
                    **cart_data,
                    'checkout_info': request.POST,
                    'error': '❌ Table Number is required for Dine-In orders.'
                })
            full_addr = ""
            house_no = ""
            street_area = ""
            pincode = ""
            landmark = ""
            pickup_time = "Immediate Serving"
        elif order_type == 'takeaway':
            table_number = ""
            full_addr = ""
            house_no = ""
            street_area = ""
            pincode = ""
            landmark = ""
        else:
            table_number = ""
            parts = [house_no, street_area, landmark, city, pincode]
            valid_parts = [p for p in parts if p]
            full_addr = ", ".join(valid_parts) if valid_parts else ""

        request.session['checkout_info'] = {
            'name': name,
            'email': email,
            'phone': phone,
            'order_type': order_type,
            'table_number': table_number,
            'pickup_time': pickup_time,
            'house_no': house_no,
            'street_area': street_area,
            'city': city,
            'pincode': pincode,
            'landmark': landmark,
            'delivery_address': full_addr,
            'timestamp': time.time()
        }
        request.session.modified = True

        if request.user.is_authenticated:
            profile = cart_data.get('user_profile')
            if profile:
                profile.phone = phone or profile.phone
                profile.house_no = house_no or profile.house_no
                profile.street_area = street_area or profile.street_area
                profile.city = city or profile.city
                profile.pincode = pincode or profile.pincode
                profile.landmark = landmark or profile.landmark
                profile.save()

        return redirect('payment')

    checkout_info = request.session.get('checkout_info', {})
    if request.user.is_authenticated:
        profile = cart_data.get('user_profile')
        if not checkout_info.get('name'):
            checkout_info['name'] = request.user.username
        if not checkout_info.get('email'):
            checkout_info['email'] = request.user.email or f"{request.user.username}@gmail.com"
        if profile:
            if not checkout_info.get('phone'): checkout_info['phone'] = profile.phone or ''
            if not checkout_info.get('house_no'): checkout_info['house_no'] = profile.house_no or ''
            if not checkout_info.get('street_area'): checkout_info['street_area'] = profile.street_area or ''
            if not checkout_info.get('city'): checkout_info['city'] = profile.city or 'Ahmedabad'
            if not checkout_info.get('pincode'): checkout_info['pincode'] = profile.pincode or ''
            if not checkout_info.get('landmark'): checkout_info['landmark'] = profile.landmark or ''

    error_msg = request.GET.get('error')
    return render(request, 'checkout.html', {**cart_data, 'checkout_info': checkout_info, 'error': error_msg})

def send_order_confirmation_email(order):
    """Dispatches order receipt email to customer's Gmail address"""
    if not order.customer_email:
        return

    subject = f"🍨 Donzel Ice Cream Order Receipt - Order #{order.id}"
    
    items_summary = "\n".join([
        f"  - {item.quantity}x {item.item_name} (₹{item.price} each)"
        for item in order.items.all()
    ])

    delivery_line = f"Delivery Address: {order.delivery_address}\n" if order.delivery_address else ""

    message_text = f"""Dear {order.customer_name},

Thank you for ordering with Donzel Artisanal Ice Cream Parlour!

==================================================
ORDER CONFIRMATION RECEIPT - ORDER #{order.id}
==================================================
Customer Name: {order.customer_name}
Customer Email: {order.customer_email}
Customer Phone: {order.customer_phone}
{delivery_line}Serving Mode: {order.order_type.title()} {f'({order.table_number})' if order.table_number else ''}
Pickup / Prep Time: {order.pickup_time}
Payment Status: {order.payment_status} ({order.payment_method})

ORDER ITEMS:
{items_summary}

==================================================
TOTAL BILL AMOUNT: ₹{order.total_price}
==================================================

Parlour Location: S.G. Highway, near LJ University, Ahmedabad
Contact Phone: +91 98765 43210
Email: info@donzelicecream.com

We are preparing your sub-zero chilled treats!

Warm Regards,
Donzel Artisanal Ice Cream Team 🍨
"""

    item_rows_html = "".join([
        f'<li style="border-bottom: 1px dashed #333; padding: 10px 0; font-size: 14px; display: flex; justify-content: space-between; color: #f5f5f5;">'
        f'<span><strong>{item.quantity}x</strong> {item.item_name}</span>'
        f'<span style="font-weight: 600; color: #fff;">₹{item.price * item.quantity}</span>'
        f'</li>'
        for item in order.items.all()
    ])

    delivery_html = f'<p style="font-size: 12px; color: #bbb; margin-top: 4px;">📍 Delivery Location: <strong>{order.delivery_address}</strong></p>' if order.delivery_address else ''

    html_message = f"""
    <div style="font-family: Arial, sans-serif; background: #0d0d0d; color: #f5f5f5; padding: 30px; border-radius: 12px; max-width: 600px; margin: 0 auto; border: 1px solid #c5a880;">
        <h2 style="color: #c5a880; text-align: center; font-family: Georgia, serif; font-size: 26px; margin-bottom: 5px;">🍨 DONZEL ARTISANAL ICE CREAM</h2>
        <p style="text-align: center; color: #aaa; font-size: 13px; margin-top: 0;">Order Confirmation & Bill Receipt</p>
        <hr style="border: 0; border-top: 1px solid rgba(197,168,128,0.3); margin: 20px 0;">
        
        <p style="font-size: 14px;">Dear <strong>{order.customer_name}</strong>,</p>
        <p style="font-size: 13px; color: #ccc;">Your chilled ice cream order has been placed and is being prepared!</p>
        
        <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(197,168,128,0.2); padding: 16px; border-radius: 8px; margin: 20px 0;">
            <div style="font-weight: bold; font-size: 18px; color: #c5a880;">
                Order #{order.id}
            </div>
            <p style="font-size: 12px; color: #bbb; margin-top: 6px; line-height: 1.5;">
                Serving Mode: <strong>{order.order_type.title()}</strong> {f'({order.table_number})' if order.table_number else ''}<br>
                Prep Time: <strong>{order.pickup_time}</strong><br>
                Payment Status: <strong>{order.payment_status}</strong> ({order.payment_method})
            </p>
            {delivery_html}
        </div>

        <h3 style="color: #c5a880; font-size: 16px; margin-bottom: 12px; font-family: Georgia, serif;">Order Items:</h3>
        <ul style="list-style: none; padding: 0; margin: 0 0 20px 0;">
            {item_rows_html}
        </ul>

        <hr style="border: 0; border-top: 1px solid #c5a880; margin: 20px 0;">

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 20px; font-weight: bold; color: #c5a880; padding: 10px 0;">
            <span>Total Amount:</span>
            <span style="font-size: 24px; color: #c5a880;">₹{order.total_price}</span>
        </div>

        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px dashed #333; font-size: 12px; color: #888;">
            📍 S.G. Highway, near LJ University, Ahmedabad | 📞 +91 98765 43210<br>
            Thank you for choosing Donzel Artisanal Ice Cream Parlour!
        </div>
    </div>
    """

    try:
        send_mail(
            subject=subject,
            message=message_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            html_message=html_message,
            fail_silently=False
        )
        print(f"\n[GMAIL SMTP SUCCESS] ---> Sent receipt to {order.customer_email} for Order #{order.id}\n")
    except Exception as e:
        print(f"\n[GMAIL SMTP LOG] ---> Could not deliver email to {order.customer_email}: {e}\n")

def payment(request):
    cart_data = get_cart_data(request)
    cart = cart_data['cart']
    checkout_info = request.session.get('checkout_info')

    order_id = request.GET.get('order_id') or request.POST.get('existing_order_id')
    existing_order = None
    if order_id:
        existing_order = Order.objects.filter(id=order_id).first()

    if existing_order:
        checkout_info = {
            'name': existing_order.customer_name,
            'email': existing_order.customer_email,
            'phone': existing_order.customer_phone,
            'order_type': existing_order.order_type,
            'table_number': existing_order.table_number,
            'pickup_time': existing_order.pickup_time,
            'delivery_address': existing_order.delivery_address,
        }
        cart_subtotal = existing_order.total_price
    else:
        if not cart or not checkout_info:
            return redirect('checkout')
        cart_subtotal = cart_data['cart_subtotal']

    user_wallet = cart_data.get('user_wallet')

    if request.method == 'POST':
        payment_method_selected = request.POST.get('payment_method', 'Donzel Wallet')
        
        if payment_method_selected == 'Donzel Wallet':
            if not request.user.is_authenticated or not user_wallet:
                return render(request, 'payment.html', {
                    **cart_data, 'checkout_info': checkout_info, 'cart_subtotal': cart_subtotal,
                    'error_message': '❌ Please log in to your account to pay using Donzel Wallet.'
                })
            
            if user_wallet.balance < cart_subtotal:
                return render(request, 'payment.html', {
                    **cart_data, 'checkout_info': checkout_info, 'cart_subtotal': cart_subtotal,
                    'existing_order': existing_order,
                    'error_message': f'❌ Insufficient Wallet Balance! Your wallet has ₹{user_wallet.balance}, but total bill is ₹{cart_subtotal}. Please top up your wallet to complete this order.'
                })

            user_wallet.balance -= cart_subtotal
            user_wallet.save()

            if existing_order:
                order = existing_order
                order.payment_method = "Donzel Wallet Balance"
                order.payment_status = "Paid (Donzel Wallet)"
                order.save()
            else:
                order = Order.objects.create(
                    user=request.user,
                    customer_name=checkout_info.get('name', request.user.username),
                    customer_email=checkout_info.get('email', request.user.email),
                    customer_phone=checkout_info.get('phone', ''),
                    order_type=checkout_info.get('order_type', 'takeaway'),
                    table_number=checkout_info.get('table_number', ''),
                    pickup_time=checkout_info.get('pickup_time', '15 mins'),
                    house_no=checkout_info.get('house_no', ''),
                    street_area=checkout_info.get('street_area', ''),
                    city=checkout_info.get('city', 'Ahmedabad'),
                    pincode=checkout_info.get('pincode', ''),
                    landmark=checkout_info.get('landmark', ''),
                    delivery_address=checkout_info.get('delivery_address', ''),
                    total_price=cart_subtotal,
                    payment_method="Donzel Wallet Balance",
                    payment_status="Paid (Donzel Wallet)"
                )
                for item in cart:
                    OrderItem.objects.create(
                        order=order,
                        item_name=item['name'],
                        price=Decimal(str(item['price'])),
                        quantity=item['quantity']
                    )

            WalletTransaction.objects.create(
                wallet=user_wallet,
                transaction_type='DEBIT',
                amount=cart_subtotal,
                description=f'🍨 Payment for Donzel Order #{order.id}'
            )

            send_order_confirmation_email(order)
            request.session['cart'] = []
            request.session.pop('checkout_info', None)
            request.session.modified = True
            return redirect('order_success', order_id=order.id)

        else:
            # Direct UPI / Online Payment or any other non-wallet submission is blocked as Future Scope
            return render(request, 'payment.html', {
                **cart_data,
                'checkout_info': checkout_info,
                'cart_subtotal': cart_subtotal,
                'existing_order': existing_order,
                'error_message': '❌ Online Payment / Direct UPI is currently under development (Future Scope). Please use your Donzel Wallet balance to pay and confirm your order.'
            })

    return render(request, 'payment.html', {
        **cart_data,
        'checkout_info': checkout_info,
        'cart_subtotal': cart_subtotal,
        'existing_order': existing_order,
    })

def order_success(request, order_id):
    cart_data = get_cart_data(request)
    order = get_object_or_404(Order, id=order_id)

    return render(request, 'order_success.html', {
        **cart_data, 
        'order': order,
    })

def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html')
    else:
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password1', '').strip()
        confirm_password = request.POST.get('password2', '').strip()
        
        phone = request.POST.get('phone', '').strip()
        house_no = request.POST.get('house_no', '').strip()
        street_area = request.POST.get('street_area', '').strip()
        city = request.POST.get('city', 'Ahmedabad').strip()
        pincode = request.POST.get('pincode', '').strip()
        landmark = request.POST.get('landmark', '').strip()

        if not username or not password:
            return render(request, 'signup.html', {'error': 'Username and password are required.'})
        
        if password != confirm_password:
            return render(request, 'signup.html', {'error': 'Passwords do not match.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username already taken. Please choose another.'})

        user = User.objects.create_user(username=username, email=email, password=password)
        
        UserProfile.objects.create(
            user=user,
            phone=phone,
            house_no=house_no,
            street_area=street_area,
            city=city or 'Ahmedabad',
            pincode=pincode,
            landmark=landmark
        )

        Wallet.objects.create(user=user, balance=Decimal('0.00'))

        login(request, user)
        return redirect('home')

def loginac(request):
    if request.method == 'GET':
        active_tab = request.GET.get('tab', 'customer')
        return render(request, 'login.html', {'form': AuthenticationForm(), 'active_tab': active_tab})
    else:
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {'form': form, 'error': 'Invalid customer username or password.', 'active_tab': 'customer'})

def admin_login(request):
    if request.method == 'POST':
        admin_id = request.POST.get('admin_id', '').strip()
        password = request.POST.get('password', '').strip()
        
        expected_id = getattr(settings, 'DONZEL_ADMIN_USERNAME', 'admin')
        expected_pass = getattr(settings, 'DONZEL_ADMIN_PASSWORD', 'admin@123')
        
        if admin_id == expected_id and password == expected_pass:
            request.session['is_admin_logged_in'] = True
            request.session['admin_user'] = admin_id
            return redirect('admin_dashboard')
        else:
            return render(request, 'login.html', {
                'form': AuthenticationForm(),
                'admin_error': '❌ Invalid Admin ID or Password. Please check manager credentials.',
                'active_tab': 'admin'
            })
    return redirect('login')

def admin_logout(request):
    request.session.pop('is_admin_logged_in', None)
    request.session.pop('admin_user', None)
    return redirect('login')

def logoutac(request):
    logout(request)
    return redirect('home')

def admin_dashboard(request):
    if not request.session.get('is_admin_logged_in'):
        return render(request, 'login.html', {
            'form': AuthenticationForm(),
            'admin_error': '🔒 Admin login required to access Manager Dashboard.',
            'active_tab': 'admin'
        })

    cart_data = get_cart_data(request)
    all_orders = Order.objects.all().prefetch_related('items').order_by('-created_at')
    
    total_revenue = sum(o.total_price for o in all_orders if o.payment_status != 'Cancelled')
    pending_count = all_orders.filter(status='Pending Approval').count()
    preparing_count = all_orders.filter(status='Accepted & Preparing').count()
    ready_count = all_orders.filter(status='Order Ready').count()
    completed_count = all_orders.filter(status='Order Delivered').count()
    served_count = all_orders.filter(status='Order Served').count()
    future_scope_count = all_orders.filter(status='Out for Delivery').count()

    context = {
        **cart_data,
        'orders': all_orders,
        'total_orders': all_orders.count(),
        'total_revenue': total_revenue,
        'pending_count': pending_count,
        'preparing_count': preparing_count,
        'ready_count': ready_count,
        'completed_count': completed_count,
        'served_count': served_count,
        'future_scope_count': future_scope_count,
        'admin_user': request.session.get('admin_user', 'admin')
    }
    return render(request, 'admin_dashboard.html', context)

def update_order_status(request, order_id):
    if not request.session.get('is_admin_logged_in') and not request.user.is_staff:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_json'):
            return JsonResponse({'status': 'error', 'message': 'Admin login required'}, status=403)
        return redirect('login')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        
        if new_status:
            order.status = new_status
            now = timezone.now()
            if new_status == 'Accepted & Preparing' and not order.accepted_at:
                order.accepted_at = now
            elif new_status == 'Order Ready' and not order.ready_at:
                order.ready_at = now
            elif new_status in ['Order Delivered', 'Order Served'] and not order.completed_at:
                order.completed_at = now
            order.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_json'):
                return JsonResponse({'status': 'ok', 'new_status': order.status})

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'admin_dashboard')

def api_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    status_step_map = {
        'Pending Approval': 1,
        'Accepted & Preparing': 1,
        'Order Ready': 2,
        'Out for Delivery': 3,
        'Order Delivered': 4,
        'Order Served': 3,
    }
    
    current_step = status_step_map.get(order.status, 1)
    
    return JsonResponse({
        'order_id': order.id,
        'status': order.status,
        'current_step': current_step,
        'is_ready': (order.status == 'Order Ready'),
        'is_served': (order.status == 'Order Served'),
        'is_completed': (order.status in ['Order Delivered', 'Order Served']),
        'created_at': order.created_at.strftime('%H:%M'),
        'accepted_at': order.accepted_at.strftime('%H:%M') if order.accepted_at else None,
        'ready_at': order.ready_at.strftime('%H:%M') if order.ready_at else None,
        'completed_at': order.completed_at.strftime('%H:%M') if order.completed_at else None,
        'pickup_time': order.pickup_time,
        'order_type': order.order_type,
        'table_number': order.table_number,
        'customer_name': order.customer_name,
        'payment_status': order.payment_status
    })
