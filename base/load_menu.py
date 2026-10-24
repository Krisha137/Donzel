import os
import sys
import csv
import django
from decimal import Decimal, InvalidOperation

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'don.settings')
django.setup()


from base.models import Menu

def load_menu_from_csv():
    Menu.objects.all().delete()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'templates', 'cafe_menu.csv')
    with open(csv_path,'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            raw_price = row['price'].replace('₹', '').replace(',', '').strip()

            if raw_price == "" or not raw_price or raw_price.lower() == 'none':
                    clean_price = None
            else:
                try:
                    clean_price = Decimal(raw_price)
                except (InvalidOperation, ValueError):
                        # જો કોઈ આડાઅવળા અક્ષરો હોય તો પણ None કરી દો
                    clean_price = None
            menu_item = Menu(
                category=row['category'],
                name=row['name'],
                price=clean_price,
                volume=row['volume'],
                ingredeients=row['ingredeients']
            )
            menu_item.save()

if __name__ == '__main__':
    load_menu_from_csv()
    print("Menu items loaded successfully.")